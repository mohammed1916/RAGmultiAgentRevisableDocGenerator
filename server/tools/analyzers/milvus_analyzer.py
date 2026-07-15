"""Milvus collection analysis tools for RAG quality inspection.

Provides modular analyzers to inspect and validate RAG pipeline data stored in Milvus.
"""

import json
import statistics
from typing import Dict, List, Any, Optional
from collections import defaultdict
import numpy as np

from server.tools.rag.milvus_rag import MilvusRAG
from server.base.logger import setup_logger

logger = setup_logger(__name__)


class ChunkAnalyzer:
    """Analyzes chunk statistics and quality metrics."""

    def __init__(self, chunks: List[Dict[str, Any]]):
        """Initialize with list of chunks.

        Args:
            chunks: List of chunk dictionaries with 'content' field
        """
        self.chunks = chunks
        self.lengths = [len(chunk.get("content", "")) for chunk in chunks]

    def analyze(self) -> Dict[str, Any]:
        """Analyze chunk statistics.

        Returns:
            Dictionary with chunk statistics
        """
        if not self.lengths:
            return {"error": "No chunks to analyze"}

        return {
            "total_chunks": len(self.chunks),
            "min_length": min(self.lengths),
            "max_length": max(self.lengths),
            "avg_length": statistics.mean(self.lengths),
            "median_length": statistics.median(self.lengths),
            "stdev_length": statistics.stdev(self.lengths) if len(self.lengths) > 1 else 0,
            "total_chars": sum(self.lengths),
        }

    def get_quality_report(self) -> Dict[str, Any]:
        """Get quality metrics.

        Returns:
            Dictionary with quality issues
        """
        empty_chunks = sum(1 for length in self.lengths if length == 0)
        small_chunks = sum(1 for length in self.lengths if 0 < length < 50)
        large_chunks = sum(1 for length in self.lengths if length > 1000)

        # Check for duplicates
        content_hashes = defaultdict(list)
        for i, chunk in enumerate(self.chunks):
            content = chunk.get("content", "")
            content_hash = hash(content)
            content_hashes[content_hash].append(i)

        duplicates = sum(1 for v in content_hashes.values() if len(v) > 1)

        return {
            "empty_chunks": empty_chunks,
            "duplicate_chunks": duplicates,
            "chunks_under_50_chars": small_chunks,
            "chunks_over_1000_chars": large_chunks,
        }


class MetadataAnalyzer:
    """Analyzes metadata distribution and statistics."""

    def __init__(self, chunks: List[Dict[str, Any]]):
        """Initialize with list of chunks.

        Args:
            chunks: List of chunk dictionaries with 'metadata' field
        """
        self.chunks = chunks
        self.metadata = [
            json.loads(chunk.get("metadata", "{}"))
            if isinstance(chunk.get("metadata"), str)
            else chunk.get("metadata", {})
            for chunk in chunks
        ]

    def analyze(self) -> Dict[str, Any]:
        """Analyze metadata distribution.

        Returns:
            Dictionary with metadata statistics
        """
        doc_types = defaultdict(int)
        topics = defaultdict(int)
        other_fields = defaultdict(int)

        for meta in self.metadata:
            if "document_type" in meta or "doc_type" in meta:
                doc_type = meta.get("document_type") or meta.get("doc_type")
                doc_types[str(doc_type)] += 1

            if "topic" in meta:
                topic = meta.get("topic")
                topics[str(topic)] += 1

            # Track other metadata fields
            for key, value in meta.items():
                if key not in ["document_type", "doc_type", "topic", "chunk_index", "doc_id"]:
                    other_fields[key] += 1

        return {
            "document_types": dict(sorted(doc_types.items(), key=lambda x: x[1], reverse=True)),
            "topics": dict(sorted(topics.items(), key=lambda x: x[1], reverse=True)),
            "other_fields": dict(other_fields),
        }


