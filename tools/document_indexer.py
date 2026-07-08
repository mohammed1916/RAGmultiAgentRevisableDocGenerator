"""Vector-based document indexing for RAG system.

Implements semantic search using embeddings.
"""

import json
import numpy as np
from typing import List, Dict, Any, Tuple
from pathlib import Path
from logger import setup_logger

logger = setup_logger(__name__)

# Simple embedding simulation (without external dependencies)
class SimpleEmbedder:
    """Simple word-frequency based embeddings (fallback without transformers)."""

    def __init__(self, vocab_size: int = 1000):
        """Initialize the simple embedder.

        Args:
            vocab_size: Maximum vocabulary size
        """
        self.vocab_size = vocab_size
        self.vocabulary = {}
        self.word_count = 0

    def encode(self, text: str) -> np.ndarray:
        """Encode text to a simple embedding vector.

        Args:
            text: Text to encode

        Returns:
            Embedding vector
        """
        words = text.lower().split()
        embedding = np.zeros(self.vocab_size)

        for word in words:
            # Simple hash-based word indexing
            word_idx = hash(word) % self.vocab_size
            embedding[word_idx] += 1.0

        # Normalize
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm

        return embedding

    @staticmethod
    def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between vectors.

        Args:
            vec1: First vector
            vec2: Second vector

        Returns:
            Cosine similarity (0-1)
        """
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)


class DocumentIndexer:
    """Index documents for semantic search and retrieval."""

    def __init__(self, index_dir: str = "document_index"):
        """Initialize the document indexer.

        Args:
            index_dir: Directory to store index
        """
        self.index_dir = Path(index_dir)
        self.index_dir.mkdir(exist_ok=True)

        self.embedder = SimpleEmbedder(vocab_size=2000)
        self.documents: Dict[str, Dict[str, Any]] = {}
        self.embeddings: Dict[str, np.ndarray] = {}
        self.index_file = self.index_dir / "index.json"

        self._load_index()

    def _load_index(self):
        """Load previously indexed documents."""
        if self.index_file.exists():
            with open(self.index_file, "r") as f:
                data = json.load(f)
                self.documents = data.get("documents", {})
            logger.info(f"Loaded index with {len(self.documents)} documents")

    def _save_index(self):
        """Save index to disk."""
        with open(self.index_file, "w") as f:
            json.dump({"documents": self.documents, "count": len(self.documents)}, f, indent=2)

    def add_document(self, doc_id: str, content: str, metadata: Dict[str, Any] = None):
        """Add a document to the index.

        Args:
            doc_id: Unique document ID
            content: Document content
            metadata: Optional metadata
        """
        # Create embedding
        embedding = self.embedder.encode(content)
        self.embeddings[doc_id] = embedding

        # Store document
        self.documents[doc_id] = {
            "id": doc_id,
            "content": content[:1000],  # Store first 1000 chars
            "full_content": content,
            "content_length": len(content),
            "metadata": metadata or {},
        }

        self._save_index()
        logger.info(f"Added document: {doc_id}")

    def add_documents_batch(self, documents: List[Tuple[str, str, Dict]]):
        """Add multiple documents at once.

        Args:
            documents: List of (doc_id, content, metadata) tuples
        """
        for doc_id, content, metadata in documents:
            self.add_document(doc_id, content, metadata)

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search for relevant documents.

        Args:
            query: Search query
            top_k: Number of top results to return

        Returns:
            List of relevant documents with scores
        """
        if not self.documents:
            logger.warning("No documents in index")
            return []

        # Encode query
        query_embedding = self.embedder.encode(query)

        # Score all documents
        scores = []
        for doc_id, embedding in self.embeddings.items():
            similarity = SimpleEmbedder.cosine_similarity(query_embedding, embedding)
            scores.append((doc_id, similarity))

        # Sort by similarity
        scores.sort(key=lambda x: x[1], reverse=True)

        # Return top results
        results = []
        for doc_id, score in scores[:top_k]:
            doc = self.documents[doc_id]
            results.append(
                {
                    "doc_id": doc_id,
                    "content": doc["content"],
                    "full_content": doc["full_content"],
                    "relevance_score": float(round(score, 4)),
                    "metadata": doc.get("metadata", {}),
                }
            )

        logger.info(f"Search for '{query}' returned {len(results)} results")
        return results

    def get_document(self, doc_id: str) -> Dict[str, Any]:
        """Get a document by ID.

        Args:
            doc_id: Document ID

        Returns:
            Document data
        """
        return self.documents.get(doc_id)

    def delete_document(self, doc_id: str):
        """Delete a document from the index.

        Args:
            doc_id: Document ID
        """
        if doc_id in self.documents:
            del self.documents[doc_id]
            if doc_id in self.embeddings:
                del self.embeddings[doc_id]
            self._save_index()
            logger.info(f"Deleted document: {doc_id}")

    def list_documents(self) -> List[Dict[str, Any]]:
        """List all indexed documents.

        Returns:
            List of document metadata
        """
        return [
            {
                "id": doc_id,
                "content_length": doc["content_length"],
                "metadata": doc.get("metadata", {}),
            }
            for doc_id, doc in self.documents.items()
        ]

    def clear_index(self):
        """Clear all documents from the index."""
        self.documents.clear()
        self.embeddings.clear()
        self._save_index()
        logger.info("Index cleared")

    def get_index_stats(self) -> Dict[str, Any]:
        """Get statistics about the index.

        Returns:
            Index statistics
        """
        total_chars = sum(doc["content_length"] for doc in self.documents.values())

        return {
            "total_documents": len(self.documents),
            "total_characters": total_chars,
            "average_doc_size": total_chars / len(self.documents) if self.documents else 0,
            "indexed": True,
        }
