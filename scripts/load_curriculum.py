#!/usr/bin/env python
"""Load curriculum data from JSON into Milvus RAG system.

Works with existing curriculum_data.json format.
"""

import json
import sys
import io
import hashlib
from pathlib import Path
from typing import List, Dict, Any

# Fix Windows console encoding issues with UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add parent directory to path so we can import server modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from server.tools import DocumentChunker, MilvusRAG
from server.base.logger import setup_logger

logger = setup_logger(__name__)


def generate_embedding(text: str) -> List[float]:
    """Generate embedding from text using hash."""
    hash_val = int(hashlib.md5(text.encode()).hexdigest(), 16)
    embedding = []
    for i in range(384):
        embedding.append(float((hash_val + i) % 1000) / 1000.0)
    return embedding


def load_curriculum_data(json_file: str = "server/data/curriculum_data.json"):
    """Load curriculum data from JSON file into Milvus.

    Args:
        json_file: Path to curriculum JSON file
    """
    print("\n" + "=" * 80)
    print("[LOAD] LOADING CURRICULUM DATA INTO MILVUS")
    print("=" * 80)

    # Check file exists
    json_path = Path(json_file)
    if not json_path.exists():
        print(f"[ERROR] File not found: {json_file}")
        return False

    # Load JSON data
    print(f"\n[LOAD] Loading: {json_file}")
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            documents = json.load(f)
    except json.JSONDecodeError as e:
        print(f"[ERROR] Invalid JSON: {e}")
        return False

    if not documents:
        print("[ERROR] No documents in file")
        return False

    print(f"[OK] Found {len(documents)} documents")

    # Initialize chunker and RAG
    chunker = DocumentChunker(chunk_size=500, overlap=100)
    rag = MilvusRAG()

    if rag.mock_mode:
        print("[WARN] WARNING: Still in MOCK mode")
        print("   Make sure Milvus is running:")
        print("   docker-compose ps")
        print("\n   Or check logs:")
        print("   docker-compose logs milvus")
        return False

    print("\n[PROCESS] Chunking documents...")

    all_chunks = []
    total_chars = 0

    for i, doc in enumerate(documents, 1):
        doc_id = doc.get("id", f"doc_{i}")
        content = doc.get("content", "")
        metadata = doc.get("metadata", {})
        doc_type = doc.get("document_type", "curriculum")

        if not content:
            continue

        total_chars += len(content)

        # Split into chunks by sentences
        chunker_obj = DocumentChunker(chunk_size=500, overlap=100)
        chunks = chunker_obj.chunk_by_sentences(content)

        # Create chunk objects
        for j, chunk_text in enumerate(chunks, 1):
            chunk = {
                "chunk_id": f"{doc_id}_c{j}",
                "document_id": doc_id,
                "chunk_text": chunk_text,
                "embedding": None,
                "metadata": {
                    **metadata,
                    "chunk_index": j,
                    "total_chunks": len(chunks),
                    "content_length": len(content),
                }
            }
            all_chunks.append(chunk)

        print(f"  {i}. {doc_id}: {len(chunks)} chunks ({len(content)} chars)")

    print(f"\n[OK] Created {len(all_chunks)} total chunks")
    print(f"  Total content: {total_chars:,} characters")
    print(f"  Average chunk size: {int(total_chars/len(all_chunks)):,} chars")

    # Load into Milvus
    print("\n[LOAD] Loading chunks into Milvus...")

    try:
        # Batch insert all chunks
        if not rag.mock_mode:
            # Build batch insert data
            batch_data = []
            for chunk in all_chunks:
                meta = chunk["metadata"].copy()
                meta["doc_id"] = chunk["chunk_id"]

                batch_data.append({
                    "vector": generate_embedding(chunk["chunk_text"]),
                    "content": chunk["chunk_text"],
                    "document_type": chunk["document_id"],
                    "metadata": json.dumps(meta),
                })

            # Insert all at once
            result = rag.client.insert(rag.collection_name, batch_data)
            print(f"   Inserted {result.get('insert_count', 0)} chunks")

            # Flush to persist data
            rag.client.flush(rag.collection_name)
            print(f"   [OK] Flushed data to disk...")
        else:
            # Mock mode: use individual inserts
            for i, chunk in enumerate(all_chunks, 1):
                rag.add_document(
                    doc_id=chunk["chunk_id"],
                    content=chunk["chunk_text"],
                    doc_type=chunk["document_id"],
                    metadata=chunk["metadata"],
                )
                if i % 50 == 0:
                    print(f"   Loaded {i}/{len(all_chunks)} chunks...")

        print(f"\n[SUCCESS] Successfully loaded all {len(all_chunks)} chunks!")

        # Show stats
        stats = rag.get_stats()
        print(f"\n[STATS] Storage Statistics:")
        print(f"   Mode: {stats.get('mode', 'unknown').upper()}")
        print(f"   Total chunks: {stats.get('total_documents', 0)}")
        print(f"   Indexed: {'[OK]' if stats.get('indexed') else '[FAIL]'}")

        if "collection_name" in stats:
            print(f"   Collection: {stats['collection_name']}")

        rag.close()

        print("\n[READY] Ready to use RAG with curriculum data!")
        print("   Test with: python view_chunks.py --search 'physics'")
        return True

    except Exception as e:
        logger.error(f"Failed to load chunks: {e}")
        print(f"[ERROR] Error loading chunks: {e}")
        return False


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Load curriculum data into Milvus",
        epilog="""
Examples:
  python load_curriculum.py                           # Load default curriculum_data.json
  python load_curriculum.py --file path/to/file.json  # Load custom file
        """,
    )

    parser.add_argument(
        "--file",
        type=str,
        default="server/data/curriculum_data.json",
        help="Path to curriculum JSON file",
    )

    args = parser.parse_args()

    success = load_curriculum_data(json_file=args.file)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
