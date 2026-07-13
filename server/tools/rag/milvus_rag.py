"""Milvus-based RAG system with real semantic embeddings.

Uses sentence-transformers for genuine semantic embeddings,
Milvus for vector storage and ANN search.
"""

import json
import socket
from typing import List, Dict, Any, Optional

try:
    from pymilvus import MilvusClient
except ImportError:
    print("WARNING: pymilvus not installed. Install with: pip install pymilvus>=3.0")

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    print("WARNING: sentence-transformers not installed. Install with: pip install sentence-transformers")


class MilvusRAG:
    """Milvus-based RAG with real semantic embeddings from sentence-transformers.

    Features:
    - Real embeddings: sentence-transformers (384-dim semantic vectors)
    - Real vector database: Milvus with ANN indexing
    - Genuine semantic search: cosine/L2 similarity on meaningful vectors
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 19530,
        collection_name: str = "documents",
        embedding_model: str = "all-MiniLM-L6-v2",
    ):
        """Initialize Milvus RAG with semantic embeddings.

        Args:
            host: Milvus server host
            port: Milvus server port
            collection_name: Collection name for documents
            embedding_model: Sentence-transformers model to use (384-dim)
        """
        self.host = host
        self.port = port
        self.collection_name = collection_name
        self.client = None
        self.embedding_model = None
        self.embedding_model_name = embedding_model
        self.mock_mode = False
        self.mock_documents = {}

        try:
            self._connect()
            self._create_collection()
            # Only load embedding model if Milvus connected successfully
            self._load_embedding_model()
        except Exception as e:
            print(f"Milvus connection failed: {e}. Using mock mode.")
            self.mock_mode = True

    def _load_embedding_model(self):
        """Lazily load embedding model when needed (not in mock mode)."""
        if self.embedding_model is None and not self.mock_mode:
            try:
                self.embedding_model = SentenceTransformer(self.embedding_model_name)
            except Exception as e:
                print(f"Warning: Could not load embedding model: {e}")
                print("Install with: pip install sentence-transformers")
                self.mock_mode = True

    def _connect(self):
        """Connect to Milvus server with timeout."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        try:
            result = sock.connect_ex((self.host, self.port))
            if result != 0:
                raise ConnectionError(f"Cannot reach Milvus at {self.host}:{self.port}")
        finally:
            sock.close()

        self.client = MilvusClient(f"http://{self.host}:{self.port}")

    def _create_collection(self):
        """Create collection schema if it doesn't exist."""
        if not self.client.has_collection(self.collection_name):
            self.client.create_collection(
                collection_name=self.collection_name,
                dimension=384,  # sentence-transformers default
                metric_type="L2",  # L2 distance for semantic similarity
                auto_id=True,
            )

    def _get_embedding(self, text: str) -> List[float]:
        """Generate semantic embedding from text.

        Args:
            text: Text to embed

        Returns:
            384-dimensional semantic embedding vector
        """
        # Lazily load model if not in mock mode
        if self.embedding_model is None and not self.mock_mode:
            self._load_embedding_model()

        if not self.embedding_model:
            raise RuntimeError("Embedding model not initialized")

        # Generate embedding
        embedding = self.embedding_model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    def add_document(
        self,
        doc_id: str,
        content: str,
        doc_type: str,
        metadata: Dict[str, Any] = None,
    ):
        """Add document to Milvus with semantic embedding.

        Args:
            doc_id: Document ID (stored in metadata)
            content: Document content to embed
            doc_type: Type of document
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

        # Generate real semantic embedding
        vector = self._get_embedding(content)

        # Store doc_id in metadata (not in Milvus auto_id field)
        meta = metadata or {}
        meta["doc_id"] = doc_id

        self.client.insert(
            collection_name=self.collection_name,
            data=[
                {
                    "vector": vector,
                    "content": content,
                    "document_type": doc_type,
                    "metadata": json.dumps(meta),
                }
            ],
        )

    def search(
        self,
        query: str,
        doc_type: str = None,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """Search for relevant documents using semantic similarity.

        Args:
            query: Search query (will be embedded)
            doc_type: Filter by document type (optional)
            top_k: Number of top results

        Returns:
            List of relevant documents with relevance scores
        """
        if self.mock_mode:
            return self._mock_search(query, doc_type, top_k)

        # Generate semantic embedding for query
        query_vector = self._get_embedding(query)

        # Build filter if needed
        filter_expr = None
        if doc_type:
            filter_expr = f'document_type == "{doc_type}"'

        # Semantic search in Milvus
        results = self.client.search(
            collection_name=self.collection_name,
            data=[query_vector],
            limit=top_k,
            search_params={"metric_type": "L2"},
            filter=filter_expr,
            output_fields=["content", "document_type", "metadata"],
        )

        # Format results
        formatted_results = []
        if results and len(results) > 0:
            for hit in results[0]:
                meta = json.loads(hit.get("metadata", "{}"))
                formatted_results.append(
                    {
                        "doc_id": meta.get("doc_id"),
                        "content": hit.get("content"),
                        "document_type": hit.get("document_type"),
                        "metadata": meta,
                        "relevance_score": float(hit.get("distance", 0)),
                    }
                )

        return formatted_results

    def _mock_search(self, query: str, doc_type: str = None, top_k: int = 5) -> List[Dict[str, Any]]:
        """Mock search (keyword matching only).

        Args:
            query: Search query
            doc_type: Filter by document type (optional)
            top_k: Number of results

        Returns:
            Mock search results (keyword-based, not semantic)
        """
        query_terms = set(query.lower().split())
        results = []

        for doc_id, doc in self.mock_documents.items():
            # Apply doc_type filter if specified
            if doc_type and doc["document_type"] != doc_type:
                continue

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
            filter=f'metadata like "%{doc_id}%"',
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
            filter=f'metadata like "%{doc_id}%"',
            limit=1,
            output_fields=["*"],
        )

        if results:
            return results[0]
        return None

    def get_stats(self) -> Dict[str, Any]:
        """Get collection statistics.

        Returns:
            Collection statistics
        """
        if self.mock_mode:
            return {
                "mode": "mock",
                "total_documents": len(self.mock_documents),
                "indexed": True,
            }

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
            "embedding_model": "all-MiniLM-L6-v2",
            "embedding_dimension": 384,
        }

    def list_all_documents(self) -> List[Dict[str, Any]]:
        """List all stored documents.

        Returns:
            List of all documents with their metadata
        """
        if self.mock_mode:
            result = []
            for doc_id, doc in self.mock_documents.items():
                result.append(
                    {
                        "doc_id": doc_id,
                        "content": doc["content"],
                        "document_type": doc["document_type"],
                        "metadata": doc.get("metadata", {}),
                    }
                )
            return result

        # Query all documents
        results = self.client.query(
            collection_name=self.collection_name,
            filter="",
            limit=16384,
            output_fields=["id", "content", "document_type", "metadata"],
        )

        formatted_results = []
        for doc in results:
            meta = json.loads(doc.get("metadata", "{}"))
            formatted_results.append(
                {
                    "doc_id": meta.get("doc_id"),
                    "content": doc.get("content"),
                    "document_type": doc.get("document_type"),
                    "metadata": meta,
                }
            )

        return formatted_results

    def close(self):
        """Close Milvus connection."""
        if self.client:
            self.client.close()
