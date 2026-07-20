#!/usr/bin/env python
"""Stage 2: Load pre-chunked JSON into Milvus with real semantic embeddings.

Reads the JSON files produced by ``scripts/extract_pdf_chunks.py`` (Stage 1)
from ``server/data/chunks``, generates genuine sentence-transformers
embeddings, and loads them into separate Milvus collections for Class 10 and 12.

By default this REPLACES the target collections (drops and recreates them) so
the PDF-derived chunks become the single source of truth.

Usage:
    python scripts/load_chunks.py                  # replace all collections
    python scripts/load_chunks.py --append         # keep existing data
    python scripts/load_chunks.py --chunks-dir path  # custom chunk dir
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
        description="Load chunk JSON into Milvus with real embeddings (Class 10 & 12)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--chunks-dir",
        type=str,
        default="server/data/chunks",
        help="Directory containing chunk JSON files (default: server/data/chunks)",
    )
    parser.add_argument(
        "--append",
        action="store_true",
        help="Append to the existing collections instead of replacing them",
    )
    args = parser.parse_args()

    chunks_dir = Path(args.chunks_dir)

    print("\n" + "=" * 70)
    print("STAGE 2: LOAD CHUNKS INTO MILVUS (separate collections per class)")
    print("=" * 70)

    if not chunks_dir.exists():
        print(f"\n[ERROR] Chunks directory not found: {chunks_dir}")
        print("        Run Stage 1 first: python scripts/extract_pdf_chunks.py")
        return 1

    # Connect (this loads the sentence-transformers model on success)
    print(f"\n[1] Connecting to Milvus...")
    rag = MilvusRAG()
    if rag.mock_mode:
        print("  [ERROR] Milvus is in mock mode - cannot load real embeddings.")
        print("          Start Milvus: docker-compose up -d")
        return 1
    print("  [OK] Connected to Milvus")
    print(f"      Collections: {list(rag.collection_names.values())}")

    # Load chunk files
    print(f"\n[2] Reading chunk files from {chunks_dir}...")
    all_chunks = load_chunk_files(chunks_dir)
    if not all_chunks:
        print("  [ERROR] No chunks found.")
        return 1
    print(f"  [OK] {len(all_chunks)} total chunks")

    # Separate chunks by class level
    class_10_chunks = [c for c in all_chunks if c.get("metadata", {}).get("class") == "10"]
    class_12_chunks = [c for c in all_chunks if c.get("metadata", {}).get("class") == "12"]
    print(f"      Class 10: {len(class_10_chunks)} chunks")
    print(f"      Class 12: {len(class_12_chunks)} chunks")

    # Replace or append
    if args.append:
        print(f"\n[3] Appending to existing collections")
    else:
        print(f"\n[3] Replacing collections (drop + recreate)")
        rag.recreate_collections()

    # Batch-embed and insert by class
    total_inserted = 0
    for class_level, chunks in [("10", class_10_chunks), ("12", class_12_chunks)]:
        if not chunks:
            print(f"\n[4.{class_level}] No chunks for Class {class_level}, skipping...")
            continue

        print(f"\n[4.{class_level}] Embedding and inserting Class {class_level} ({len(chunks)} chunks, batch={BATCH_SIZE})...")
        inserted = 0

        for start in range(0, len(chunks), BATCH_SIZE):
            batch = chunks[start : start + BATCH_SIZE]
            contents = [c["content"] for c in batch]

            # Real semantic embeddings (batch encode for speed)
            vectors = rag.embedding_model.encode(contents, convert_to_numpy=True)

            for chunk, vector in zip(batch, vectors):
                meta = dict(chunk.get("metadata", {}))
                doc_id = chunk["id"]

                rag.add_document(
                    doc_id=doc_id,
                    content=chunk["content"],
                    doc_type=chunk.get("document_type", "syllabus"),
                    class_level=class_level,
                    metadata=meta,
                )
                inserted += 1
                total_inserted += 1

            print(f"      {inserted}/{len(chunks)} inserted...")

        # Flush this collection
        collection_name = rag.collection_names[class_level]
        rag.client.flush(collection_name)
        print(f"      [OK] Flushed to disk")

    # Stats
    stats = rag.get_stats()
    print("\n[5] Storage statistics")
    print("-" * 70)
    print(f"  Mode          : {stats.get('mode', 'unknown').upper()}")
    print(f"  Total chunks  : {stats.get('total_documents', 0)}")
    print(f"  Class 10      : {stats.get('class_10_documents', 0)} chunks")
    print(f"  Class 12      : {stats.get('class_12_documents', 0)} chunks")
    print(f"  Embedding     : {stats.get('embedding_model', 'N/A')} ({stats.get('embedding_dimension', 0)}-dim)")

    rag.close()
    print("\n[DONE] Chunks loaded with real semantic embeddings into separate collections.")
    print("       Inspect: python scripts/analyze_milvus.py --query \"electrostatics\"")
    return 0


if __name__ == "__main__":
    sys.exit(main())
