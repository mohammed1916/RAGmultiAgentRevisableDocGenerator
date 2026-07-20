"""PDF text extraction and chunking for RAG indexing.

Extracts text from PDF files with PyMuPDF and splits it into overlapping
chunks with LangChain's RecursiveCharacterTextSplitter. Filenames following
the CBSE convention (e.g. ``12_Physics_SrSec_2025-26.pdf``) are parsed into
structured metadata.
"""

import re
from pathlib import Path
from typing import Dict, List, Any

import fitz  # PyMuPDF
from langchain_text_splitters import RecursiveCharacterTextSplitter

from ...base.logger import setup_logger

logger = setup_logger(__name__)


class PDFChunker:
    """Extracts and chunks text from PDF documents."""

    def __init__(self, chunk_size: int = 1200, chunk_overlap: int = 200):
        """Initialize the PDF chunker.

        Args:
            chunk_size: Target characters per chunk
            chunk_overlap: Character overlap between consecutive chunks
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

    @staticmethod
    def clean_text(text: str) -> str:
        """Normalize extracted PDF text.

        Args:
            text: Raw text extracted from a PDF

        Returns:
            Cleaned, whitespace-normalized text
        """
        text = text.replace("\x00", "")
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"\n\s*\n", "\n\n", text)
        return text.strip()

    def extract_pdf_text(self, pdf_path: Path) -> str:
        """Extract and clean all text from a PDF.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Cleaned full-document text
        """
        document = fitz.open(pdf_path)
        try:
            pages = [page.get_text() for page in document]
        finally:
            document.close()
        return self.clean_text("\n".join(pages))

    @staticmethod
    def parse_filename(filename: str) -> Dict[str, Any]:
        """Infer metadata from a CBSE-style filename.

        Example:
            ``12_Physics_SrSec_2025-26.pdf`` ->
            class=12, subject=Physics, academic_level=Senior Secondary

        Args:
            filename: PDF filename (with or without path)

        Returns:
            Metadata dictionary
        """
        stem = Path(filename).stem
        parts = stem.split("_")

        metadata: Dict[str, Any] = {
            "document": filename,
            "board": "CBSE",
            "class": None,
            "subject": None,
            "academic_level": None,
        }

        if parts and parts[0].isdigit():
            metadata["class"] = parts[0]

        if "SrSec" in parts:
            metadata["academic_level"] = "Senior Secondary"
            subject_parts = parts[1 : parts.index("SrSec")]
        elif "Sec" in parts:
            metadata["academic_level"] = "Secondary"
            subject_parts = parts[1 : parts.index("Sec")]
        else:
            subject_parts = parts[1:]

        metadata["subject"] = " ".join(subject_parts)
        return metadata

    def chunk_document(self, text: str, filename: str) -> List[Dict[str, Any]]:
        """Convert extracted text into chunk objects.

        Args:
            text: Cleaned document text
            filename: Source PDF filename (used for id + metadata)

        Returns:
            List of chunk dictionaries ready for embedding
        """
        metadata = self.parse_filename(filename)
        text_chunks = self.splitter.split_text(text)
        total = len(text_chunks)
        stem = Path(filename).stem

        chunks = []
        for index, chunk_text in enumerate(text_chunks, start=1):
            chunks.append(
                {
                    "id": f"{stem}_chunk_{index:03d}",
                    "content": chunk_text,
                    "document_type": "syllabus",
                    "metadata": {
                        **metadata,
                        "chunk_index": index,
                        "total_chunks": total,
                    },
                }
            )
        return chunks

    def process_pdf(self, pdf_path: Path, min_chars: int = 100) -> List[Dict[str, Any]]:
        """Extract and chunk a single PDF.

        Args:
            pdf_path: Path to the PDF file
            min_chars: Minimum extracted characters to consider valid

        Returns:
            List of chunk dictionaries (empty if the PDF has too little text)
        """
        text = self.extract_pdf_text(pdf_path)
        if len(text) < min_chars:
            logger.warning(f"Skipped {pdf_path.name}: only {len(text)} chars extracted")
            return []

        chunks = self.chunk_document(text=text, filename=pdf_path.name)
        logger.info(f"Chunked {pdf_path.name}: {len(chunks)} chunks from {len(text)} chars")
        return chunks
