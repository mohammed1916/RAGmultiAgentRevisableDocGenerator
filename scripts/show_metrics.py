#!/usr/bin/env python
"""Display metrics from LangGraph orchestrator with Milvus RAG context.

Shows performance metrics, RAG context retrieval, and quality scores.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path so we can import server modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from server.langgraph_orchestrator import LangGraphOrchestrator
from server.tools import MilvusRAG
from server.logger import setup_logger

logger = setup_logger(__name__)


async def show_metrics():
    """Display metrics from document generation."""
    print("\n" + "=" * 80)
    print("📊 LANGGRAPH ORCHESTRATOR METRICS WITH MILVUS RAG")
    print("=" * 80)

    # Initialize RAG
    print("\n[1] Checking Milvus RAG System...")
    rag = MilvusRAG()
    stats = rag.get_stats()

    print(f"    Mode: {stats.get('mode', 'unknown').upper()}")
    print(f"    Total chunks stored: {stats.get('total_documents', 0)}")
    print(f"    Indexed: {'✓ Yes' if stats.get('indexed') else '✗ No'}")

    if rag.mock_mode:
        print("\n    ⚠️  WARNING: Milvus in mock mode (no persistent storage)")
        print("    Run: python setup_milvus.py --start")
        print("    Then: python load_curriculum.py")
        return

    # Search for sample curriculum content
    print("\n[2] Fetching RAG Context...")
    search_query = "electrostatics electric field"
    context = rag.search(search_query, top_k=2)

    if context:
        print(f"    Found {len(context)} matching curriculum chunks for: '{search_query}'")
        for i, chunk in enumerate(context, 1):
            doc_id = chunk.get("doc_id", "unknown")
            content_preview = chunk.get("content", "")[:100]
            relevance = chunk.get("relevance_score", 0)
            print(f"    {i}. {doc_id} (relevance: {relevance:.2f})")
            print(f"       {content_preview}...")
    else:
        print(f"    No chunks found for: '{search_query}'")

    # Generate document using LangGraph orchestrator
    print("\n[3] Generating Document with LangGraph...")
    orchestrator = LangGraphOrchestrator()

    try:
        result = await orchestrator.generate_document(
            request="Create a 2-day study plan for Electrostatics covering electric field and Coulomb's law",
            metadata={
                "subject": "Physics",
                "level": "JEE",
                "scope": "Electrostatics"
            }
        )

        print(f"    ✅ Success: {result.get('success', False)}")
        print(f"    Sections generated: {result.get('sections_count', 0)}")
        print(f"    Review iterations: {result.get('iterations', 0)}")
        print(f"    Message history: {result.get('messages', 0)} messages")

        if result.get("error"):
            print(f"    Error: {result['error']}")

        if result.get("document_filename"):
            print(f"    Output: {result['document_filename']}")

    except Exception as e:
        logger.error(f"Generation failed: {e}")
        print(f"    ❌ Error: {e}")

    # Display execution metrics
    print("\n[4] Execution Summary")
    print("    " + "-" * 76)
    print("    LangGraph workflow:")
    print("      • Plan Node: Creates document outline and structure")
    print("      • Write Node: Generates content sections")
    print("      • Review Node: Evaluates quality and identifies issues")
    print("      • Refine Node: Iteratively improves based on feedback")
    print("      • Generate Node: Creates final DOCX output")
    print("\n    RAG Integration:")
    print(f"      • Retrieves curriculum context from Milvus")
    print(f"      • Enhances writer with domain knowledge")
    print(f"      • Grounds generation in curriculum")

    rag.close()

    print("\n" + "=" * 80)
    print("✅ Metrics display complete")
    print("=" * 80)
    print("\n💡 Next steps:")
    print("   • Run: python run_server.py")
    print("   • Test API: curl http://localhost:8000/api/generate")
    print("   • View chunks: python view_chunks.py --stats")


def main():
    """Main entry point."""
    print("🚀 Starting LangGraph Orchestrator Metrics Demo...\n")

    try:
        asyncio.run(show_metrics())
    except KeyboardInterrupt:
        print("\n\n⏹️  Cancelled by user")
    except Exception as e:
        logger.error(f"Failed: {e}")
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    main()
