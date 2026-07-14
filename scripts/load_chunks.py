#!/usr/bin/env python
"""Stage 2: Load pre-chunked JSON into Milvus with real semantic embeddings.

Reads the JSON files produced by ``scripts/extract_pdf_chunks.py`` (Stage 1)
from ``server/data/chunks``, generates genuine sentence-transformers
embeddings, and loads them into Milvus.

By default this REPLACES the target collection (drops and recreates it) so the
PDF-derived chunks become the single source of truth.

Usage:
    python scripts/load_chunks.py                       # replace 'documents'
    python scripts/load_chunks.py --append              # keep existing data
    python scripts/load_chunks.py --chunks-dir path     # custom chunk dir
    python scripts/load_chunks.py --collection name     # custom collection
"""

import sys
import io
import json
import argparse
from pathlib import Path

# Fix Windows console encoding issues with UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Add parent directory to path so we can import server modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from server.tools import MilvusRAG
from server.base.logger import setup_logger

logger = setup_logger(__name__)

BATCH_SIZE = 128


def load_chunk_files(chunks_dir: Path) -> list:
    """Load and flatten all chunk JSON files in a directory.

    Args:
        chunks_dir: Directory containing chunk JSON files

    Returns:
        Flat list of chunk dictionaries
    """
    all_chunks = []
    files = sorted(chunks_dir.glob("*.json"))
    for f in files:
        with f.open(encoding="utf-8") as fp:
            chunks = json.load(fp)
        all_chunks.extend(chunks)
        print(f"  {f.name}: {len(chunks)} chunks")
    return all_chunks


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Load chunk JSON into Milvus with real embeddings",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--chunks-dir",
        type=str,
        default="server/data/chunks",
        help="Directory containing chunk JSON files (default: server/data/chunks)",
    )
    parser.add_argument(
        "--collection",
        type=str,
        default="documents",
        help="Target Milvus collection (default: documents)",
    )
    parser.add_argument(
        "--append",
        action="store_true",
        help="Append to the existing collection instead of replacing it",
    )
    args = parser.parse_args()

    chunks_dir = Path(args.chunks_dir)

    print("\n" + "=" * 70)
    print("STAGE 2: LOAD CHUNKS INTO MILVUS (real embeddings)")
    print("=" * 70)

    if not chunks_dir.exists():
        print(f"\n[ERROR] Chunks directory not found: {chunks_dir}")
        print("        Run Stage 1 first: python scripts/extract_pdf_chunks.py")
        return 1

    # Connect (this loads the sentence-transformers model on success)
    print(f"\n[1] Connecting to Milvus (collection: {args.collection})...")
    rag = MilvusRAG(collection_name=args.collection)
    if rag.mock_mode:
        print("  [ERROR] Milvus is in mock mode - cannot load real embeddings.")
        print("          Start Milvus: docker-compose up -d")
        return 1
    print("  [OK] Connected, embedding model loaded")

    # Load chunk files
    print(f"\n[2] Reading chunk files from {chunks_dir}...")
    all_chunks = load_chunk_files(chunks_dir)
    if not all_chunks:
        print("  [ERROR] No chunks found.")
        return 1
    print(f"  [OK] {len(all_chunks)} total chunks")

    # Replace or append
    if args.append:
        print(f"\n[3] Appending to existing collection '{args.collection}'")
    else:
        print(f"\n[3] Replacing collection '{args.collection}' (drop + recreate)")
        rag.recreate_collection()

    # Batch-embed and insert
    print(f"\n[4] Embedding and inserting ({len(all_chunks)} chunks, batch={BATCH_SIZE})...")
    inserted = 0
    for start in range(0, len(all_chunks), BATCH_SIZE):
        batch = all_chunks[start : start + BATCH_SIZE]
        contents = [c["content"] for c in batch]

        # Real semantic embeddings (batch encode for speed)
        vectors = rag.embedding_model.encode(contents, convert_to_numpy=True)

        batch_data = []
        for chunk, vector in zip(batch, vectors):
            meta = dict(chunk.get("metadata", {}))
            meta["doc_id"] = chunk["id"]
            batch_data.append(
                {
                    "vector": vector.tolist(),
                    "content": chunk["content"],
                    "document_type": chunk.get("document_type", "syllabus"),
                    "metadata": json.dumps(meta),
                }
            )

        result = rag.client.insert(args.collection, batch_data)
        inserted += result.get("insert_count", len(batch_data))
        print(f"  {inserted}/{len(all_chunks)} inserted...")

    # Persist
    rag.client.flush(args.collection)
    print("  [OK] Flushed to disk")

    # Stats
    stats = rag.get_stats()
    print("\n[5] Storage statistics")
    print("-" * 70)
    print(f"  Mode          : {stats.get('mode', 'unknown').upper()}")
    print(f"  Collection    : {stats.get('collection_name', args.collection)}")
    print(f"  Total chunks  : {stats.get('total_documents', 0)}")
    print(f"  Embedding     : {stats.get('embedding_model', 'N/A')} ({stats.get('embedding_dimension', 0)}-dim)")

    rag.close()
    print("\n[DONE] Chunks loaded with real semantic embeddings.")
    print("       Inspect: python scripts/analyze_milvus.py --query \"electrostatics\"")
    return 0


if __name__ == "__main__":
    sys.exit(main())
