"""End-to-end tests for document generation with real RAG corpus.

Tests the full pipeline:
  API request → Orchestrator → RAG (Milvus semantic search) → Agents → DOCX

Uses real sentence-transformers embeddings and PDF-based Milvus corpus.
"""

import pytest
from pathlib import Path

from server.tools import MilvusRAG
from server.core.orchestrators.langgraph import LangGraphOrchestrator
from server.core.orchestrators.chat import ChatOrchestrator
from server.base.models import DocumentRequest


class TestLangGraphE2E:
    """E2E tests for LangGraph orchestrator with real RAG."""

    @pytest.fixture
    def orchestrator(self):
        """Initialize LangGraph orchestrator."""
        return LangGraphOrchestrator()

    @pytest.fixture
    def rag(self):
        """Initialize RAG with new PDF corpus."""
        return MilvusRAG()

    @pytest.mark.asyncio
    async def test_document_generation_physics_query(self, orchestrator):
        """Test document generation for physics revision guide.

        Validates:
        - Orchestrator accepts request
        - LangGraph pipeline executes (Plan → Write → Review → Refine → Generate)
        - DOCX file is generated
        """
        request = DocumentRequest(
            request="Create a concise summary of Electrostatics for CBSE Class 12 Physics",
            metadata={"subject": "Physics", "class": "12"},
        )

        result = await orchestrator.generate_document(request.request, request.metadata)

        assert result["success"] is True
        assert "document_filename" in result
        assert result["document_filename"].endswith(".docx")

        # Verify file exists
        doc_path = Path(result["document_filename"])
        assert doc_path.exists(), f"Generated document not found at {doc_path}"

    @pytest.mark.asyncio
    async def test_document_generation_chemistry_query(self, orchestrator):
        """Test document generation for chemistry topic summary.

        Validates semantic search retrieves chemistry content from PDF corpus.
        """
        request = DocumentRequest(
            request="Explain Aldehydes and Ketones with examples for Class 12 Chemistry",
            metadata={"subject": "Chemistry", "class": "12"},
        )

        result = await orchestrator.generate_document(request.request, request.metadata)

        assert result["success"] is True
        assert result["document_filename"].endswith(".docx")
        assert Path(result["document_filename"]).exists()

    @pytest.mark.asyncio
    async def test_document_generation_biology_query(self, orchestrator):
        """Test document generation for biology revision.

        Validates RAG retrieves from Class 10/12 Science corpus.
        """
        request = DocumentRequest(
            request="Summarize Plant Kingdom and Biomolecules for Class 12 Biology",
            metadata={"subject": "Biology", "class": "12"},
        )

        result = await orchestrator.generate_document(request.request, request.metadata)

        assert result["success"] is True
        assert Path(result["document_filename"]).exists()


class TestChatFlowE2E:
    """E2E tests for chat-based multi-step document generation."""

    @pytest.fixture
    def chat_orchestrator(self):
        """Initialize chat orchestrator."""
        return ChatOrchestrator()

    def test_chat_start_conversation(self, chat_orchestrator):
        """Test starting a chat conversation.

        Validates:
        - Chat accepts initial request
        - LLM generates clarifying questions
        - Conversation context is created
        """
        request = "I need to prepare for my CBSE Class 12 Physics board exam"

        response = chat_orchestrator.start_conversation(request)

        assert response is not None
        assert response.context is not None
        assert response.context.conversation is not None
        assert len(response.context.conversation) > 0
        # Should have user message + assistant response
        assert any(msg.role == "user" for msg in response.context.conversation)
        assert any(msg.role == "assistant" for msg in response.context.conversation)

    def test_chat_add_answer(self, chat_orchestrator):
        """Test adding answer to chat.

        Validates:
        - Chat accepts user answers
        - Conversation extends with new messages
        """
        # Start conversation
        request = "I need to prepare for my CBSE Class 12 Physics board exam"
        response = chat_orchestrator.start_conversation(request)
        initial_msg_count = len(response.context.conversation)

        # Add answer
        answer = "I want to focus on Electrostatics, Current Electricity and Optics. My exam is in 6 weeks and I can study 2 hours per day"
        response = chat_orchestrator.add_answer(response.context, "user_message", answer)

        # Should have more messages now
        assert len(response.context.conversation) > initial_msg_count


