#!/usr/bin/env python
"""Display RAG evaluation metrics from LangGraph orchestrator with Milvus context.

Shows BLEU, ROUGE, groundedness, context utilization, and other quality metrics.
"""

import asyncio
import sys
import io
from pathlib import Path
from docx import Document

# Fix Windows console encoding issues with UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add parent directory to path so we can import server modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from server.core import LangGraphOrchestrator
from server.tools import MilvusRAG
from server.tools.utils.evaluation_metrics import ContentEvaluator
from server.base.logger import setup_logger

logger = setup_logger(__name__)


def extract_docx_content(filepath: str) -> str:
    """Extract text content from a DOCX file.

    Args:
        filepath: Path to DOCX file

    Returns:
        Extracted text content
    """
    try:
        doc = Document(filepath)
        return "\n".join(paragraph.text for paragraph in doc.paragraphs)
    except Exception as e:
        logger.warning(f"Could not extract DOCX content: {e}")
        return ""


async def show_metrics():
    """Display metrics from document generation."""
    print("\n" + "=" * 80)
    print("RAG EVALUATION METRICS - LANGGRAPH ORCHESTRATOR WITH MILVUS")
    print("=" * 80)

    # Initialize RAG
    print("\n[1] Checking Milvus RAG System...")
    rag = MilvusRAG()
    stats = rag.get_stats()

    print(f"    Mode: {stats.get('mode', 'unknown').upper()}")
    print(f"    Total chunks stored: {stats.get('total_documents', 0)}")
    print(f"    Indexed: {'Yes' if stats.get('indexed') else 'No'}")

    if rag.mock_mode:
        print("\n    WARNING: Milvus in mock mode (no persistent storage)")
        print("    Run: python setup_milvus.py --start")
        print("    Then: python load_curriculum.py")
        return

    # Search for sample curriculum content
    print("\n[2] Fetching RAG Context...")
    search_query = "electrostatics electric field"
    context_chunks = rag.search(search_query, top_k=3)

    # Combine all context chunks into one document
    combined_context = "\n\n".join(
        chunk.get("content", "") for chunk in (context_chunks or [])
    )

    if context_chunks:
        print(f"    Found {len(context_chunks)} matching curriculum chunks for: '{search_query}'")
        for i, chunk in enumerate(context_chunks, 1):
            doc_id = chunk.get("doc_id", "unknown")
            content_preview = chunk.get("content", "")[:80]
            relevance = chunk.get("relevance_score", 0)
            print(f"    {i}. {doc_id} (relevance: {relevance:.2f})")
            print(f"       {content_preview}...")
    else:
        print(f"    No chunks found for: '{search_query}'")
        combined_context = ""

    # Generate document using LangGraph orchestrator
    print("\n[3] Generating Document with LangGraph...")
    orchestrator = LangGraphOrchestrator()

    result = None
    try:
        result = await orchestrator.generate_document(
            request="Create a 2-day study plan for Electrostatics covering electric field and Coulomb's law",
            metadata={
                "subject": "Physics",
                "level": "JEE",
                "scope": "Electrostatics"
            }
        )

        print(f"    ✓ Success: {result.get('success', False)}")
        print(f"    ✓ Sections generated: {result.get('sections_count', 0)}")
        print(f"    ✓ Review iterations: {result.get('iterations', 0)}")
        print(f"    ✓ Message history: {result.get('messages', 0)} messages")

        if result.get("error"):
            print(f"    ✗ Error: {result['error']}")

        if result.get("document_filename"):
            print(f"    ✓ Output: {result['document_filename']}")

    except Exception as e:
        logger.error(f"Generation failed: {e}")
        print(f"    ✗ Error: {e}")
        rag.close()
        return

    # Calculate RAG evaluation metrics
    print("\n[4] RAG Evaluation Metrics (BLEU, ROUGE, Groundedness, Context Utilization)...")
    print("    " + "-" * 76)

    generated_content = ""
    if result and result.get("document_filename"):
        try:
            generated_content = extract_docx_content(result["document_filename"])
        except Exception as e:
            logger.error(f"Failed to extract document content: {e}")
            print(f"    Could not read generated document: {e}")

    if not generated_content:
        print("    No generated content to evaluate")
    else:
        metrics = None
        if combined_context:
            # Calculate metrics with actual RAG context
            metrics = ContentEvaluator.comprehensive_evaluation(
                generated=generated_content,
                reference=combined_context,
                context=combined_context
            )
        else:
            # Demo mode: use generated content itself as reference
            print("    [DEMO MODE] No RAG context available - showing metrics with generated content as reference")
            print()
            metrics = ContentEvaluator.comprehensive_evaluation(
                generated=generated_content,
                reference=generated_content[:1000],  # Use first part as reference
                context=generated_content
            )

        if metrics:
            # Display BLEU metrics
            print("\n    [BLEU] Bilingual Evaluation Understudy Score")
            print(f"       BLEU-1 (unigram):  {metrics['bleu'].get('bleu_1', 0):.4f}")
            print(f"       BLEU-2 (bigram):   {metrics['bleu'].get('bleu_2', 0):.4f}")
            print(f"       BLEU-3 (trigram):  {metrics['bleu'].get('bleu_3', 0):.4f}")
            print(f"       BLEU-4 (4-gram):   {metrics['bleu'].get('bleu_4', 0):.4f}")
            print(f"       Overall BLEU:      {metrics['bleu'].get('bleu', 0):.4f}")

            # Display ROUGE metrics
            print("\n    [ROUGE] Recall-Oriented Understudy for Gisting Evaluation")
            print(f"       ROUGE-1 (unigram): {metrics['rouge'].get('rouge1', 0):.4f}")
            print(f"       ROUGE-2 (bigram):  {metrics['rouge'].get('rouge2', 0):.4f}")
            print(f"       ROUGE-L (longest): {metrics['rouge'].get('rougeL', 0):.4f}")

            # Display groundedness metrics
            if 'groundedness' in metrics:
                groundedness = metrics['groundedness']
                print("\n    [GROUNDEDNESS] How well content is grounded in context")
                print(f"       Groundedness Score: {groundedness.get('groundedness', 0):.4f}")
                print(f"       Grounded Tokens:    {groundedness.get('grounded_tokens', 0)}/{groundedness.get('total_tokens', 0)}")
                print(f"       Grounded Ratio:     {groundedness.get('grounded_ratio', 0):.1%}")

            # Display context utilization metrics
            if 'context_utilization' in metrics:
                utilization = metrics['context_utilization']
                print("\n    [CONTEXT UTIL] How much context was actually used")
                print(f"       Utilization Score:  {utilization.get('context_utilization', 0):.4f}")
                print(f"       Context Tokens:     {utilization.get('unique_context_tokens_used', 0)}/{utilization.get('total_context_tokens', 0)} unique tokens")

            # Display semantic similarity
            if 'semantic_similarity' in metrics:
                print(f"\n    [SEMANTIC SIM] Jaccard Similarity: {metrics['semantic_similarity'].get('semantic_similarity', 0):.4f}")

            # Display overall evaluation score
            print(f"\n    [OVERALL] Combined Evaluation Score: {metrics.get('overall_evaluation_score', 0):.4f}")
            print("       (Weighted combination of all metrics)")

    # Display execution summary
    print("\n[5] Execution Summary")
    print("    " + "-" * 76)
    print("    LangGraph workflow pipeline:")
    print("      ① Plan Node:     Creates document outline and structure")
    print("      ② Write Node:    Generates content sections")
    print("      ③ Review Node:   Evaluates quality and identifies issues")
    print("      ④ Refine Node:   Iteratively improves based on feedback (if needed)")
    print("      ⑤ Generate Node: Creates final DOCX output")
    print("\n    RAG Integration:")
    print(f"      • Retrieves curriculum context from Milvus")
    print(f"      • Enhances writer with domain-specific knowledge")
    print(f"      • Measures groundedness in retrieved context")
    print(f"      • Tracks context utilization for RAG efficiency")

    rag.close()

    print("\n" + "=" * 80)
    print("Metrics evaluation complete")
    print("=" * 80)
    print("\nNext steps:")
    print("   - Run: python run_server.py")
    print("   - Load curriculum: python load_curriculum.py")
    print("   - Test API: curl http://localhost:8000/api/generate")


def main():
    """Main entry point."""
    print("Starting LangGraph Orchestrator Metrics Demo...\n")

    try:
        asyncio.run(show_metrics())
    except KeyboardInterrupt:
        print("\n\nCancelled by user")
    except Exception as e:
        logger.error(f"Failed: {e}")
        print(f"\nError: {e}")


if __name__ == "__main__":
    main()
