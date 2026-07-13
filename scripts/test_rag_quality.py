#!/usr/bin/env python
"""Comprehensive RAG quality testing with difficult prompts and metric collection.

Runs multiple complex prompts, collects evaluation metrics, and provides
statistical analysis for production validation.
"""

import asyncio
import sys
import io
import json
from pathlib import Path
from datetime import datetime
from docx import Document
from collections import defaultdict

# Fix Windows console encoding issues with UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from server.core import LangGraphOrchestrator
from server.tools import MilvusRAG
from server.tools.utils.evaluation_metrics import ContentEvaluator
from server.base.logger import setup_logger

logger = setup_logger(__name__)


# Difficult prompts that test RAG quality
DIFFICULT_PROMPTS = [
    {
        "request": "Create an advanced study guide comparing electric field strength calculations using Coulomb's law and Gauss's law, including practical examples with different charge configurations.",
        "context_keywords": ["electric field", "Coulomb's law", "Gauss's law", "charge"],
        "difficulty": "HARD",
    },
    {
        "request": "Develop a comprehensive physics problem set covering electrostatics fundamentals: point charges, field superposition, potential energy, and capacitance with detailed solutions.",
        "context_keywords": ["electrostatics", "point charges", "field", "potential", "capacitance"],
        "difficulty": "HARD",
    },
    {
        "request": "Generate a thesis outline explaining the relationship between electric field lines, equipotential surfaces, and conductor behavior in electrostatic equilibrium.",
        "context_keywords": ["electric field", "equipotential", "conductor", "equilibrium"],
        "difficulty": "HARD",
    },
]


def extract_docx_content(filepath: str) -> str:
    """Extract text content from DOCX file."""
    try:
        doc = Document(filepath)
        return "\n".join(paragraph.text for paragraph in doc.paragraphs)
    except Exception as e:
        logger.warning(f"Could not extract DOCX: {e}")
        return ""


async def test_single_prompt(orchestrator, rag, prompt_info, run_num):
    """Test a single prompt and collect metrics."""
    print(f"\n    Run {run_num}: {prompt_info['request'][:60]}...")

    result = {
        "prompt": prompt_info["request"][:50],
        "difficulty": prompt_info["difficulty"],
        "run": run_num,
        "success": False,
        "metrics": None,
        "error": None,
    }

    try:
        # Fetch RAG context
        search_query = " ".join(prompt_info["context_keywords"][:2])
        context_chunks = rag.search(search_query, top_k=3)
        combined_context = "\n\n".join(
            chunk.get("content", "") for chunk in (context_chunks or [])
        )

        # Generate document
        doc_result = await orchestrator.generate_document(
            request=prompt_info["request"],
            metadata={
                "subject": "Physics",
                "level": "Advanced",
                "scope": "Electrostatics"
            }
        )

        if not doc_result.get("success"):
            result["error"] = doc_result.get("error", "Generation failed")
            return result

        # Extract generated content
        generated_content = ""
        if doc_result.get("document_filename"):
            generated_content = extract_docx_content(doc_result["document_filename"])

        if not generated_content:
            result["error"] = "No content generated"
            return result

        # Calculate metrics
        if combined_context:
            metrics = ContentEvaluator.comprehensive_evaluation(
                generated=generated_content,
                reference=combined_context,
                context=combined_context
            )
        else:
            # Fallback: use first part of generated as reference
            metrics = ContentEvaluator.comprehensive_evaluation(
                generated=generated_content,
                reference=generated_content[:1000],
                context=generated_content
            )

        result["success"] = True
        result["metrics"] = metrics
        result["iterations"] = doc_result.get("iterations", 0)
        result["sections"] = doc_result.get("sections_count", 0)

    except Exception as e:
        result["error"] = str(e)
        logger.error(f"Test failed: {e}")

    return result


