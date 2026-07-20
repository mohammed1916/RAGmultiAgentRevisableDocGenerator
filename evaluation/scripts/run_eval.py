#!/usr/bin/env python
"""Unified evaluation script for RAG system.

Modes:
  - retrieval   : Measure Recall@k, Precision@k, MRR, nDCG@k
  - generate-bm : Generate benchmark from curriculum chunks
"""

import sys
import argparse
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from server.base.logger import setup_logger

logger = setup_logger(__name__)


def get_log_file(mode: str) -> Path:
    """Get timestamped log file for this evaluation run."""
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    logs_dir = Path(__file__).parent.parent / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir / f"{mode}_{timestamp}.log"


def run_retrieval_eval():
    """Run retrieval evaluation on benchmark."""
    from .run_retrieval_eval import run_retrieval_evaluation
    print("Starting retrieval evaluation...")
    run_retrieval_evaluation()


def generate_benchmark():
    """Generate benchmark from curriculum chunks."""
    from .generate_curriculum_benchmark import generate_curriculum_benchmark
    print("Starting curriculum benchmark generation...")
    output_csv, queries = generate_curriculum_benchmark()
    print(f"\nGenerated {len(queries)} benchmark queries")
    print(f"Next: python -m evaluation.scripts.run_eval --mode retrieval")


def main():
    parser = argparse.ArgumentParser(
        description="Unified RAG evaluation framework",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m evaluation.scripts.run_eval --mode retrieval
  python -m evaluation.scripts.run_eval --mode generate-bm
        """
    )

    parser.add_argument(
        "--mode",
        choices=["retrieval", "generate-bm"],
        default="retrieval",
        help="Evaluation mode (default: retrieval)"
    )

    parser.add_argument(
        "--benchmark",
        type=str,
        default=None,
        help="Path to benchmark CSV (default: benchmarks/curriculum_generated.csv)"
    )

    args = parser.parse_args()

    # Log file setup
    log_file = get_log_file(args.mode)
    print(f"Logging to: {log_file}")

    # Route to appropriate function
    modes = {
        "retrieval": run_retrieval_eval,
        "generate-bm": generate_benchmark,
    }

    try:
        modes[args.mode]()
        print(f"\n[OK] {args.mode} evaluation complete")
    except Exception as e:
        logger.error(f"Evaluation failed: {e}", exc_info=True)
        print(f"\n[ERROR] {args.mode} evaluation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
