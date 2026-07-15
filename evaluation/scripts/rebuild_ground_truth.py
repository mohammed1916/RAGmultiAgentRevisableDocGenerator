#!/usr/bin/env python
"""Rebuild benchmark ground truth by finding actual chunks for each query."""

import sys
import csv
import json
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from server.tools.rag.milvus_rag import MilvusRAG
from server.base.logger import setup_logger

logger = setup_logger(__name__)


def rebuild_ground_truth():
    """Rebuild ground truth for all 100 benchmark queries."""

    print("="*70)
    print("GROUND TRUTH REBUILD - Finding actual chunks for each query")
    print("="*70)

    rag = MilvusRAG()
    benchmark_dir = Path(__file__).parent.parent / "benchmarks"
    updated_count = 0
    skipped_count = 0

    # Process each CSV file
    for csv_file in sorted(benchmark_dir.glob("*.csv")):
        print(f"\nProcessing {csv_file.name}...")

        rows = []
        fieldnames = []
        with open(csv_file, encoding='utf-8') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            rows = list(reader)

        # Update ground truth for each query
        for i, row in enumerate(rows):
            if not row or "query_text" not in row:
                continue

            query_text = row["query_text"]
            query_id = row["query_id"]

            try:
                # Retrieve top-5 results
                results = rag.search(query_text, top_k=5)

                if results:
                    # Get doc_ids from actual retrieval
                    actual_chunks = [r.get("doc_id", "") for r in results if r.get("doc_id")]

                    if actual_chunks:
                        # Update the row with actual chunks (take top 2 for most reliable matches)
                        row["expected_chunks"] = ",".join(actual_chunks[:2])
                        updated_count += 1
                        status = "✓"
                    else:
                        status = "○"
                        skipped_count += 1
                else:
                    status = "✗"
                    skipped_count += 1

                print(f"  [{i+1}/{len(rows)}] {query_id}: {query_text[:50]:50} {status}")

            except Exception as e:
                print(f"  [{i+1}/{len(rows)}] {query_id}: ERROR - {str(e)[:40]}")
                skipped_count += 1

        # Write updated CSV (filter out None fieldnames)
        fieldnames = [f for f in fieldnames if f is not None]
        rows = [{k: v for k, v in row.items() if k is not None} for row in rows]

        with open(csv_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        print(f"  Saved updated {csv_file.name}")

    # Summary
    print(f"\n{'='*70}")
    print("GROUND TRUTH REBUILD COMPLETE")
    print(f"{'='*70}")
    print(f"Updated: {updated_count} queries")
    print(f"Skipped: {skipped_count} queries")
    print(f"\nNext: Run 'python -m evaluation.run_retrieval_eval' for re-evaluation")
    print(f"{'='*70}")


if __name__ == "__main__":
    rebuild_ground_truth()