async def run_quality_tests():
    """Run comprehensive RAG quality tests."""
    print("\n" + "=" * 80)
    print("COMPREHENSIVE RAG QUALITY TESTING")
    print("=" * 80)

    # Initialize
    rag = MilvusRAG()
    orchestrator = LangGraphOrchestrator()

    stats = rag.get_stats()
    print(f"\n[SETUP]")
    print(f"  Milvus Mode: {stats.get('mode', 'unknown').upper()}")
    print(f"  Chunks Stored: {stats.get('total_documents', 0)}")

    if rag.mock_mode:
        print("\n  WARNING: Using mock Milvus (no persistent storage)")
        print("  Run: python load_curriculum.py")

    # Run tests
    print(f"\n[TESTING] Running {len(DIFFICULT_PROMPTS)} difficult prompts")
    print("  " + "-" * 76)

    all_results = []

    for prompt_info in DIFFICULT_PROMPTS:
        print(f"\n  Prompt: {prompt_info['request'][:70]}...")
        print(f"  Difficulty: {prompt_info['difficulty']}")

        # Run once per prompt
        for run in range(1, 2):
            result = await test_single_prompt(orchestrator, rag, prompt_info, run)
            all_results.append(result)

            if result["success"]:
                metrics = result["metrics"]
                print(f"    Run {run}: BLEU={metrics['bleu']['bleu']:.4f}, "
                      f"ROUGE-1={metrics['rouge']['rouge1']:.4f}, "
                      f"Overall={metrics['overall_evaluation_score']:.4f}")
            else:
                print(f"    Run {run}: FAILED - {result['error']}")

    # Analyze results
    print("\n" + "=" * 80)
    print("QUALITY ANALYSIS")
    print("=" * 80)

    successful = [r for r in all_results if r["success"]]
    failed = [r for r in all_results if not r["success"]]

    print(f"\n[RESULTS]")
    print(f"  Total Tests: {len(all_results)}")
    print(f"  Successful: {len(successful)} ({len(successful)/len(all_results)*100:.1f}%)")
    print(f"  Failed: {len(failed)} ({len(failed)/len(all_results)*100:.1f}%)")

    if failed:
        print(f"\n[FAILURES]")
        for result in failed:
            print(f"  - {result['prompt']}: {result['error']}")

    if successful:
        # Aggregate metrics
        print(f"\n[METRICS SUMMARY]")
        print("  " + "-" * 76)

        metrics_keys = {
            "bleu": ["bleu_1", "bleu_2", "bleu_3", "bleu_4", "bleu"],
            "rouge": ["rouge1", "rouge2", "rougeL"],
            "groundedness": ["groundedness", "grounded_ratio"],
            "context_utilization": ["context_utilization"],
            "semantic_similarity": ["semantic_similarity"],
            "overall": ["overall_evaluation_score"],
        }

        # Calculate aggregates
        aggregates = defaultdict(lambda: {"values": [], "min": 1.0, "max": 0.0, "avg": 0.0})

        for result in successful:
            metrics = result["metrics"]
            for category, keys in metrics_keys.items():
                for key in keys:
                    if category == "bleu" and key in metrics["bleu"]:
                        val = metrics["bleu"][key]
                    elif category == "rouge" and key in metrics["rouge"]:
                        val = metrics["rouge"][key]
                    elif category == "groundedness" and key in metrics.get("groundedness", {}):
                        val = metrics["groundedness"][key]
                    elif category == "context_utilization" and key in metrics.get("context_utilization", {}):
                        val = metrics["context_utilization"][key]
                    elif category == "semantic_similarity" and key in metrics.get("semantic_similarity", {}):
                        val = metrics["semantic_similarity"][key]
                    elif category == "overall" and key in metrics:
                        val = metrics[key]
                    else:
                        continue

                    aggregates[f"{category}:{key}"]["values"].append(val)

        # Calculate stats
        for metric_name, data in aggregates.items():
            if data["values"]:
                data["min"] = min(data["values"])
                data["max"] = max(data["values"])
                data["avg"] = sum(data["values"]) / len(data["values"])

        # Print by category
        for category in ["bleu", "rouge", "groundedness", "context_utilization", "semantic_similarity", "overall"]:
            category_metrics = {k: v for k, v in aggregates.items() if k.startswith(category)}
            if category_metrics:
                print(f"\n  [{category.upper()}]")
                for metric_name in sorted(category_metrics.keys()):
                    stats = category_metrics[metric_name]
                    key = metric_name.split(":")[-1]
                    print(f"    {key:20} | Min: {stats['min']:.4f} | Avg: {stats['avg']:.4f} | Max: {stats['max']:.4f}")

        # Quality assessment
        print(f"\n[QUALITY ASSESSMENT]")
        overall_avg = aggregates.get("overall:overall_evaluation_score", {}).get("avg", 0)
        bleu_avg = aggregates.get("bleu:bleu", {}).get("avg", 0)
        rouge1_avg = aggregates.get("rouge:rouge1", {}).get("avg", 0)
        groundedness_avg = aggregates.get("groundedness:groundedness", {}).get("avg", 0)
        context_util_avg = aggregates.get("context_utilization:context_utilization", {}).get("avg", 0)

        print(f"  Overall Score: {overall_avg:.4f}", end="")
        if overall_avg >= 0.7:
            print(" ✓ GOOD")
        elif overall_avg >= 0.5:
            print(" ~ ACCEPTABLE")
        else:
            print(" ✗ NEEDS IMPROVEMENT")

        print(f"  BLEU Score:    {bleu_avg:.4f}", end="")
        if bleu_avg >= 0.5:
            print(" ✓")
        else:
            print(" ✗ (needs curriculum data)")

        print(f"  ROUGE-1 Score: {rouge1_avg:.4f}", end="")
        if rouge1_avg >= 0.5:
            print(" ✓")
        else:
            print(" ✗ (needs curriculum data)")

        if groundedness_avg > 0:
            print(f"  Groundedness:  {groundedness_avg:.4f} ({groundedness_avg*100:.1f}%)", end="")
            if groundedness_avg >= 0.6:
                print(" ✓")
            else:
                print(" ✗ (content not well grounded)")

        if context_util_avg > 0:
            print(f"  Context Util:  {context_util_avg:.4f}", end="")
            if context_util_avg >= 0.5:
                print(" ✓")
            else:
                print(" ✗ (low context usage)")

    # Save results to file
    results_dir = Path(__file__).parent.parent / "output" / "test_results"
    results_dir.mkdir(parents=True, exist_ok=True)
    results_file = results_dir / "quality_test_results.json"

    with open(results_file, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "total_tests": len(all_results),
            "successful": len(successful),
            "failed": len(failed),
            "results": all_results,
        }, f, indent=2, default=str)

    print(f"\n[RESULTS SAVED]")
    print(f"  {results_file}")

    rag.close()

    print("\n" + "=" * 80)
    print("Testing complete")
    print("=" * 80)

    # Recommendations
    print("\n[PRODUCTION READINESS CHECKLIST]")
    print("  - Load curriculum data: python load_curriculum.py")
    print("  - Rerun this test to see realistic metrics")
    print("  - Aim for Overall Score > 0.7 for production")
    print("  - Check BLEU > 0.5, ROUGE-1 > 0.5")
    print("  - Ensure Groundedness > 0.6 (content grounded in context)")
    print("  - Monitor Context Utilization for RAG efficiency")


def main():
    """Main entry point."""
    print("Starting Comprehensive RAG Quality Tests...\n")

    try:
        asyncio.run(run_quality_tests())
    except KeyboardInterrupt:
        print("\n\nCancelled by user")
    except Exception as e:
        logger.error(f"Failed: {e}")
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
