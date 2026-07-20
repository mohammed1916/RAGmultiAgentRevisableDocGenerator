"""Document loader and chunker for converting documents to RAG chunks.

Reads documents (JSON), splits into chunks, stores in Milvus.
"""

import json
import re
from typing import List, Dict, Any
from pathlib import Path
from ...base.logger import setup_logger

logger = setup_logger(__name__)


class DocumentChunker:
    """Splits documents into chunks for RAG indexing."""

    def __init__(self, chunk_size: int = 500, overlap: int = 100):
        """Initialize chunker.

        Args:
            chunk_size: Characters per chunk
            overlap: Character overlap between chunks
        """
        self.chunk_size = chunk_size
        self.overlap = overlap

    def load_json_document(self, filepath: str) -> Dict[str, Any]:
        """Load document from JSON file.

        Args:
            filepath: Path to JSON document

        Returns:
            Document dictionary
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)

    def chunk_by_sentences(self, text: str) -> List[str]:
        """Split text into sentence-based chunks.

        Args:
            text: Full document text

        Returns:
            List of text chunks
        """
        sentences = re.split(r'(?<=[.!?])\s+', text)

        chunks = []
        current_chunk = ""

        for sentence in sentences:
            if len(current_chunk) + len(sentence) < self.chunk_size:
                current_chunk += sentence + " "
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence + " "

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    def chunk_by_size(self, text: str) -> List[str]:
        """Split text into fixed-size chunks with overlap.

        Args:
            text: Full document text

        Returns:
            List of text chunks
        """
        chunks = []
        start = 0

        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            chunk = text[start:end].strip()

            if chunk:
                chunks.append(chunk)

            start += self.chunk_size - self.overlap

        return chunks

    def chunk_by_sections(self, text: str) -> List[str]:
        """Split text by markdown headers (sections).

        Args:
            text: Full document text

        Returns:
            List of text chunks (one per section)
        """
        sections = re.split(r'\n#+\s+', text)
        return [s.strip() for s in sections if s.strip()]

    def create_chunks(
        self,
        doc_id: str,
        document: Dict[str, Any],
        chunking_method: str = "sentences"
    ) -> List[Dict[str, Any]]:
        """Create chunks from a document.

        Args:
            doc_id: Document identifier
            document: Document dictionary with 'content' and 'metadata'
            chunking_method: 'sentences', 'size', or 'sections'

        Returns:
            List of chunk dictionaries
        """
        content = document.get("content", "")
        metadata = document.get("metadata", {})
        title = document.get("title", "")
        subject = document.get("subject", "")

        # Choose chunking method
        if chunking_method == "sentences":
            text_chunks = self.chunk_by_sentences(content)
        elif chunking_method == "sections":
            text_chunks = self.chunk_by_sections(content)
        else:  # size
            text_chunks = self.chunk_by_size(content)

        # Create chunk objects
        chunks = []
        for i, chunk_text in enumerate(text_chunks, 1):
            if not chunk_text.strip():
                continue

            chunk = {
                "chunk_id": f"{doc_id}_chunk_{i}",
                "document_id": doc_id,
                "chunk_text": chunk_text,
                "embedding": None,
                "metadata": {
                    **metadata,
                    "source_title": title,
                    "source_subject": subject,
                    "chunk_index": i,
                    "total_chunks": len(text_chunks),
                }
            }
            chunks.append(chunk)

        logger.info(f"Created {len(chunks)} chunks from {doc_id}")
        return chunks

    def process_document_file(
        self,
        filepath: str,
        chunking_method: str = "sentences"
    ) -> List[Dict[str, Any]]:
        """Load and chunk a JSON document file.

        Args:
            filepath: Path to JSON document
            chunking_method: How to split the document

        Returns:
            List of chunks
        """
        logger.info(f"Processing document: {filepath}")

        try:
            document = self.load_json_document(filepath)
            doc_id = document.get("id", Path(filepath).stem)

            chunks = self.create_chunks(
                doc_id=doc_id,
                document=document,
                chunking_method=chunking_method
            )

            return chunks

        except Exception as e:
            logger.error(f"Failed to process {filepath}: {e}")
            return []

    def process_documents_directory(
        self,
        directory: str,
        chunking_method: str = "sentences"
    ) -> List[Dict[str, Any]]:
        """Load and chunk all JSON documents in a directory.

        Args:
            directory: Path to directory containing JSON files
            chunking_method: How to split documents

        Returns:
            All chunks from all documents
        """
        doc_dir = Path(directory)
        all_chunks = []

        logger.info(f"Processing documents from: {directory}")

        for json_file in doc_dir.glob("*.json"):
            if json_file.name == "schema.json":
                continue

            chunks = self.process_document_file(
                str(json_file),
                chunking_method=chunking_method
            )
            all_chunks.extend(chunks)

        logger.info(f"Total chunks created: {len(all_chunks)}")
        return all_chunks