class EmbeddingAnalyzer:
    """Analyzes embedding quality and statistics."""

    def __init__(self, chunks: List[Dict[str, Any]], embedding_model=None):
        """Initialize with list of chunks.

        Args:
            chunks: List of chunk dictionaries with 'vector' or 'embedding' field
            embedding_model: Optional SentenceTransformer model for actual token counting
        """
        self.chunks = chunks
        self.embedding_model = embedding_model
        self.vectors = []
        for chunk in chunks:
            vec = chunk.get("vector") or chunk.get("embedding")
            if vec:
                self.vectors.append(vec)

    def analyze(self) -> Dict[str, Any]:
        """Analyze embedding statistics.

        Returns:
            Dictionary with embedding metrics
        """
        # Vector-based metrics (only if vectors are available).
        # Note: Milvus query() does not return the vector field, so this
        # section is typically empty when analyzing a live collection.
        if not self.vectors:
            result = {
                "total_embeddings": 0,
                "missing_embeddings": len(self.chunks),
                "coverage": 0.0,
                "vectors_available": False,
            }
        else:
            vectors = np.array(self.vectors)

            # Calculate statistics
            norms = np.linalg.norm(vectors, axis=1)
            avg_norm = float(np.mean(norms))
            std_norm = float(np.std(norms)) if len(norms) > 1 else 0.0

            # Find nearest neighbors (expensive for large sets, sample if needed)
            avg_nearest_neighbor = 0.0
            if len(vectors) > 1:
                # Sample for performance if > 1000 vectors
                sample_size = min(100, len(vectors))
                sample_indices = np.random.choice(len(vectors), sample_size, replace=False)

                distances = []
                for i in sample_indices:
                    # Compute distance to all others
                    dists = np.linalg.norm(vectors - vectors[i], axis=1)
                    # Second smallest (smallest is self)
                    dists_sorted = np.sort(dists)
                    if len(dists_sorted) > 1:
                        distances.append(float(dists_sorted[1]))

                avg_nearest_neighbor = float(np.mean(distances)) if distances else 0.0

            result = {
                "total_embeddings": len(self.vectors),
                "missing_embeddings": len(self.chunks) - len(self.vectors),
                "coverage": len(self.vectors) / len(self.chunks) if self.chunks else 0.0,
                "embedding_dimension": len(self.vectors[0]) if self.vectors else 0,
                "avg_norm": avg_norm,
                "stdev_norm": std_norm,
                "avg_nearest_neighbor_distance": avg_nearest_neighbor,
                "vectors_available": True,
            }

        # Get actual token counts if model provided.
        # This works from chunk content, so it runs even without vectors.
        if self.embedding_model:
            token_stats = self._get_actual_token_stats()
            result.update(token_stats)

        return result

    def _get_actual_token_stats(self) -> Dict[str, Any]:
        """Get actual token counts using the embedding model's tokenizer.

        Returns:
            Dictionary with token statistics
        """
        try:
            token_counts = []
            for chunk in self.chunks:
                content = chunk.get("content", "")
                if content:
                    # Tokenize using the model's tokenizer
                    tokens = self.embedding_model.tokenize([content])
                    token_count = len(tokens["input_ids"][0])
                    token_counts.append(token_count)

            if token_counts:
                return {
                    "total_tokens_actual": sum(token_counts),
                    "avg_tokens_actual": float(statistics.mean(token_counts)),
                    "min_tokens_actual": min(token_counts),
                    "max_tokens_actual": max(token_counts),
                    "token_counting_method": "sentence-transformers tokenizer",
                }
        except Exception as e:
            logger.warning(f"Could not compute actual token counts: {e}")

        return {}


class RetrievalAnalyzer:
    """Analyzes retrieval quality and performance."""

    def __init__(self, rag: MilvusRAG):
        """Initialize with RAG instance.

        Args:
            rag: MilvusRAG instance
        """
        self.rag = rag

    def test_queries(self, test_queries: List[str], top_k: int = 5) -> Dict[str, Any]:
        """Test retrieval with sample queries.

        Args:
            test_queries: List of test queries
            top_k: Number of top results to retrieve

        Returns:
            Dictionary with query results
        """
        results = {}

        for query in test_queries:
            try:
                retrieved = self.rag.search(query, top_k=top_k)
                results[query] = {
                    "results_found": len(retrieved),
                    "top_scores": [r.get("relevance_score", 0) for r in retrieved],
                    "results": [
                        {
                            "doc_id": r.get("doc_id"),
                            "score": r.get("relevance_score"),
                            "content_preview": r.get("content", "")[:100],
                        }
                        for r in retrieved
                    ],
                }
            except Exception as e:
                results[query] = {"error": str(e)}

        return results


