#!/usr/bin/env python
"""CLI tool to view chunks stored in Milvus RAG system.

Usage:
    python view_chunks.py                 # List all chunks
    python view_chunks.py --type jee_math # List chunks by type
    python view_chunks.py --id chunk_001  # Get specific chunk
    python view_chunks.py --stats         # Show statistics
    python view_chunks.py --search "limits" # Search chunks
"""

import argparse
import json
import sys
import io
from pathlib import Path
from tabulate import tabulate

# Fix Windows console encoding issues with UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add parent directory to path so we can import server modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from server.tools import MilvusRAG


def print_chunk(chunk: dict, verbose: bool = False):
    """Pretty print a single chunk."""
    print(f"\n[CHUNK] ID: {chunk.get('doc_id')}")
    print(f"   Type: {chunk.get('document_type')}")
    print(f"   Metadata: {json.dumps(chunk.get('metadata', {}), indent=8)}")
    print(f"   Content Preview:")
    content = chunk.get("content", "")
    if verbose:
        print(f"   {content}")
    else:
        preview = content[:300] + ("..." if len(content) > 300 else "")
        print(f"   {preview}")


def print_chunks_table(chunks: list):
    """Print chunks in table format."""
    if not chunks:
        print("❌ No chunks found")
        return

    table_data = []
    for chunk in chunks:
        content_preview = chunk.get("content", "")[:60].replace("\n", " ")
        table_data.append([
            chunk.get("doc_id"),
            chunk.get("document_type"),
            content_preview + ("..." if len(content_preview) >= 60 else ""),
            chunk.get("metadata", {}).get("topic", "N/A"),
        ])

    headers = ["Chunk ID", "Type", "Content Preview", "Topic"]
    print("\n" + tabulate(table_data, headers=headers, tablefmt="simple"))


def view_all(rag: MilvusRAG, verbose: bool = False):
    """View all stored chunks."""
    print("\n" + "=" * 80)
    print("[ALL STORED CHUNKS]")
    print("=" * 80)

    chunks = rag.list_all_documents()

    if not chunks:
        print("[ERROR] No chunks stored")
        return

    print(f"\n[OK] Found {len(chunks)} chunks\n")

    if verbose:
        for chunk in chunks:
            print_chunk(chunk, verbose=True)
    else:
        print_chunks_table(chunks)


def view_by_type(rag: MilvusRAG, doc_type: str, verbose: bool = False):
    """View chunks by document type."""
    print("\n" + "=" * 80)
    print(f"[CHUNKS BY TYPE: {doc_type}]")
    print("=" * 80)

    chunks = rag.list_by_type(doc_type)

    if not chunks:
        print(f"[ERROR] No chunks found for type: {doc_type}")
        return

    print(f"\n[OK] Found {len(chunks)} chunks\n")

    if verbose:
        for chunk in chunks:
            print_chunk(chunk, verbose=True)
    else:
        print_chunks_table(chunks)


def view_chunk(rag: MilvusRAG, chunk_id: str):
    """View a specific chunk."""
    print("\n" + "=" * 80)
    print(f"[CHUNK DETAILS: {chunk_id}]")
    print("=" * 80)

    chunk = rag.get_document(chunk_id)

    if not chunk:
        print(f"[ERROR] Chunk not found: {chunk_id}")
        return

    print_chunk(chunk, verbose=True)


def view_stats(rag: MilvusRAG):
    """View storage statistics."""
    print("\n" + "=" * 80)
    print("[STORAGE STATISTICS]")
    print("=" * 80)

    stats = rag.get_stats()

    print(f"\nMode: {stats.get('mode', 'unknown').upper()}")
    print(f"Total Chunks: {stats.get('total_documents', 0)}")
    print(f"Indexed: {'[OK]' if stats.get('indexed') else '[NO]'}")

    if "collection_name" in stats:
        print(f"Collection: {stats['collection_name']}")


def search_chunks(rag: MilvusRAG, query: str, top_k: int = 5):
    """Search chunks by query."""
    print("\n" + "=" * 80)
    print(f"[SEARCH RESULTS: '{query}']")
    print("=" * 80)

    results = rag.search(query, top_k=top_k)

    if not results:
        print(f"[ERROR] No chunks match query: {query}")
        return

    print(f"\n[OK] Found {len(results)} matching chunks\n")
    print_chunks_table(results)

    print("\nDetailed Results:")
    for i, result in enumerate(results, 1):
        print(f"\n{i}. {result.get('doc_id')} (Score: {result.get('relevance_score', 0):.2f})")
        print(f"   {result.get('content', '')[:200]}...")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="View and manage chunks in Milvus RAG storage",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python view_chunks.py                    # List all chunks
  python view_chunks.py --type jee_math    # Filter by type
  python view_chunks.py --id jee_001       # Get specific chunk
  python view_chunks.py --search "matrices" # Search chunks
  python view_chunks.py --stats             # Show statistics
  python view_chunks.py --all -v           # List all with full content
        """,
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help="List all stored chunks",
    )
    parser.add_argument(
        "--type",
        type=str,
        help="Filter chunks by document type",
    )
    parser.add_argument(
        "--id",
        type=str,
        help="Get specific chunk by ID",
    )
    parser.add_argument(
        "--search",
        type=str,
        help="Search chunks by query",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show storage statistics",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show full content (not just previews)",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Number of results for search (default: 5)",
    )

    args = parser.parse_args()

    # Initialize RAG
    rag = MilvusRAG()

    try:
        if args.id:
            view_chunk(rag, args.id)

        elif args.type:
            view_by_type(rag, args.type, verbose=args.verbose)

        elif args.search:
            search_chunks(rag, args.search, top_k=args.top_k)

        elif args.stats:
            view_stats(rag)

        else:
            # Default: list all
            view_all(rag, verbose=args.verbose)

    finally:
        rag.close()


if __name__ == "__main__":
    main()
