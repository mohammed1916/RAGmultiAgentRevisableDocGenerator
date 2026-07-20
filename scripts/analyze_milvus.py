#!/usr/bin/env python
"""Analyze Milvus collection for RAG quality inspection.

Produces detailed reports on collection statistics, metadata, embeddings,
and retrieval quality.

Usage:
    python analyze_milvus.py                      # Full analysis
    python analyze_milvus.py --no-embeddings      # Skip embedding analysis
    python analyze_milvus.py --query "calculus"   # Add retrieval test
    python analyze_milvus.py --query "q1" --query "q2"  # Multiple queries
    python analyze_milvus.py --output report.json # Save to file
"""

import sys
import io
import json
import argparse
from pathlib import Path

# Fix Windows console encoding issues with UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from server.tools.rag.milvus_rag import MilvusRAG
from server.tools.analyzers import ReportGenerator
from server.base.logger import setup_logger

logger = setup_logger(__name__)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Analyze Milvus collection for RAG quality",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python analyze_milvus.py
  python analyze_milvus.py --no-embeddings
  python analyze_milvus.py --query "calculus" --query "derivatives"
  python analyze_milvus.py --output report.json
        """,
    )

    parser.add_argument(
        "--no-embeddings",
        action="store_true",
        help="Skip embedding analysis (faster)",
    )

    parser.add_argument(
        "--query",
        action="append",
        default=[],
        help="Test query for retrieval analysis (can be repeated)",
    )

    parser.add_argument(
        "--output",
        type=str,
        help="Save report to JSON file",
    )

    args = parser.parse_args()

    print("\n" + "=" * 70)
    print("MILVUS COLLECTION ANALYZER")
    print("=" * 70)

    # Initialize RAG
    print("\n[1] Connecting to Milvus...")
    try:
        rag = MilvusRAG()
        if rag.mock_mode:
            print("  [WARN] Milvus in mock mode - using test data")
        else:
            print("  [OK] Connected to Milvus")
    except Exception as e:
        print(f"  [ERROR] Connection failed: {e}")
        return 1

    # Generate report
    print("\n[2] Analyzing collection...")
    generator = ReportGenerator(rag)

    try:
        report = generator.generate_full_report(
            include_embeddings=not args.no_embeddings,
            test_queries=args.query if args.query else None,
        )

        if "error" in report:
            print(f"  [ERROR] {report['error']}")
            return 1

        print("  [OK] Analysis complete")
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        print(f"  [ERROR] {e}")
        return 1

    # Print report
    print("\n[3] Generating report...")
    generator.print_report(report)

    # Save to file if requested
    if args.output:
        try:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w") as f:
                json.dump(report, f, indent=2, default=str)
            print(f"\n[OK] Report saved to: {output_path}")
        except Exception as e:
            logger.error(f"Failed to save report: {e}")
            print(f"  [ERROR] Could not save report: {e}")
            return 1

    print("\n" + "=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
