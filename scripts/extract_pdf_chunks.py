#!/usr/bin/env python
"""Stage 1: Extract text from curriculum PDFs and write chunked JSON files.

Reads every PDF in ``server/data`` (excluding any with "curriculum" in the
name) and writes one JSON file of chunks per PDF into ``server/data/chunks``.

The output JSON is consumed by ``scripts/load_chunks.py`` (Stage 2), which
generates real semantic embeddings and loads the chunks into Milvus.

Usage:
    python scripts/extract_pdf_chunks.py                    # all PDFs
    python scripts/extract_pdf_chunks.py --data-dir path    # custom source dir
    python scripts/extract_pdf_chunks.py --chunk-size 1000  # override chunk size
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

from server.tools import PDFChunker
from server.base.logger import setup_logger

logger = setup_logger(__name__)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract and chunk curriculum PDFs into JSON files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default="server/data",
        help="Directory containing source PDFs (default: server/data)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="server/data/chunks",
        help="Directory for chunk JSON output (default: server/data/chunks)",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=1200,
        help="Target characters per chunk (default: 1200)",
    )
    parser.add_argument(
        "--chunk-overlap",
        type=int,
        default=200,
        help="Character overlap between chunks (default: 200)",
    )
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 70)
    print("STAGE 1: EXTRACT & CHUNK PDFs")
    print("=" * 70)
    print(f"\nSource:  {data_dir}")
    print(f"Output:  {output_dir}")
    print(f"Chunk size: {args.chunk_size}, overlap: {args.chunk_overlap}")

    pdfs = sorted(data_dir.glob("*.pdf"))
    if not pdfs:
        print(f"\n[ERROR] No PDFs found in {data_dir}")
        return 1

    chunker = PDFChunker(chunk_size=args.chunk_size, chunk_overlap=args.chunk_overlap)

    total_chunks = 0
    processed = 0
    skipped = 0

    print(f"\nFound {len(pdfs)} PDF(s)\n" + "-" * 70)

    for pdf in pdfs:
        # Skip the legacy curriculum source if present as PDF
        if "curriculum" in pdf.name.lower():
            print(f"  SKIP  {pdf.name} (legacy curriculum)")
            skipped += 1
            continue

        try:
            chunks = chunker.process_pdf(pdf)
        except Exception as e:
            logger.error(f"Failed to process {pdf.name}: {e}")
            print(f"  ERROR {pdf.name}: {e}")
            skipped += 1
            continue

        if not chunks:
            print(f"  SKIP  {pdf.name} (too little text)")
            skipped += 1
            continue

        output_file = output_dir / f"{pdf.stem}.json"
        with output_file.open("w", encoding="utf-8") as fp:
            json.dump(chunks, fp, indent=2, ensure_ascii=False)

        total_chunks += len(chunks)
        processed += 1
        print(f"  OK    {pdf.name}: {len(chunks)} chunks")

    print("-" * 70)
    print(f"\n[DONE] Processed {processed} PDF(s), skipped {skipped}")
    print(f"       {total_chunks} total chunks written to {output_dir}")
    print(f"\nNext: python scripts/load_chunks.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
