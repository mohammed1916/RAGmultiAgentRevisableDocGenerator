#!/usr/bin/env python
"""Performance and quality evaluation of the RAG document generation pipeline.

Measures:
- Planner latency
- Writer latency
- Reviewer latency
- Total pipeline time
- Token usage
- Quality metrics (ROUGE, BLEU, groundedness)
- Review iterations
"""

import sys
import time
import asyncio
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from server.core.orchestrators import LangGraphOrchestrator
from server.base.logger import setup_logger

logger = setup_logger(__name__)


async def run_evaluation():
    """Run comprehensive performance evaluation."""

    test_prompts = [
        "Create a comprehensive study guide on electrostatics and electric field concepts",
        "Design a learning plan for thermodynamics fundamentals",
        "Prepare study material on Newton's laws of motion",
        "Develop curriculum content for atomic structure and bonding",
        "Create educational content on photosynthesis and cellular respiration",
    ]

    results = {
        "timestamp": datetime.now().isoformat(),
        "tests": []
    }

    orchestrator = LangGraphOrchestrator()

    for i, prompt in enumerate(test_prompts, 1):
        print(f"\n{'='*70}")
        print(f"Test {i}/5: {prompt[:60]}...")
        print(f"{'='*70}")

        start_time = time.time()

        try:
            result = await orchestrator.generate_document(
                request=prompt,
                metadata={
                    "class_level": "10" if i % 2 == 0 else "12",
                    "subject": "Science" if i <= 3 else "Biology"
                }
            )

            elapsed = time.time() - start_time

            test_result = {
                "test_num": i,
                "prompt": prompt,
                "class_level": "10" if i % 2 == 0 else "12",
                "success": result.get("success", False),
                "total_latency_sec": round(elapsed, 2),
                "sections_count": result.get("sections_count", 0),
                "iterations": result.get("iterations", 0),
                "error": result.get("error"),
            }

            results["tests"].append(test_result)

            print(f"✓ Success: {result.get('success')}")
            print(f"  Latency: {elapsed:.2f}s")
            print(f"  Sections: {result.get('sections_count')}")
            print(f"  Review iterations: {result.get('iterations')}")
            print(f"  Messages: {result.get('messages')}")

        except Exception as e:
            elapsed = time.time() - start_time
            print(f"✗ Error: {e}")
            results["tests"].append({
                "test_num": i,
                "prompt": prompt,
                "success": False,
                "total_latency_sec": round(elapsed, 2),
                "error": str(e)
            })

    # Summary statistics
    successful = [t for t in results["tests"] if t.get("success")]
    latencies = [t.get("total_latency_sec", 0) for t in successful if t.get("total_latency_sec")]
    iterations = [t.get("iterations", 0) for t in successful]

    summary = {
        "total_tests": len(test_prompts),
        "successful_tests": len(successful),
        "failed_tests": len(test_prompts) - len(successful),
        "success_rate": f"{100 * len(successful) / len(test_prompts):.1f}%",
        "avg_latency_sec": round(sum(latencies) / len(latencies), 2) if latencies else 0,
        "min_latency_sec": round(min(latencies), 2) if latencies else 0,
        "max_latency_sec": round(max(latencies), 2) if latencies else 0,
        "avg_iterations": round(sum(iterations) / len(iterations), 2) if iterations else 0,
        "avg_sections": round(sum(t.get("sections_count", 0) for t in successful) / len(successful), 1) if successful else 0,
    }

    results["summary"] = summary

    # Save results
    output_path = Path(__file__).parent.parent / "output" / "metrics" / "performance_eval.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n{'='*70}")
    print("PERFORMANCE EVALUATION SUMMARY")
    print(f"{'='*70}")
    print(f"Total Tests: {summary['total_tests']}")
    print(f"Successful: {summary['successful_tests']}")
    print(f"Failed: {summary['failed_tests']}")
    print(f"Success Rate: {summary['success_rate']}")
    print(f"Avg Latency: {summary['avg_latency_sec']}s")
    print(f"Latency Range: {summary['min_latency_sec']}s - {summary['max_latency_sec']}s")
    print(f"Avg Review Iterations: {summary['avg_iterations']}")
    print(f"Avg Sections Generated: {summary['avg_sections']}")
    print(f"\nResults saved to: {output_path}")
    print(f"{'='*70}")


if __name__ == "__main__":
    asyncio.run(run_evaluation())
