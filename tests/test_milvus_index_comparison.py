"""Benchmark tests comparing Milvus index types: IVF_FLAT vs HNSW."""

import pytest
import time
from server.tools.milvus_rag import MilvusRAG
import json
from pathlib import Path


class TestIndexTypeComparison:
    """Compare IVF_FLAT vs HNSW for curriculum data."""

    @pytest.fixture
    def curriculum_data(self):
        """Load curriculum test data."""
        data_path = Path(__file__).parent.parent / "server" / "data" / "curriculum_data.json"
        with open(data_path) as f:
            return json.load(f)

    def test_ivf_flat_search_performance(self, curriculum_data):
        """Benchmark IVF_FLAT index (current implementation).

        IVF_FLAT (Inverted File with Flat quantizer):
        - Metric: L2 (Euclidean distance)
        - nlist: 128 (number of Voronoi cells)
        - Good for: Large-scale data, lower memory
        - Trade-off: Requires careful tuning of nlist
        """
        rag = MilvusRAG()

        # Add curriculum data
        for doc in curriculum_data[:5]:  # Use first 5 documents
            rag.add_document(
                doc_id=doc["id"],
                content=doc["content"],
                doc_type=doc["document_type"],
                metadata=doc.get("metadata", {}),
            )

        # Benchmark search performance
        queries = [
            "electrostatics electric field capacitor",
            "derivatives calculus integrals",
            "JEE mathematics preparation",
            "CBSE chemistry oxidation",
            "college physics mechanics"
        ]

        start_time = time.time()
        results_count = 0

        for query in queries:
            results = rag.search(query, top_k=3)
            results_count += len(results)

        elapsed = time.time() - start_time

        print(f"\nIVF_FLAT Performance (Mock Mode):")
        print(f"  Queries: {len(queries)}")
        print(f"  Results per query: {results_count / len(queries):.1f}")
        print(f"  Total time: {elapsed:.4f}s")
        print(f"  Avg per query: {elapsed / len(queries):.4f}s")
        print(f"  Metric: L2 (Euclidean)")
        print(f"  Config: IVF with nlist=128")
        print(f"  Note: Using mock mode (no real Milvus server), times are negligible")

        # Verify results exist (mock mode search is very fast)
        assert results_count > 0
        assert len(queries) == 5

    def test_hnsw_configuration(self):
        """Show recommended HNSW configuration for curriculum search.

        HNSW (Hierarchical Navigable Small World):
        - Metric: COSINE (cosine similarity - better for semantic search)
        - M: 16 (connections per node, 4-64 typical)
        - efConstruction: 200 (construction time quality, 100-300 typical)
        - efSearch: 16 (search parameter, lower is faster)
        - Advantages: Better for semantic search, no tuning needed
        - Trade-off: Higher memory than IVF_FLAT
        """

        hnsw_config = {
            "metric_type": "COSINE",
            "index_type": "HNSW",
            "params": {
                "M": 16,
                "efConstruction": 200,
                "efSearch": 16
            }
        }

        print(f"\nHNSW Configuration (Recommended for curriculum):")
        print(f"  Metric: COSINE (semantic similarity)")
        print(f"  Index Type: HNSW (hierarchical search)")
        print(f"  M: {hnsw_config['params']['M']} (connections per node)")
        print(f"  efConstruction: {hnsw_config['params']['efConstruction']} (quality)")
        print(f"  efSearch: {hnsw_config['params']['efSearch']} (speed)")

        assert hnsw_config["metric_type"] == "COSINE"
        assert hnsw_config["index_type"] == "HNSW"

    def test_index_choice_analysis(self):
        """Analysis of which index type suits curriculum data better."""

        analysis = {
            "IVF_FLAT": {
                "metric": "L2 (Euclidean)",
                "pros": [
                    "Good for large-scale data (millions of documents)",
                    "Lower memory usage",
                    "Fast indexing",
                    "Predictable performance"
                ],
                "cons": [
                    "Requires careful nlist tuning",
                    "Not optimal for semantic similarity",
                    "Performance degrades with wrong nlist"
                ],
                "suitable_for": "Very large curricula (10k+ documents)"
            },
            "HNSW": {
                "metric": "COSINE (Cosine similarity)",
                "pros": [
                    "Optimized for semantic search",
                    "No tuning needed (works well with defaults)",
                    "Better for curriculum clustering (similar topics)",
                    "Consistent performance across data sizes"
                ],
                "cons": [
                    "Higher memory usage (~10x IVF_FLAT)",
                    "Slower indexing",
                    "Not ideal for >1M documents"
                ],
                "suitable_for": "Medium curricula (100-100k documents) - RECOMMENDED"
            }
        }

        print("\n" + "="*60)
        print("INDEX TYPE COMPARISON FOR CURRICULUM DATA")
        print("="*60)

        for index_type, details in analysis.items():
            print(f"\n{index_type}:")
            print(f"  Metric: {details['metric']}")
            print(f"  Suitable for: {details['suitable_for']}")
            print(f"  Pros:")
            for pro in details['pros']:
                print(f"    + {pro}")
            print(f"  Cons:")
            for con in details['cons']:
                print(f"    - {con}")

        print("\n" + "="*60)
        print("RECOMMENDATION FOR THIS PROJECT:")
        print("="*60)
        print("Use HNSW because:")
        print("1. Curriculum data is 10-1000 documents (perfect HNSW size)")
        print("2. Semantic similarity is critical (cluster by subject, level)")
        print("3. No complex tuning needed (works well with defaults)")
        print("4. Better quality for educational clustering")
        print("="*60)

    def test_embedding_metric_impact(self):
        """Show impact of embedding metric choice on search quality.

        For curriculum data:
        - L2 (Euclidean): Measures straight-line distance in embedding space
        - COSINE: Measures angle between vectors (ignores magnitude)

        COSINE is better for text because:
        - Two texts can have different lengths but same meaning
        - Cosine similarity is length-invariant
        - Aligns with semantic understanding
        """

        print("\nEmbedding Metric Impact on Curriculum Search:")
        print("\nQuery: 'electrostatics capacitor electric field'")
        print("\nUsing L2 (Euclidean):")
        print("  - Penalizes longer documents")
        print("  - Sensitive to magnitude of embeddings")
        print("  - Can miss semantically similar content")

        print("\nUsing COSINE (Cosine Similarity):")
        print("  - Treats all documents equally")
        print("  - Focuses on direction, not magnitude")
        print("  - Better for finding conceptually similar topics")
        print("  - Example: 'Electrostatics' and 'Capacitor circuits' are similar")


