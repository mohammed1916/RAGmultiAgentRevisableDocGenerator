"""Milvus-based RAG system with real semantic embeddings.

Uses sentence-transformers for genuine semantic embeddings,
Milvus for vector storage and ANN search.
"""

import json
import socket
from typing import List, Dict, Any, Optional

from ...base.logger import setup_logger

try:
    from pymilvus import MilvusClient
except ImportError:
    print("WARNING: pymilvus not installed. Install with: pip install pymilvus>=3.0")

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    print("WARNING: sentence-transformers not installed. Install with: pip install sentence-transformers")

logger = setup_logger(__name__)


class MilvusRAG:
    """Milvus-based RAG with real semantic embeddings from sentence-transformers.

    Features:
    - Real embeddings: sentence-transformers (384-dim semantic vectors)
    - Real vector database: Milvus with ANN indexing
    - Genuine semantic search: cosine/L2 similarity on meaningful vectors
    - Multiple collections: Separate collections for Class 10 and Class 12
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 19530,
        embedding_model: str = "all-MiniLM-L6-v2",
    ):
        """Initialize Milvus RAG with semantic embeddings.

        Args:
            host: Milvus server host
            port: Milvus server port
            embedding_model: Sentence-transformers model to use (384-dim)
        """
        self.host = host
        self.port = port
        self.collection_names = {
            "10": "documents_class_10",
            "12": "documents_class_12",
        }
        self.client = None
        self.embedding_model = None
        self.embedding_model_name = embedding_model
        self.mock_mode = False
        self.mock_documents = {}

        try:
            self._connect()
            self._create_collections()
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

    def _create_collections(self):
        """Create collection schemas if they don't exist."""
        for class_level, collection_name in self.collection_names.items():
            if not self.client.has_collection(collection_name):
                self.client.create_collection(
                    collection_name=collection_name,
                    dimension=384,  # sentence-transformers default
                    metric_type="COSINE",  # Cosine similarity for semantic search
                    auto_id=True,
                )
                logger.info(f"Created collection: {collection_name} (Class {class_level})")

    def recreate_collections(self):
        """Drop both collections if they exist and create fresh ones.

        Used when fully replacing the indexed data (e.g. re-ingesting from
        source). Requires an active Milvus connection (not mock mode).
        """
        if self.mock_mode:
            self.mock_documents = {}
            return

        for class_level, collection_name in self.collection_names.items():
            if self.client.has_collection(collection_name):
                self.client.drop_collection(collection_name)
                logger.info(f"Dropped existing collection: {collection_name}")

            self.client.create_collection(
                collection_name=collection_name,
                dimension=384,
                metric_type="COSINE",
                auto_id=True,
            )
            logger.info(f"Created fresh collection: {collection_name} (Class {class_level})")

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
        class_level: str = "12",
        metadata: Dict[str, Any] = None,
    ):
        """Add document to Milvus with semantic embedding.

        Args:
            doc_id: Document ID (stored in metadata)
            content: Document content to embed
            doc_type: Type of document
            class_level: Class level ("10" or "12") for collection routing
            metadata: Optional metadata dictionary
        """
        # Ensure class_level is valid
        if class_level not in self.collection_names:
            raise ValueError(f"Invalid class_level: {class_level}. Must be one of {list(self.collection_names.keys())}")

        collection_name = self.collection_names[class_level]

        if self.mock_mode:
            self.mock_documents[doc_id] = {
                "id": doc_id,
                "content": content,
                "document_type": doc_type,
                "metadata": metadata or {},
                "class_level": class_level,
            }
            return

        # Generate real semantic embedding
        vector = self._get_embedding(content)

        # Store doc_id in metadata (not in Milvus auto_id field)
        meta = metadata or {}
        meta["doc_id"] = doc_id

        self.client.insert(
            collection_name=collection_name,
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
        class_level: str = None,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """Search for relevant documents using semantic similarity.

        Searches across one or both collections depending on class_level.

        Args:
            query: Search query (will be embedded)
            doc_type: Filter by document type (optional)
            class_level: Search in specific class ("10", "12", or None for both)
            top_k: Number of top results

        Returns:
            List of relevant documents with relevance scores
        """
        if self.mock_mode:
            return self._mock_search(query, doc_type, class_level, top_k)

        # Determine which collections to search
        collections_to_search = {}
        if class_level:
            if class_level not in self.collection_names:
                raise ValueError(f"Invalid class_level: {class_level}. Must be one of {list(self.collection_names.keys())}")
            collections_to_search = {class_level: self.collection_names[class_level]}
        else:
            collections_to_search = self.collection_names.copy()

        # Generate semantic embedding for query
        query_vector = self._get_embedding(query)

        # Build filter if needed
        filter_expr = None
        if doc_type:
            filter_expr = f'document_type == "{doc_type}"'

        # Semantic search across all target collections
        all_results = []
        for level, collection_name in collections_to_search.items():
            try:
                results = self.client.search(
                    collection_name=collection_name,
                    data=[query_vector],
                    limit=top_k,
                    search_params={"metric_type": "COSINE"},
                    filter=filter_expr,
                    output_fields=["content", "document_type", "metadata"],
                )

                # Format results from this collection
                if results and len(results) > 0:
                    for hit in results[0]:
                        meta = json.loads(hit.get("metadata", "{}"))
                        all_results.append(
                            {
                                "doc_id": meta.get("doc_id"),
                                "content": hit.get("content"),
                                "document_type": hit.get("document_type"),
                                "metadata": meta,
                                "class_level": level,
                                "relevance_score": float(hit.get("distance", 0)),
                            }
                        )
            except Exception as e:
                logger.warning(f"Search failed in {collection_name}: {e}")

        # Sort by relevance score and return top_k
        all_results.sort(key=lambda x: x["relevance_score"], reverse=True)
        return all_results[:top_k]

    def _mock_search(self, query: str, doc_type: str = None, class_level: str = None, top_k: int = 5) -> List[Dict[str, Any]]:
        """Mock search (keyword matching only).

        Args:
            query: Search query
            doc_type: Filter by document type (optional)
            class_level: Filter by class level (optional)
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

            # Apply class_level filter if specified
            if class_level and doc.get("class_level") != class_level:
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
                        "class_level": doc.get("class_level", "12"),
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
        """Get collection statistics for all collections.

        Returns:
            Collection statistics including per-class breakdown
        """
        if self.mock_mode:
            class_10_docs = sum(1 for doc in self.mock_documents.values() if doc.get("class_level") == "10")
            class_12_docs = sum(1 for doc in self.mock_documents.values() if doc.get("class_level") == "12")
            return {
                "mode": "mock",
                "total_documents": len(self.mock_documents),
                "class_10_documents": class_10_docs,
                "class_12_documents": class_12_docs,
                "indexed": True,
            }

        stats_by_class = {}
        total_docs = 0

        for class_level, collection_name in self.collection_names.items():
            try:
                stats = self.client.get_collection_stats(collection_name)
                doc_count = stats.get("row_count", 0)
                stats_by_class[f"class_{class_level}_documents"] = doc_count
                total_docs += doc_count
            except Exception as e:
                logger.warning(f"Failed to get stats for {collection_name}: {e}")
                stats_by_class[f"class_{class_level}_documents"] = 0

        return {
            "mode": "milvus",
            "total_documents": total_docs,
            **stats_by_class,
            "collections": self.collection_names,
            "indexed": True,
            "embedding_model": "all-MiniLM-L6-v2",
            "embedding_dimension": 384,
        }

    def list_all_documents(self) -> List[Dict[str, Any]]:
        """List all stored documents from all collections.

        Returns:
            List of all documents with their metadata and class level
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
                        "class_level": doc.get("class_level", "12"),
                    }
                )
            return result

        formatted_results = []

        # Query all documents from both collections
        for class_level, collection_name in self.collection_names.items():
            try:
                results = self.client.query(
                    collection_name=collection_name,
                    filter="",
                    limit=16384,
                    output_fields=["id", "content", "document_type", "metadata"],
                )

                for doc in results:
                    meta = json.loads(doc.get("metadata", "{}"))
                    formatted_results.append(
                        {
                            "doc_id": meta.get("doc_id"),
                            "content": doc.get("content"),
                            "document_type": doc.get("document_type"),
                            "metadata": meta,
                            "class_level": class_level,
                        }
                    )
            except Exception as e:
                logger.warning(f"Failed to list documents from {collection_name}: {e}")

        return formatted_results

    def close(self):
        """Close Milvus connection."""
        if self.client:
            self.client.close()