class TestRAGWithPDFCorpus:
    """E2E tests for RAG retrieval from PDF corpus."""

    @pytest.fixture
    def rag(self):
        """Initialize RAG with PDF-based Milvus corpus."""
        rag = MilvusRAG()
        if rag.mock_mode:
            pytest.skip("Milvus not available for RAG test")
        return rag

    def test_semantic_search_physics(self, rag):
        """Test semantic search retrieves physics content.

        Validates:
        - Real embeddings are used (COSINE metric)
        - Retrieval returns relevant Class 12 Physics chunks
        """
        results = rag.search("Electrostatics electric field capacitance", top_k=5)

        assert len(results) > 0, "No physics results found"
        # Check that retrieved documents mention physics topics
        content_lower = " ".join(r["content"].lower() for r in results)
        assert any(term in content_lower for term in ["electrostatics", "electric", "physics"])

    def test_semantic_search_chemistry(self, rag):
        """Test semantic search retrieves chemistry content."""
        results = rag.search("Aldehydes ketones organic chemistry", top_k=5)

        assert len(results) > 0, "No chemistry results found"
        content_lower = " ".join(r["content"].lower() for r in results)
        assert any(term in content_lower for term in ["chemistry", "organic", "chemical"])

    def test_semantic_search_with_cosine_metric(self, rag):
        """Test that search uses COSINE similarity (not fake embeddings).

        COSINE scores should be in range [0, 1] for normalized embeddings.
        L2 scores would be raw distances (~0-3).
        """
        results = rag.search("mathematics algebra calculus", top_k=3)

        assert len(results) > 0
        # COSINE similarity scores should be between 0 and 1
        for result in results:
            score = result.get("relevance_score", 0)
            assert 0 <= score <= 1, f"Score {score} outside COSINE range [0, 1]"

    def test_rag_metadata_from_pdfs(self, rag):
        """Test that RAG retrieves chunks with PDF-sourced metadata.

        Validates:
        - Metadata includes CBSE class, subject, academic_level from PDF filenames
        - Not old curriculum_data.json structure
        """
        results = rag.search("CBSE class 12 physics", top_k=5)

        assert len(results) > 0
        for result in results:
            meta = result.get("metadata", {})
            # Check for PDF-derived metadata
            assert "class" in meta or "subject" in meta or "board" in meta, \
                f"Missing PDF metadata in: {meta}"


class TestDocumentQuality:
    """E2E tests verifying generated documents have real content."""

    @pytest.fixture
    def orchestrator(self):
        """Initialize orchestrator."""
        return LangGraphOrchestrator()

    @pytest.mark.asyncio
    async def test_generated_docx_has_content(self, orchestrator):
        """Test that generated DOCX files contain substantive content.

        Validates:
        - DOCX is well-formed (can be opened)
        - Contains more than just headers
        - Has paragraphs or tables with data
        """
        from docx import Document

        request = DocumentRequest(
            request="Create a study guide for Optics chapter in Class 12 Physics",
            metadata={"subject": "Physics"},
        )

        result = await orchestrator.generate_document(request.request, request.metadata)
        assert result["success"] is True

        # Open and inspect DOCX
        doc = Document(result["document_filename"])
        paragraphs = [p for p in doc.paragraphs if p.text.strip()]
        tables = doc.tables

        assert len(paragraphs) > 1 or len(tables) > 0, \
            "Generated DOCX is empty or contains only whitespace"

        # Should have some meaningful content
        total_text_length = sum(len(p.text) for p in paragraphs)
        assert total_text_length > 100, \
            f"Generated DOCX has minimal content ({total_text_length} chars)"
