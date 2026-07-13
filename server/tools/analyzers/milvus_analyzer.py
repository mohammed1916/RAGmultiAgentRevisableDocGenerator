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

    def __init__(self, chunks: List[Dict[str, Any]]):
        """Initialize with list of chunks.

        Args:
            chunks: List of chunk dictionaries with 'vector' or 'embedding' field
        """
        self.chunks = chunks
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
        if not self.vectors:
            return {
                "total_embeddings": 0,
                "missing_embeddings": len(self.chunks),
                "coverage": 0.0,
            }

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

        return {
            "total_embeddings": len(self.vectors),
            "missing_embeddings": len(self.chunks) - len(self.vectors),
            "coverage": len(self.vectors) / len(self.chunks) if self.chunks else 0.0,
            "embedding_dimension": len(self.vectors[0]) if self.vectors else 0,
            "avg_norm": avg_norm,
            "stdev_norm": std_norm,
            "avg_nearest_neighbor_distance": avg_nearest_neighbor,
        }


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

        report = {
            "collection": self.rag.collection_name,
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
            embedding_analyzer = EmbeddingAnalyzer(self.chunks)
            report["embedding_analysis"] = embedding_analyzer.analyze()

        # Retrieval analysis
        if test_queries:
            retrieval_analyzer = RetrievalAnalyzer(self.rag)
            report["retrieval_analysis"] = retrieval_analyzer.test_queries(test_queries)

        # Token estimation
        report["token_estimation"] = self._estimate_tokens(chunk_analyzer.analyze())

        return report

    def _estimate_tokens(self, chunk_stats: Dict[str, Any]) -> Dict[str, Any]:
        """Estimate token counts using rough conversion (1 token ≈ 4 chars).

        Args:
            chunk_stats: Chunk statistics dictionary

        Returns:
            Dictionary with token estimates
        """
        return {
            "avg_tokens_per_chunk": int(chunk_stats.get("avg_length", 0) / 4),
            "min_tokens": int(chunk_stats.get("min_length", 0) / 4),
            "max_tokens": int(chunk_stats.get("max_length", 0) / 4),
            "total_estimated_tokens": int(chunk_stats.get("total_chars", 0) / 4),
        }

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

        print(f"\nCollection: {report.get('collection')}")
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
        print("\nEstimated Tokens (1 token ≈ 4 chars)")
        print("-" * 70)
        tokens = report.get("token_estimation", {})
        print(f"  Average              : {tokens.get('avg_tokens_per_chunk', 0)}")
        print(f"  Min                  : {tokens.get('min_tokens', 0)}")
        print(f"  Max                  : {tokens.get('max_tokens', 0)}")
        print(f"  Total                : {tokens.get('total_estimated_tokens', 0)}")

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
            print(f"  Total Embeddings     : {embeddings.get('total_embeddings', 0)}")
            print(f"  Missing Embeddings   : {embeddings.get('missing_embeddings', 0)}")
            print(f"  Coverage             : {embeddings.get('coverage', 0):.1%}")
            print(f"  Dimension            : {embeddings.get('embedding_dimension', 0)}")
            print(f"  Avg Norm             : {embeddings.get('avg_norm', 0):.3f}")
            print(f"  Avg NN Distance      : {embeddings.get('avg_nearest_neighbor_distance', 0):.3f}")

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
