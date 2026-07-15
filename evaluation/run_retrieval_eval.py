#!/usr/bin/env python
"""Retrieval evaluation: Measure Recall@k, Precision@k, MRR, nDCG@k across 100 queries."""

import sys
import json
import csv
import math
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from server.tools.rag.milvus_rag import MilvusRAG
from server.base.logger import setup_logger

logger = setup_logger(__name__)


def calculate_mrr(retrieved_ranks):
    """Calculate Mean Reciprocal Rank."""
    if not retrieved_ranks:
        return 0.0
    return 1.0 / min(retrieved_ranks) if retrieved_ranks else 0.0


def calculate_ndcg(relevance_scores, k=5):
    """Calculate Normalized Discounted Cumulative Gain@k."""
    if not relevance_scores:
        return 0.0

    # DCG calculation
    dcg = sum(rel / math.log2(i + 2) for i, rel in enumerate(relevance_scores[:k]))

    # IDCG calculation (ideal ranking)
    ideal_scores = sorted(relevance_scores, reverse=True)[:k]
    idcg = sum(rel / math.log2(i + 2) for i, rel in enumerate(ideal_scores))

    return dcg / idcg if idcg > 0 else 0.0


def load_benchmark_queries():
    """Load all 100 benchmark questions from CSV files."""
    queries = []
    benchmark_dir = Path(__file__).parent / "benchmark"

    for csv_file in sorted(benchmark_dir.glob("*.csv")):
        with open(csv_file, encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                queries.append({
                    "query_id": row["query_id"],
                    "subject": row["subject"],
                    "chapter": row["chapter"],
                    "query_text": row["query_text"],
                    "ground_truth": row["ground_truth_answer"],
                    "category": row["query_category"],
                    "difficulty": row["difficulty"],
                    "expected_chunks": row["expected_chunks"].split(",")
                })

    return queries


def run_retrieval_evaluation():
    """Run retrieval evaluation on 100 queries."""

    print("="*70)
    print("RETRIEVAL EVALUATION - 100 Query Benchmark")
    print("="*70)

    # Load benchmark
    queries = load_benchmark_queries()
    print(f"\nLoaded {len(queries)} benchmark queries")

    # Initialize RAG
    print("Initializing Milvus RAG...")
    rag = MilvusRAG()

    # Storage for metrics
    results = {
        "timestamp": str(__import__("datetime").datetime.now()),
        "total_queries": len(queries),
        "queries_evaluated": [],
        "metrics_summary": {}
    }

    # Metrics tracking
    recall_at_k = {1: [], 3: [], 5: []}
    precision_at_k = {1: [], 3: [], 5: []}
    mrr_scores = []
    ndcg_scores = {3: [], 5: []}

    category_stats = defaultdict(lambda: {"total": 0, "found": 0})
    difficulty_stats = defaultdict(lambda: {"total": 0, "found": 0})
    subject_stats = defaultdict(lambda: {"total": 0, "found": 0})

    # Run retrieval for each query
    for i, query_data in enumerate(queries, 1):
        print(f"\n[{i}/{len(queries)}] {query_data['query_id']}: {query_data['query_text'][:60]}...")

        try:
            # Retrieve documents
            retrieved = rag.search(query_data["query_text"], top_k=5)
            retrieved_chunk_ids = [r.get("doc_id", "") for r in retrieved]
            expected_chunks = query_data["expected_chunks"]

            # Check if any expected chunk was retrieved
            hits = [1 if chunk in retrieved_chunk_ids else 0 for chunk in expected_chunks]
            any_hit = 1 if any(hits) else 0

            # Calculate metrics
            recall_at_1 = min(sum(hits[:1]) / len(expected_chunks), 1.0) if expected_chunks else 0
            recall_at_3 = min(sum(hits[:3]) / len(expected_chunks), 1.0) if expected_chunks else 0
            recall_at_5 = min(sum(hits[:5]) / len(expected_chunks), 1.0) if expected_chunks else 0

            precision_at_1 = sum(hits[:1]) / 1 if len(retrieved_chunk_ids) >= 1 else 0
            precision_at_3 = sum(hits[:3]) / min(3, len(retrieved_chunk_ids)) if len(retrieved_chunk_ids) >= 1 else 0
            precision_at_5 = sum(hits[:5]) / min(5, len(retrieved_chunk_ids)) if len(retrieved_chunk_ids) >= 1 else 0

            # MRR (if any hit, reciprocal rank of first hit)
            first_hit_rank = next((i + 1 for i, h in enumerate(hits) if h), None)
            mrr = 1.0 / first_hit_rank if first_hit_rank else 0.0

            # nDCG (assuming retrieved == relevant)
            relevance = [1 if cid in retrieved_chunk_ids else 0 for cid in expected_chunks]
            ndcg_3 = calculate_ndcg(relevance, k=3)
            ndcg_5 = calculate_ndcg(relevance, k=5)

            # Store metrics
            recall_at_k[1].append(recall_at_1)
            recall_at_k[3].append(recall_at_3)
            recall_at_k[5].append(recall_at_5)
            precision_at_k[1].append(precision_at_1)
            precision_at_k[3].append(precision_at_3)
            precision_at_k[5].append(precision_at_5)
            mrr_scores.append(mrr)
            ndcg_scores[3].append(ndcg_3)
            ndcg_scores[5].append(ndcg_5)

            # Category/Difficulty/Subject stats
            category_stats[query_data["category"]]["total"] += 1
            if any_hit:
                category_stats[query_data["category"]]["found"] += 1

            difficulty_stats[query_data["difficulty"]]["total"] += 1
            if any_hit:
                difficulty_stats[query_data["difficulty"]]["found"] += 1

            subject_stats[query_data["subject"]]["total"] += 1
            if any_hit:
                subject_stats[query_data["subject"]]["found"] += 1

            # Store query result
            results["queries_evaluated"].append({
                "query_id": query_data["query_id"],
                "recall_at_5": round(recall_at_5, 4),
                "precision_at_5": round(precision_at_5, 4),
                "mrr": round(mrr, 4),
                "ndcg_at_5": round(ndcg_5, 4),
                "hit": any_hit
            })

            print(f"  Recall@5: {recall_at_5:.2%} | MRR: {mrr:.3f} | nDCG@5: {ndcg_5:.3f}")

        except Exception as e:
            logger.error(f"Error evaluating query {query_data['query_id']}: {e}")
            results["queries_evaluated"].append({
                "query_id": query_data["query_id"],
                "error": str(e)
            })

    # Calculate summary statistics
    results["metrics_summary"] = {
        "recall_at_1": round(sum(recall_at_k[1]) / len(recall_at_k[1]), 4) if recall_at_k[1] else 0,
        "recall_at_3": round(sum(recall_at_k[3]) / len(recall_at_k[3]), 4) if recall_at_k[3] else 0,
        "recall_at_5": round(sum(recall_at_k[5]) / len(recall_at_k[5]), 4) if recall_at_k[5] else 0,
        "precision_at_1": round(sum(precision_at_k[1]) / len(precision_at_k[1]), 4) if precision_at_k[1] else 0,
        "precision_at_3": round(sum(precision_at_k[3]) / len(precision_at_k[3]), 4) if precision_at_k[3] else 0,
        "precision_at_5": round(sum(precision_at_k[5]) / len(precision_at_k[5]), 4) if precision_at_k[5] else 0,
        "mean_reciprocal_rank": round(sum(mrr_scores) / len(mrr_scores), 4) if mrr_scores else 0,
        "ndcg_at_3": round(sum(ndcg_scores[3]) / len(ndcg_scores[3]), 4) if ndcg_scores[3] else 0,
        "ndcg_at_5": round(sum(ndcg_scores[5]) / len(ndcg_scores[5]), 4) if ndcg_scores[5] else 0,
        "hit_rate": round(sum(1 for q in results["queries_evaluated"] if q.get("hit")) / len(results["queries_evaluated"]), 4) if results["queries_evaluated"] else 0,
    }

    # Category breakdown
    results["category_breakdown"] = {
        cat: {
            "total": stats["total"],
            "found": stats["found"],
            "hit_rate": round(stats["found"] / stats["total"], 2) if stats["total"] > 0 else 0
        }
        for cat, stats in sorted(category_stats.items())
    }

    # Difficulty breakdown
    results["difficulty_breakdown"] = {
        diff: {
            "total": stats["total"],
            "found": stats["found"],
            "hit_rate": round(stats["found"] / stats["total"], 2) if stats["total"] > 0 else 0
        }
        for diff, stats in sorted(difficulty_stats.items())
    }

    # Subject breakdown
    results["subject_breakdown"] = {
        subj: {
            "total": stats["total"],
            "found": stats["found"],
            "hit_rate": round(stats["found"] / stats["total"], 2) if stats["total"] > 0 else 0
        }
        for subj, stats in sorted(subject_stats.items())
    }

    # Save results
    output_file = Path(__file__).parent / "retrieval_metrics.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)

    # Print summary
    print(f"\n{'='*70}")
    print("RETRIEVAL METRICS SUMMARY")
    print(f"{'='*70}")
    print(f"Recall@1:    {results['metrics_summary']['recall_at_1']:.2%}")
    print(f"Recall@3:    {results['metrics_summary']['recall_at_3']:.2%}")
    print(f"Recall@5:    {results['metrics_summary']['recall_at_5']:.2%}")
    print(f"Precision@5: {results['metrics_summary']['precision_at_5']:.2%}")
    print(f"MRR:         {results['metrics_summary']['mean_reciprocal_rank']:.3f}")
    print(f"nDCG@5:      {results['metrics_summary']['ndcg_at_5']:.3f}")
    print(f"Hit Rate:    {results['metrics_summary']['hit_rate']:.2%}")
    print(f"\nResults saved to: {output_file}")
    print(f"{'='*70}")


if __name__ == "__main__":
    run_retrieval_evaluation()