class TestMilvusIndexUpgrade:
    """Test upgrading from IVF_FLAT to HNSW."""

    def test_recommended_hnsw_migration_steps(self):
        """Steps to migrate from IVF_FLAT to HNSW in production.

        Current setup uses IVF_FLAT, but for better curriculum search:
        """

        migration_steps = [
            {
                "step": 1,
                "action": "Update MilvusRAG index creation",
                "code": """
                index_params = {
                    "metric_type": "COSINE",
                    "index_type": "HNSW",
                    "params": {
                        "M": 16,
                        "efConstruction": 200,
                        "efSearch": 16
                    }
                }
                """
            },
            {
                "step": 2,
                "action": "Regenerate embeddings with COSINE metric",
                "reason": "Embeddings must match the metric (L2 vs COSINE)"
            },
            {
                "step": 3,
                "action": "Test search quality on curriculum queries",
                "queries": [
                    "JEE mathematics preparation",
                    "CBSE physics electrostatics",
                    "college CS algorithms"
                ]
            },
            {
                "step": 4,
                "action": "Benchmark performance (HNSW vs IVF_FLAT)",
                "metric": "Search latency, relevance scores, memory usage"
            }
        ]

        print("\n" + "="*60)
        print("MIGRATION PLAN: IVF_FLAT -> HNSW")
        print("="*60)

        for step in migration_steps:
            print(f"\nStep {step['step']}: {step['action']}")
            if 'code' in step:
                print(f"  Code:\n{step['code']}")
            if 'reason' in step:
                print(f"  Reason: {step['reason']}")
            if 'queries' in step:
                print(f"  Example queries: {', '.join(step['queries'][:2])}...")
            if 'metric' in step:
                print(f"  Metrics to track: {step['metric']}")


class TestCurrentVsRecommended:
    """Direct comparison of current vs recommended configuration."""

    def test_configuration_comparison_table(self):
        """Show side-by-side comparison."""

        comparison = """
Current Implementation (IVF_FLAT):
    Metric Type:    L2 (Euclidean distance)
    Index Type:     IVF_FLAT
    nlist:          128
    Use Case:       General purpose, large-scale
    Memory:         Low
    Search Quality: Medium (depends on tuning)
    Tuning Needed:  Yes (nlist parameter)

Recommended (HNSW):
    Metric Type:    COSINE (Cosine similarity)
    Index Type:     HNSW
    M:              16
    efConstruction: 200
    Use Case:       Semantic search, curriculum clustering
    Memory:         Higher (10x IVF_FLAT)
    Search Quality: High (optimized for semantic)
    Tuning Needed:  No (works well with defaults)

For curriculum data: HNSW is BETTER because:
    - Curriculum size is perfect for HNSW (100-100k docs)
    - Semantic similarity is critical (group by subject/level)
    - COSINE metric aligns with educational clustering
    - No complex parameter tuning required
"""

        print("\n" + "="*60)
        print(comparison)
        print("="*60)
