"""Milvus-based RAG system for curriculum-aware document retrieval.

Uses modern MilvusClient API (PyMilvus 3.0+), replacing deprecated ORM-style API.
"""

import json
import socket
from typing import List, Dict, Any, Optional
import hashlib

try:
    from pymilvus import MilvusClient
except ImportError:
    print("WARNING: pymilvus not installed. Install with: pip install pymilvus>=3.0")


class MilvusRAG:
    """Milvus-based RAG for semantic search on curriculum data using modern MilvusClient API."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 19530,
        collection_name: str = "documents",
    ):
        """Initialize Milvus RAG system.

        Args:
            host: Milvus server host
            port: Milvus server port
            collection_name: Collection name for documents
        """
        self.host = host
        self.port = port
        self.collection_name = collection_name
        self.client = None
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

        # Initialize MilvusClient (modern API)
        self.client = MilvusClient(f"http://{self.host}:{self.port}")

    def _create_collection(self):
        """Create collection schema if it doesn't exist."""
        # Only create if it doesn't already exist
        if not self.client.has_collection(self.collection_name):
            # Create collection with MilvusClient 3.0+ API (simplified)
            # Using auto_id=True for ID generation, simple schema
            self.client.create_collection(
                collection_name=self.collection_name,
                dimension=384,
                metric_type="L2",
                auto_id=True,
            )

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

        # Merge doc_id into metadata
        meta = metadata or {}
        meta["doc_id"] = doc_id

        self.client.insert(
            collection_name=self.collection_name,
            data=[
                {
                    "vector": embedding,
                    "content": content,
                    "document_type": doc_type,
                    "metadata": json.dumps(meta),
                }
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

        # Build filter if needed
        filter_expr = None
        if doc_type:
            filter_expr = f'document_type == "{doc_type}"'

        # Search using MilvusClient
        results = self.client.search(
            collection_name=self.collection_name,
            data=[query_embedding],
            limit=top_k,
            search_params={"metric_type": "L2"},
            filter=filter_expr,
            output_fields=["content", "document_type", "metadata"],
        )

        # Format results
        formatted_results = []
        if results and len(results) > 0:
            for hit in results[0]:
                formatted_results.append(
                    {
                        "doc_id": hit.get("id"),
                        "content": hit.get("content"),
                        "document_type": hit.get("document_type"),
                        "metadata": json.loads(hit.get("metadata", "{}")),
                        "relevance_score": float(hit.get("distance", 0)),
                    }
                )

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

        self.client.delete(
            collection_name=self.collection_name,
            filter=f'id == "{doc_id}"'
        )

    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific document.

        Args:
            doc_id: Document ID

        Returns:
            Document data or None
        """
        if self.mock_mode:
            return self.mock_documents.get(doc_id)

        results = self.client.query(
            collection_name=self.collection_name,
            filter=f'id == "{doc_id}"',
            output_fields=["*"]
        )

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

        # Get collection stats from Milvus
        try:
            stats = self.client.get_collection_stats(self.collection_name)
            total_docs = stats.get("row_count", 0)
        except:
            total_docs = 0

        return {
            "mode": "milvus",
            "total_documents": total_docs,
            "collection_name": self.collection_name,
            "indexed": True,
        }

    def list_all_documents(self) -> List[Dict[str, Any]]:
        """List all stored documents/chunks.

        Returns:
            List of all documents with their metadata
        """
        if self.mock_mode:
            result = []
            for doc_id, doc in self.mock_documents.items():
                result.append({
                    "doc_id": doc_id,
                    "content": doc["content"],
                    "document_type": doc["document_type"],
                    "metadata": doc.get("metadata", {}),
                })
            return result

        # Query all documents
        results = self.client.query(
            collection_name=self.collection_name,
            filter="",
            output_fields=["id", "content", "document_type", "metadata"]
        )

        formatted_results = []
        for doc in results:
            formatted_results.append({
                "doc_id": doc.get("id"),
                "content": doc.get("content"),
                "document_type": doc.get("document_type"),
                "metadata": json.loads(doc.get("metadata", "{}")),
            })

        return formatted_results

    def list_by_type(self, doc_type: str) -> List[Dict[str, Any]]:
        """List all documents of a specific type.

        Args:
            doc_type: Document type to filter by

        Returns:
            List of documents matching the type
        """
        if self.mock_mode:
            result = []
            for doc_id, doc in self.mock_documents.items():
                if doc["document_type"] == doc_type:
                    result.append({
                        "doc_id": doc_id,
                        "content": doc["content"],
                        "document_type": doc["document_type"],
                        "metadata": doc.get("metadata", {}),
                    })
            return result

        results = self.client.query(
            collection_name=self.collection_name,
            filter=f'document_type == "{doc_type}"',
            output_fields=["id", "content", "document_type", "metadata"]
        )

        formatted_results = []
        for doc in results:
            formatted_results.append({
                "doc_id": doc.get("id"),
                "content": doc.get("content"),
                "document_type": doc.get("document_type"),
                "metadata": json.loads(doc.get("metadata", "{}")),
            })

        return formatted_results

    def close(self):
        """Close Milvus connection."""
        if not self.mock_mode and self.client:
            self.client.close()
