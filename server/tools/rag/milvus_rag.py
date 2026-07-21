"""Milvus-based RAG system with real semantic embeddings.

Uses sentence-transformers for genuine semantic embeddings,
Milvus for vector storage and ANN search.
"""

import json
import socket
from typing import List, Dict, Any, Optional

from ...base.logger import setup_logger

try:
    from pymilvus import MilvusClient, DataType
except ImportError:
    print("WARNING: pymilvus not installed. Install with: pip install pymilvus>=3.0")

# Dedicated collection for user-ingested, profile-scoped chunks. Uses an explicit
# schema so profile_id is a filterable scalar field (Milvus only supports exact /
# prefix matches in filter expressions, not infix JSON matching).
PROFILE_CHUNKS_COLLECTION = "learning_profile_chunks"
EMBEDDING_DIM = 384

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

        # if Milvus or the embedding model is unavailable the caller
        # decides how to degrade.
        self._connect()
        self._create_collections()
        self._load_embedding_model()

    def _load_embedding_model(self):
        """Load the sentence-transformers embedding model."""
        if self.embedding_model is None:
            self.embedding_model = SentenceTransformer(self.embedding_model_name)

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

    def _ensure_profile_collection(self) -> None:
        """Create the profile-scoped chunk collection with an explicit schema.

        Unlike the auto-schema class collections, this collection promotes
        ``profile_id`` (and other identity fields) to top-level scalar fields so
        retrieval can filter with an exact ``profile_id == "..."`` expression.
        """
        if self.client.has_collection(PROFILE_CHUNKS_COLLECTION):
            return

        schema = self.client.create_schema(auto_id=True, enable_dynamic_field=True)
        schema.add_field("id", DataType.INT64, is_primary=True)
        schema.add_field("vector", DataType.FLOAT_VECTOR, dim=EMBEDDING_DIM)
        schema.add_field("content", DataType.VARCHAR, max_length=8192)
        schema.add_field("profile_id", DataType.VARCHAR, max_length=64)
        schema.add_field("user_id", DataType.VARCHAR, max_length=64)
        schema.add_field("subject", DataType.VARCHAR, max_length=128)
        schema.add_field("chapter", DataType.VARCHAR, max_length=128)
        schema.add_field("source", DataType.VARCHAR, max_length=256)
        schema.add_field("doc_id", DataType.VARCHAR, max_length=64)

        index_params = self.client.prepare_index_params()
        index_params.add_index(field_name="vector", metric_type="COSINE", index_type="AUTOINDEX")
        self.client.create_collection(
            collection_name=PROFILE_CHUNKS_COLLECTION,
            schema=schema,
            index_params=index_params,
        )
        logger.info("Created profile chunk collection: %s", PROFILE_CHUNKS_COLLECTION)

    def add_profile_chunk(
        self,
        *,
        content: str,
        profile_id: str,
        user_id: str,
        doc_id: str,
        subject: Optional[str] = None,
        chapter: Optional[str] = None,
        source: str = "text",
    ) -> None:
        """Embed and store one profile-scoped chunk."""
        self._ensure_profile_collection()
        vector = self._get_embedding(content)
        self.client.insert(
            collection_name=PROFILE_CHUNKS_COLLECTION,
            data=[{
                "vector": vector,
                "content": content[:8192],
                "profile_id": profile_id,
                "user_id": user_id,
                "subject": (subject or "")[:128],
                "chapter": (chapter or "")[:128],
                "source": (source or "")[:256],
                "doc_id": doc_id,
            }],
        )

    def search_profile_chunks(
        self,
        query: str,
        profile_id: str,
        top_k: int = 20,
    ) -> List[Dict[str, Any]]:
        """Vector search restricted to a single profile via exact-match filter."""
        if not self.client.has_collection(PROFILE_CHUNKS_COLLECTION):
            return []
        query_vector = self._get_embedding(query)
        results = self.client.search(
            collection_name=PROFILE_CHUNKS_COLLECTION,
            data=[query_vector],
            limit=top_k,
            search_params={"metric_type": "COSINE"},
            filter=f'profile_id == "{self._escape_filter_value(profile_id)}"',
            output_fields=["content", "profile_id", "user_id", "subject", "chapter", "source", "doc_id"],
        )
        out: List[Dict[str, Any]] = []
        if results and results[0]:
            for hit in results[0]:
                entity = hit.get("entity", hit)
                out.append({
                    "content": entity.get("content"),
                    "profile_id": entity.get("profile_id"),
                    "subject": entity.get("subject"),
                    "chapter": entity.get("chapter"),
                    "source": entity.get("source"),
                    "doc_id": entity.get("doc_id"),
                    "relevance_score": float(hit.get("distance", 0)),
                })
        return out

    def delete_profile_chunks(self, profile_id: str, doc_id: Optional[str] = None) -> None:
        """Delete a profile's ingested chunks, optionally scoped to one doc_id."""
        if not self.client.has_collection(PROFILE_CHUNKS_COLLECTION):
            return
        expr = f'profile_id == "{self._escape_filter_value(profile_id)}"'
        if doc_id is not None:
            expr += f' and doc_id == "{self._escape_filter_value(doc_id)}"'
        try:
            # Resolve matching primary keys, then delete by pk (Milvus deletes
            # only support pk-in expressions on this collection schema).
            rows = self.client.query(
                collection_name=PROFILE_CHUNKS_COLLECTION,
                filter=expr,
                output_fields=["id"],
                limit=16384,
            )
            ids = [row["id"] for row in rows if "id" in row]
            if ids:
                self.client.delete(collection_name=PROFILE_CHUNKS_COLLECTION, ids=ids)
        except Exception as e:
            logger.warning(f"Delete profile chunks failed: {e}")

    def list_profile_chunks(self, profile_id: str, limit: int = 500) -> List[Dict[str, Any]]:
        """Return a profile's stored chunks (content + identity) for corpus analysis."""
        if not self.client.has_collection(PROFILE_CHUNKS_COLLECTION):
            return []
        try:
            return self.client.query(
                collection_name=PROFILE_CHUNKS_COLLECTION,
                filter=f'profile_id == "{self._escape_filter_value(profile_id)}"',
                limit=limit,
                output_fields=["content", "subject", "chapter", "source", "doc_id"],
            )
        except Exception as e:
            logger.warning(f"List profile chunks failed: {e}")
            return []

    def recreate_collections(self):
        """Drop both collections if they exist and create fresh ones.

        Used when fully replacing the indexed data (e.g. re-ingesting from source).
        """
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
        if self.embedding_model is None:
            self._load_embedding_model()
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
        Kept for backward compatibility; prefer search_collections() for new code.

        Args:
            query: Search query (will be embedded)
            doc_type: Filter by document type (optional)
            class_level: Search in specific class ("10", "12", or None for both)
            top_k: Number of top results

        Returns:
            List of relevant documents with relevance scores
        """
        # Convert class_level to collection names
        if class_level:
            if class_level not in self.collection_names:
                raise ValueError(f"Invalid class_level: {class_level}. Must be one of {list(self.collection_names.keys())}")
            collection_list = [self.collection_names[class_level]]
        else:
            collection_list = list(self.collection_names.values())

        return self.search_collections(query, collection_list, doc_type, top_k)

    def search_collections(
        self,
        query: str,
        collection_names: List[str],
        doc_type: str = None,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """Search for relevant documents across specified collections.

        This is the primary search method for routing-based collection selection.
        Allows searching arbitrary collections without prior knowledge of structure.

        For profile-scoped (identity-based) retrieval use
        :meth:`search_profile_chunks`, which filters on an indexed ``profile_id``
        scalar field (Milvus filter expressions do not support infix matching on
        the JSON metadata blob).

        Args:
            query: Search query (will be embedded)
            collection_names: List of collection names to search
            doc_type: Filter by document type (optional)
            top_k: Number of top results

        Returns:
            List of relevant documents with relevance scores from all collections
        """
        if not collection_names:
            raise ValueError("No collections specified for search")

        # Generate semantic embedding for query
        query_vector = self._get_embedding(query)

        # Build filter if needed (escape user input to avoid expression injection)
        filter_expr = None
        if doc_type:
            filter_expr = f'document_type == "{self._escape_filter_value(doc_type)}"'

        # Semantic search across specified collections
        all_results = []
        for collection_name in collection_names:
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
                                "collection": collection_name,
                                "relevance_score": float(hit.get("distance", 0)),
                            }
                        )
            except Exception as e:
                logger.warning(f"Search failed in {collection_name}: {e}")

        # Sort by relevance score and return top_k
        all_results.sort(key=lambda x: x["relevance_score"], reverse=True)
        return all_results[:top_k]

    def delete_document(self, doc_id: str):
        """Delete document from Milvus.

        Args:
            doc_id: Document ID to delete
        """
        safe_id = self._escape_filter_value(doc_id)
        for collection_name in self.collection_names.values():
            try:
                self.client.delete(
                    collection_name=collection_name,
                    filter=f'metadata["doc_id"] == "{safe_id}"',
                )
            except Exception as e:
                logger.warning(f"Delete failed in {collection_name}: {e}")

    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific document.

        Args:
            doc_id: Document ID

        Returns:
            Document data or None
        """
        safe_id = self._escape_filter_value(doc_id)
        for collection_name in self.collection_names.values():
            try:
                results = self.client.query(
                    collection_name=collection_name,
                    filter=f'metadata["doc_id"] == "{safe_id}"',
                    limit=1,
                    output_fields=["*"],
                )
                if results:
                    return results[0]
            except Exception as e:
                logger.warning(f"Query failed in {collection_name}: {e}")
        return None

    @staticmethod
    def _escape_filter_value(value: str) -> str:
        """Escape a user-supplied value for safe use inside a Milvus filter string.

        Milvus filter expressions are double-quoted strings; a stray quote or
        backslash would let a caller inject expression syntax. Strip control
        characters and escape backslashes and double quotes.
        """
        cleaned = "".join(ch for ch in str(value) if ch.isprintable())
        return cleaned.replace("\\", "\\\\").replace('"', '\\"')

    def get_stats(self) -> Dict[str, Any]:
        """Get collection statistics for all collections.

        Returns:
            Collection statistics including per-class breakdown
        """
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