class ReportGenerator:
    """Generates comprehensive analysis reports."""

    def __init__(self, rag: MilvusRAG):
        """Initialize with RAG instance.

        Args:
            rag: MilvusRAG instance
        """
        self.rag = rag
        self.chunks = None

    def _load_chunks(self) -> bool:
        """Load all chunks from Milvus.

        Returns:
            True if successful, False otherwise
        """
        try:
            self.chunks = self.rag.list_all_documents()
            return len(self.chunks) > 0
        except Exception as e:
            logger.error(f"Failed to load chunks: {e}")
            return False

    def generate_full_report(
        self,
        include_embeddings: bool = True,
        test_queries: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Generate comprehensive analysis report.

        Args:
            include_embeddings: Include embedding analysis
            test_queries: Optional list of test queries

        Returns:
            Dictionary with full analysis
        """
        if not self._load_chunks():
            return {"error": "Could not load chunks from Milvus"}

        # Get collection names (MilvusRAG uses collection_names dict)
        collection_info = list(self.rag.collection_names.values()) if hasattr(self.rag, 'collection_names') else ["unknown"]

        report = {
            "collections": collection_info,
            "timestamp": str(__import__("datetime").datetime.now()),
        }

        # Chunk analysis
        chunk_analyzer = ChunkAnalyzer(self.chunks)
        report["chunk_statistics"] = chunk_analyzer.analyze()
        report["quality_report"] = chunk_analyzer.get_quality_report()

        # Metadata analysis
        metadata_analyzer = MetadataAnalyzer(self.chunks)
        report["metadata_analysis"] = metadata_analyzer.analyze()

        # Embedding analysis
        if include_embeddings:
            # Try to load embedding model for actual token counting
            embedding_model = None
            try:
                if hasattr(self.rag, 'embedding_model') and self.rag.embedding_model:
                    embedding_model = self.rag.embedding_model
                elif hasattr(self.rag, 'embedding_model_name') and not self.rag.mock_mode:
                    from sentence_transformers import SentenceTransformer
                    embedding_model = SentenceTransformer(self.rag.embedding_model_name)
            except Exception as e:
                logger.warning(f"Could not load embedding model for token counting: {e}")

            embedding_analyzer = EmbeddingAnalyzer(self.chunks, embedding_model=embedding_model)
            report["embedding_analysis"] = embedding_analyzer.analyze()

        # Retrieval analysis
        if test_queries:
            retrieval_analyzer = RetrievalAnalyzer(self.rag)
            report["retrieval_analysis"] = retrieval_analyzer.test_queries(test_queries)

        # Token estimation
        chunk_stats = chunk_analyzer.analyze()
        embedding_stats = report.get("embedding_analysis", {})
        report["token_estimation"] = self._estimate_tokens(chunk_stats, embedding_stats)

        return report

    def _estimate_tokens(self, chunk_stats: Dict[str, Any], embedding_stats: Dict[str, Any] = None) -> Dict[str, Any]:
        """Estimate and/or report token counts.

        Args:
            chunk_stats: Chunk statistics dictionary
            embedding_stats: Optional embedding statistics with actual token counts

        Returns:
            Dictionary with token estimates and actual counts
        """
        result = {
            "estimate_method": "4-char approximation (rough)",
            "avg_tokens_estimate": int(chunk_stats.get("avg_length", 0) / 4),
            "min_tokens_estimate": int(chunk_stats.get("min_length", 0) / 4),
            "max_tokens_estimate": int(chunk_stats.get("max_length", 0) / 4),
            "total_tokens_estimate": int(chunk_stats.get("total_chars", 0) / 4),
        }

        # If actual tokens were computed, add them
        if embedding_stats:
            if "total_tokens_actual" in embedding_stats:
                result.update({
                    "total_tokens_actual": embedding_stats.get("total_tokens_actual"),
                    "avg_tokens_actual": embedding_stats.get("avg_tokens_actual"),
                    "min_tokens_actual": embedding_stats.get("min_tokens_actual"),
                    "max_tokens_actual": embedding_stats.get("max_tokens_actual"),
                    "token_counting_method": embedding_stats.get("token_counting_method"),
                    "estimate_accuracy": f"{(embedding_stats.get('total_tokens_actual', 0) / result['total_tokens_estimate'] * 100 if result['total_tokens_estimate'] > 0 else 0):.1f}%",
                })

        return result

    def print_report(self, report: Dict[str, Any]) -> None:
        """Pretty-print the analysis report.

        Args:
            report: Report dictionary from generate_full_report()
        """
        if "error" in report:
            print(f"\n[ERROR] {report['error']}")
            return

        print("\n" + "=" * 70)
        print("MILVUS COLLECTION ANALYSIS")
        print("=" * 70)

        collections = report.get('collections', [])
        print(f"\nCollections: {', '.join(collections) if collections else 'unknown'}")
        print(f"Analyzed: {report.get('timestamp')}")

        # Chunk statistics
        print("\nChunk Statistics")
        print("-" * 70)
        chunk_stats = report.get("chunk_statistics", {})
        print(f"  Total Chunks         : {chunk_stats.get('total_chunks', 0)}")
        print(f"  Min Length           : {chunk_stats.get('min_length', 0)} chars")
        print(f"  Max Length           : {chunk_stats.get('max_length', 0)} chars")
        print(f"  Average Length       : {chunk_stats.get('avg_length', 0):.1f} chars")
        print(f"  Median Length        : {chunk_stats.get('median_length', 0)} chars")
        print(f"  Total Content        : {chunk_stats.get('total_chars', 0)} chars")

        # Token estimation
        print("\nToken Analysis")
        print("-" * 70)
        tokens = report.get("token_estimation", {})

        # Show estimate method
        print(f"  Estimate Method      : {tokens.get('estimate_method', 'N/A')}")

        # Estimated tokens
        print(f"\n  Estimated (4-char):")
        print(f"    Average            : {tokens.get('avg_tokens_estimate', 0)}")
        print(f"    Min                : {tokens.get('min_tokens_estimate', 0)}")
        print(f"    Max                : {tokens.get('max_tokens_estimate', 0)}")
        print(f"    Total              : {tokens.get('total_tokens_estimate', 0)}")

        # Actual tokens (if available)
        if "total_tokens_actual" in tokens:
            print(f"\n  Actual ({tokens.get('token_counting_method', 'tokenizer')}):")
            print(f"    Average            : {tokens.get('avg_tokens_actual', 0):.1f}")
            print(f"    Min                : {tokens.get('min_tokens_actual', 0)}")
            print(f"    Max                : {tokens.get('max_tokens_actual', 0)}")
            print(f"    Total              : {tokens.get('total_tokens_actual', 0)}")
            print(f"\n  Accuracy             : {tokens.get('estimate_accuracy', 'N/A')} (actual vs estimate)")

        # Quality report
        print("\nQuality Report")
        print("-" * 70)
        quality = report.get("quality_report", {})
        print(f"  Empty Chunks         : {quality.get('empty_chunks', 0)}")
        print(f"  Duplicate Chunks     : {quality.get('duplicate_chunks', 0)}")
        print(f"  Chunks < 50 chars    : {quality.get('chunks_under_50_chars', 0)}")
        print(f"  Chunks > 1000 chars  : {quality.get('chunks_over_1000_chars', 0)}")

        # Metadata analysis
        metadata = report.get("metadata_analysis", {})
        if metadata.get("document_types"):
            print("\nDocument Types")
            print("-" * 70)
            for doc_type, count in list(metadata["document_types"].items())[:10]:
                print(f"  {doc_type:<30} : {count}")

        if metadata.get("topics"):
            print("\nTopics")
            print("-" * 70)
            for topic, count in list(metadata["topics"].items())[:10]:
                print(f"  {topic:<30} : {count}")

        # Embedding analysis
        if "embedding_analysis" in report:
            print("\nEmbedding Analysis")
            print("-" * 70)
            embeddings = report["embedding_analysis"]
            if embeddings.get("vectors_available"):
                print(f"  Total Embeddings     : {embeddings.get('total_embeddings', 0)}")
                print(f"  Missing Embeddings   : {embeddings.get('missing_embeddings', 0)}")
                print(f"  Coverage             : {embeddings.get('coverage', 0):.1%}")
                print(f"  Dimension            : {embeddings.get('embedding_dimension', 0)}")
                print(f"  Avg Norm             : {embeddings.get('avg_norm', 0):.3f}")
                print(f"  Avg NN Distance      : {embeddings.get('avg_nearest_neighbor_distance', 0):.3f}")
            else:
                print("  Vectors not returned by Milvus query() API.")
                print("  (Vector stats unavailable; token counts shown above are exact.)")

        # Retrieval analysis
        if "retrieval_analysis" in report:
            print("\nRetrieval Analysis")
            print("-" * 70)
            retrieval = report["retrieval_analysis"]
            for query, results in retrieval.items():
                if "error" in results:
                    print(f"  Query: {query} → ERROR: {results['error']}")
                else:
                    print(f"  Query: {query}")
                    print(f"    Results Found    : {results.get('results_found', 0)}")
                    scores = results.get("top_scores", [])
                    if scores:
                        print(f"    Top Score        : {scores[0]:.3f}")
                        print(f"    Avg Score        : {statistics.mean(scores):.3f}")

        print("\n" + "=" * 70)
