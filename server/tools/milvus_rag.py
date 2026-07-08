"""Milvus-based RAG system for curriculum-aware document retrieval.

Replaces document_fetcher and document_indexer with Milvus vector DB.
"""

import json
import socket
from typing import List, Dict, Any, Optional
from pathlib import Path
import hashlib
import threading

try:
    from pymilvus import Collection, connections, utility, FieldSchema, CollectionSchema, DataType
except ImportError:
    print("WARNING: pymilvus not installed. Install with: pip install pymilvus")


class MilvusRAG:
    """Milvus-based RAG for semantic search on curriculum data."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 19530,
        db_name: str = "curriculum_db",
        collection_name: str = "documents",
    ):
        """Initialize Milvus RAG system.

        Args:
            host: Milvus server host
            port: Milvus server port
            db_name: Database name
            collection_name: Collection name for documents
        """
        self.host = host
        self.port = port
        self.db_name = db_name
        self.collection_name = collection_name
        self.mock_mode = False
        self.mock_documents = {}

        try:
            self._connect()
            self._create_collection()
        except Exception as e:
            print(f"Milvus connection failed: {e}. Using mock mode.")
            self.mock_mode = True

    def _connect(self):
        """Connect to Milvus server with timeout."""
        # Quick check if server is reachable
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        try:
            result = sock.connect_ex((self.host, self.port))
            if result != 0:
                raise ConnectionError(f"Cannot reach Milvus at {self.host}:{self.port}")
        finally:
            sock.close()

        # Connect with pymilvus
        connections.connect(
            alias="default",
            host=self.host,
            port=self.port,
        )

    def _create_collection(self):
        """Create collection schema if it doesn't exist."""
        if utility.has_collection(self.collection_name, using="default"):
            utility.drop_collection(self.collection_name, using="default")

        # Define schema
        fields = [
            FieldSchema(
                name="id",
                dtype=DataType.VARCHAR,
                is_primary=True,
                auto_id=False,
                max_length=100,
            ),
            FieldSchema(
                name="embedding",
                dtype=DataType.FLOAT_VECTOR,
                dim=384,  # Embedding dimension
            ),
            FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=10000),
            FieldSchema(name="document_type", dtype=DataType.VARCHAR, max_length=100),
            FieldSchema(name="metadata", dtype=DataType.VARCHAR, max_length=5000),
        ]

        schema = CollectionSchema(fields=fields, description="Curriculum documents")

        # Create collection
        collection = Collection(
            name=self.collection_name,
            schema=schema,
            using="default",
        )

        # Create index
        index_params = {
            "metric_type": "L2",
            "index_type": "IVF_FLAT",
            "params": {"nlist": 128},
        }
        collection.create_index(field_name="embedding", index_params=index_params)

    def _generate_mock_embedding(self, text: str) -> List[float]:
        """Generate simple embedding using hash (for mock mode).

        Args:
            text: Text to embed

        Returns:
            384-dimensional embedding vector
        """
        hash_val = int(hashlib.md5(text.encode()).hexdigest(), 16)
        embedding = []
        for i in range(384):
            embedding.append(float((hash_val + i) % 1000) / 1000.0)
        return embedding

    def add_document(self, doc_id: str, content: str, doc_type: str, metadata: Dict[str, Any] = None):
        """Add document to Milvus.

        Args:
            doc_id: Document ID
            content: Document content
            doc_type: Type of document (e.g., 'jee_math', 'cbse_physics')
            metadata: Optional metadata dictionary
        """
        if self.mock_mode:
            self.mock_documents[doc_id] = {
                "id": doc_id,
                "content": content,
                "document_type": doc_type,
                "metadata": metadata or {},
            }
            return

        embedding = self._generate_mock_embedding(content)

        collection = Collection(self.collection_name, using="default")
        collection.insert(
            [
                [doc_id],
                [embedding],
                [content],
                [doc_type],
                [json.dumps(metadata or {})],
            ]
        )

    def search(self, query: str, doc_type: str = None, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search for relevant documents.

        Args:
            query: Search query
            doc_type: Filter by document type (optional)
            top_k: Number of top results

        Returns:
            List of relevant documents
        """
        if self.mock_mode:
            return self._mock_search(query, top_k)

        query_embedding = self._generate_mock_embedding(query)

        collection = Collection(self.collection_name, using="default")
        collection.load()

        # Build search filter
        expr = None
        if doc_type:
            expr = f'document_type == "{doc_type}"'

        # Search
        results = collection.search(
            data=[query_embedding],
            anns_field="embedding",
            param={"metric_type": "L2", "params": {"nprobe": 10}},
            limit=top_k,
            expr=expr,
            output_fields=["content", "document_type", "metadata"],
        )

        # Format results
        formatted_results = []
        for hit in results[0]:
            formatted_results.append(
                {
                    "doc_id": hit.id,
                    "content": hit.entity.get("content"),
                    "document_type": hit.entity.get("document_type"),
                    "metadata": json.loads(hit.entity.get("metadata", "{}")),
                    "relevance_score": float(hit.score),
                }
            )

        collection.release()
        return formatted_results

    def _mock_search(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """Mock search for testing without Milvus.

        Args:
            query: Search query
            top_k: Number of results

        Returns:
            Mock search results
        """
        query_terms = set(query.lower().split())
        results = []

        for doc_id, doc in self.mock_documents.items():
            content = doc["content"].lower()
            score = sum(1 for term in query_terms if term in content)

            if score > 0:
                results.append(
                    {
                        "doc_id": doc_id,
                        "content": doc["content"][:500],
                        "document_type": doc["document_type"],
                        "metadata": doc.get("metadata", {}),
                        "relevance_score": score / len(query_terms) if query_terms else 0,
                    }
                )

        # Sort by relevance and return top_k
        results.sort(key=lambda x: x["relevance_score"], reverse=True)
        return results[:top_k]

    def delete_document(self, doc_id: str):
        """Delete document from Milvus.

        Args:
            doc_id: Document ID to delete
        """
        if self.mock_mode:
            if doc_id in self.mock_documents:
                del self.mock_documents[doc_id]
            return

        collection = Collection(self.collection_name, using="default")
        collection.delete(expr=f'id == "{doc_id}"')

    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific document.

        Args:
            doc_id: Document ID

        Returns:
            Document data or None
        """
        if self.mock_mode:
            return self.mock_documents.get(doc_id)

        collection = Collection(self.collection_name, using="default")
        collection.load()

        results = collection.query(expr=f'id == "{doc_id}"', output_fields=["*"])

        collection.release()

        if results:
            return results[0]
        return None

    def get_stats(self) -> Dict[str, Any]:
        """Get index statistics.

        Returns:
            Index statistics
        """
        if self.mock_mode:
            return {
                "mode": "mock",
                "total_documents": len(self.mock_documents),
                "indexed": True,
            }

        collection = Collection(self.collection_name, using="default")
        return {
            "mode": "milvus",
            "total_documents": collection.num_entities,
            "collection_name": self.collection_name,
            "indexed": True,
        }

    def close(self):
        """Close Milvus connection."""
        if not self.mock_mode:
            connections.disconnect(alias="default")
