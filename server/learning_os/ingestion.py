"""Profile-scoped data ingestion and retrieval.

Turns uploaded content (PDF or raw text) into embedded, profile-tagged chunks in
Milvus so it can later be retrieved with identity-based (profile-scoped) search
and cross-encoder reranking.

Every chunk carries identity metadata::

    {"user_id", "profile_id", "subject", "chapter", "source", "doc_id", "chunk"}

so retrieval can filter to a single profile instead of scanning the whole store.
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from langchain_text_splitters import RecursiveCharacterTextSplitter

from ..base.logger import setup_logger
from ..tools import MilvusRAG, PDFChunker, Reranker
from ..config import config

logger = setup_logger(__name__)


class IngestionService:
    """Chunk -> embed -> store (with profile metadata) and profile-scoped retrieval."""

    def __init__(
        self,
        rag_system: Optional[MilvusRAG] = None,
        reranker: Optional[Reranker] = None,
        chunk_size: int = None,
        chunk_overlap: int = None,
    ) -> None:
        # rag_system is injected from the orchestrator; it may be None if the
        # vector store was unavailable at startup.
        self._rag = rag_system
        self._reranker = reranker or Reranker()

        chunk_size = chunk_size or config.max_chunk_size
        chunk_overlap = chunk_overlap or config.max_chunk_overlap

        self._pdf_chunker = PDFChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        self._text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

    @property
    def rag_available(self) -> bool:
        return self._rag is not None

    # -------------------------------------------------------------- ingestion

    def ingest_text(
        self,
        *,
        user_id: str,
        profile_id: str,
        text: str,
        subject: Optional[str] = None,
        chapter: Optional[str] = None,
        source: str = "text",
        class_level: str = "12",
    ) -> Dict[str, Any]:
        """Chunk raw text and store it with profile identity metadata."""
        chunks = [c.strip() for c in self._text_splitter.split_text(text) if c.strip()]
        return self._store_chunks(
            user_id=user_id,
            profile_id=profile_id,
            chunks=chunks,
            subject=subject,
            chapter=chapter,
            source=source,
            class_level=class_level,
        )

    def ingest_note(
        self,
        *,
        user_id: str,
        profile_id: str,
        doc_id: str,
        text: str,
        subject: Optional[str] = None,
        chapter: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Chunk and embed a workspace note under a stable doc_id (re-embeddable)."""
        chunks = [c.strip() for c in self._text_splitter.split_text(text) if c.strip()]
        return self._store_chunks(
            user_id=user_id, profile_id=profile_id, chunks=chunks,
            subject=subject, chapter=chapter, source="note", class_level="12",
            doc_id=doc_id,
        )

    def delete_doc(self, profile_id: str, doc_id: str) -> None:
        """Remove all vector chunks for one document/note in a profile."""
        if not self.rag_available:
            return
        self._rag.delete_profile_chunks(profile_id, doc_id)

    def list_corpus(self, profile_id: str, limit: int = 500):
        """Return the profile's stored chunks for corpus-level analysis."""
        if not self.rag_available:
            return []
        return self._rag.list_profile_chunks(profile_id, limit=limit)

    def ingest_pdf(
        self,
        *,
        user_id: str,
        profile_id: str,
        pdf_path: str,
        subject: Optional[str] = None,
        chapter: Optional[str] = None,
        source: Optional[str] = None,
        class_level: str = "12",
    ) -> Dict[str, Any]:
        """Extract, chunk and store a PDF with profile identity metadata."""
        raw_chunks = self._pdf_chunker.process_pdf(Path(pdf_path))
        chunks = [
            (c.get("content") if isinstance(c, dict) else str(c))
            for c in raw_chunks
        ]
        chunks = [c.strip() for c in chunks if c and c.strip()]
        return self._store_chunks(
            user_id=user_id,
            profile_id=profile_id,
            chunks=chunks,
            subject=subject,
            chapter=chapter,
            source=source or "pdf",
            class_level=class_level,
        )

    def _store_chunks(
        self,
        *,
        user_id: str,
        profile_id: str,
        chunks: List[str],
        subject: Optional[str],
        chapter: Optional[str],
        source: str,
        class_level: str,
        doc_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not self.rag_available:
            raise RuntimeError(
                "Vector store (Milvus) is not available; cannot ingest documents"
            )
        if not chunks:
            return {"ingested": 0, "doc_id": doc_id, "source": source}

        doc_id = doc_id or str(uuid.uuid4())
        for chunk in chunks:
            self._rag.add_profile_chunk(
                content=chunk,
                profile_id=profile_id,
                user_id=user_id,
                doc_id=doc_id,
                subject=subject,
                chapter=chapter,
                source=source,
            )
        logger.info(
            "Ingested %d chunks for profile=%s doc_id=%s source=%s",
            len(chunks), profile_id, doc_id, source,
        )
        return {"ingested": len(chunks), "doc_id": doc_id, "source": source}

    # -------------------------------------------------------------- retrieval

    def retrieve(
        self,
        *,
        profile_id: str,
        query: str,
        top_k: int = 5,
        recall_k: int = 20,
    ) -> Dict[str, Any]:
        """Profile-scoped vector search followed by cross-encoder reranking.

        First-stage recall pulls ``recall_k`` candidates filtered to the profile,
        then the reranker orders them and returns the top ``top_k``.
        """
        if not self.rag_available:
            raise RuntimeError("Vector store (Milvus) is not available; cannot retrieve")

        candidates = self._rag.search_profile_chunks(
            query=query,
            profile_id=profile_id,
            top_k=recall_k,
        )
        reranked = self._reranker.rerank(query, candidates, top_k=top_k)
        return {
            "query": query,
            "profile_id": profile_id,
            "reranked": self._reranker.available,
            "results": reranked,
        }
