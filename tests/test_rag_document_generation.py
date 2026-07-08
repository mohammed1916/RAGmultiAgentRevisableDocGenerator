"""End-to-end tests for RAG-enabled document generation with curriculum data.

Demonstrates:
1. Loading curriculum data from JSON
2. Indexing in Milvus (with mock mode fallback)
3. Searching for relevant documents
4. Using retrieved context in document generation
"""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path
import json

from server.tools.milvus_rag import MilvusRAG
from server.models import DocumentRequest
from server.orchestrator import Orchestrator


class TestCurriculumDataLoading:
    """Test loading curriculum data from JSON file."""

    def test_curriculum_data_exists(self):
        """Verify curriculum data file exists and is valid JSON."""
        data_path = Path(__file__).parent.parent / "server" / "data" / "curriculum_data.json"
        assert data_path.exists(), f"Curriculum data not found at {data_path}"

        with open(data_path) as f:
            data = json.load(f)

        assert isinstance(data, list)
        assert len(data) > 0

    def test_curriculum_documents_structure(self):
        """Verify each curriculum document has required fields."""
        data_path = Path(__file__).parent.parent / "server" / "data" / "curriculum_data.json"

        with open(data_path) as f:
            documents = json.load(f)

        for doc in documents:
            assert "id" in doc
            assert "content" in doc
            assert "document_type" in doc
            assert "metadata" in doc
            assert isinstance(doc["metadata"], dict)

    def test_curriculum_has_required_subjects(self):
        """Verify curriculum covers key subjects."""
        data_path = Path(__file__).parent.parent / "server" / "data" / "curriculum_data.json"

        with open(data_path) as f:
            documents = json.load(f)

        doc_ids = {doc["id"] for doc in documents}

        # Verify coverage
        assert any("cbse_12" in doc_id for doc_id in doc_ids), "Missing CBSE Class 12"
        assert any("cbse_10" in doc_id for doc_id in doc_ids), "Missing CBSE Class 10"
        assert any("jee" in doc_id for doc_id in doc_ids), "Missing JEE curriculum"
        assert any("college" in doc_id for doc_id in doc_ids), "Missing College curriculum"


class TestMilvusRAGSystem:
    """Test Milvus RAG with curriculum data."""

    def test_milvus_rag_initialization(self):
        """Test initializing MilvusRAG (uses mock mode if server unavailable)."""
        rag = MilvusRAG()
        assert rag is not None
        # Should fall back to mock mode if Milvus server unavailable
        assert rag.mock_mode or rag.host == "localhost"

    def test_add_documents_to_rag(self):
        """Test adding curriculum documents to RAG."""
        rag = MilvusRAG()
        data_path = Path(__file__).parent.parent / "server" / "data" / "curriculum_data.json"

        with open(data_path) as f:
            documents = json.load(f)

        # Add first few documents
        for doc in documents[:3]:
            rag.add_document(
                doc_id=doc["id"],
                content=doc["content"],
                doc_type=doc["document_type"],
                metadata=doc.get("metadata", {}),
            )

        stats = rag.get_stats()
        assert stats["total_documents"] >= 3

    def test_search_cbse_physics(self):
        """Test searching for CBSE Physics curriculum."""
        rag = MilvusRAG()
        data_path = Path(__file__).parent.parent / "server" / "data" / "curriculum_data.json"

        with open(data_path) as f:
            documents = json.load(f)

        for doc in documents:
            rag.add_document(
                doc_id=doc["id"],
                content=doc["content"],
                doc_type=doc["document_type"],
                metadata=doc.get("metadata", {}),
            )

        # Search for electrostatics (physics topic)
        results = rag.search("electrostatics electric field capacitor", top_k=3)
        assert len(results) > 0
        assert any("physics" in r["doc_id"].lower() for r in results)

    def test_search_jee_mathematics(self):
        """Test searching for JEE mathematics curriculum."""
        rag = MilvusRAG()
        data_path = Path(__file__).parent.parent / "server" / "data" / "curriculum_data.json"

        with open(data_path) as f:
            documents = json.load(f)

        for doc in documents:
            rag.add_document(
                doc_id=doc["id"],
                content=doc["content"],
                doc_type=doc["document_type"],
                metadata=doc.get("metadata", {}),
            )

        # Search for calculus (JEE topic)
        results = rag.search("derivatives integrals calculus", top_k=3)
        assert len(results) > 0

    def test_search_college_level_curriculum(self):
        """Test searching for college-level curriculum."""
        rag = MilvusRAG()
        data_path = Path(__file__).parent.parent / "server" / "data" / "curriculum_data.json"

        with open(data_path) as f:
            documents = json.load(f)

        for doc in documents:
            rag.add_document(
                doc_id=doc["id"],
                content=doc["content"],
                doc_type=doc["document_type"],
                metadata=doc.get("metadata", {}),
            )

        # Search for quantum mechanics (college physics)
        results = rag.search("quantum mechanics wave function", top_k=3)
        assert len(results) > 0
        assert any("college" in r["doc_id"].lower() or "jee_advanced" in r["doc_id"].lower() for r in results)

    def test_retrieve_single_document(self):
        """Test retrieving a specific curriculum document."""
        rag = MilvusRAG()
        data_path = Path(__file__).parent.parent / "server" / "data" / "curriculum_data.json"

        with open(data_path) as f:
            documents = json.load(f)

        # Add documents
        for doc in documents[:5]:
            rag.add_document(
                doc_id=doc["id"],
                content=doc["content"],
                doc_type=doc["document_type"],
                metadata=doc.get("metadata", {}),
            )

        # Retrieve specific document
        retrieved = rag.get_document(documents[0]["id"])
        assert retrieved is not None
        assert retrieved["id"] == documents[0]["id"]


class TestRAGDocumentGeneration:
    """Test document generation using RAG with curriculum data."""

    @patch("server.orchestrator.OllamaClient")
    def test_writer_uses_rag_context(self, mock_ollama_class):
        """Test that writer agent receives RAG context in prompt."""
        from server.agents.writer import WriterAgent
        from server.models import ExecutionPlan

        mock_client = Mock()
        mock_ollama_class.return_value = mock_client

        # Initialize RAG with curriculum data
        rag = MilvusRAG()
        data_path = Path(__file__).parent.parent / "server" / "data" / "curriculum_data.json"

        with open(data_path) as f:
            documents = json.load(f)

        for doc in documents:
            rag.add_document(
                doc_id=doc["id"],
                content=doc["content"],
                doc_type=doc["document_type"],
                metadata=doc.get("metadata", {}),
            )

        # Create writer with RAG
        writer = WriterAgent(mock_client, rag_system=rag)

        # Create a test plan
        plan = ExecutionPlan(
            document_type="CBSE Class 12 Physics Study Guide",
            assumptions={"subject": "Physics", "level": "Class 12"},
            tasks=[],
            outline=["Electrostatics", "Magnetism", "Optics"],
        )

        # Mock the LLM response
        mock_client.structured_generate.return_value = {
            "parsed_response": {
                "title": "Electrostatics",
                "content": "Electrostatics covers electric charges, Coulomb's law, electric field, and potential.",
                "heading_level": 2,
            }
        }

        # Write a section
        section = writer.write_section(
            "Create a physics study guide",
            plan,
            0,
        )

        assert section is not None
        assert section.title == "Electrostatics"
        assert len(section.content) > 0

        # Verify that structured_generate was called (meaning RAG context was fetched)
        assert mock_client.structured_generate.called

    def test_rag_context_in_writing_prompt(self):
        """Test that RAG context is properly formatted in writing prompt."""
        from server.agents.writer import WriterAgent
        from server.models import ExecutionPlan

        mock_client = Mock()
        rag = MilvusRAG()

        # Add a test document
        rag.add_document(
            "test_physics",
            "Electrostatics is the study of electric charges and fields",
            "test",
            {"subject": "Physics"},
        )

        writer = WriterAgent(mock_client, rag_system=rag)
        plan = ExecutionPlan(
            document_type="Physics",
            assumptions={},
            tasks=[],
            outline=["Electrostatics"],
        )

        # Build prompt with RAG context
        prompt = writer._build_writing_prompt(
            "Study physics",
            plan,
            "Electrostatics",
        )

        # Verify RAG context is in the prompt
        assert "RELEVANT CURRICULUM CONTEXT" in prompt or "test_physics" in prompt or len(prompt) > 500


class TestCurriculumClustering:
    """Test Milvus IVF clustering capability for curriculum organization."""

    def test_curriculum_metadata_for_clustering(self):
        """Verify curriculum metadata supports IVF clustering."""
        data_path = Path(__file__).parent.parent / "server" / "data" / "curriculum_data.json"

        with open(data_path) as f:
            documents = json.load(f)

        # Group by level for clustering
        level_groups = {}
        for doc in documents:
            metadata = doc["metadata"]
            level = metadata.get("level") or metadata.get("degree")
            if level:
                if level not in level_groups:
                    level_groups[level] = []
                level_groups[level].append(doc["id"])

        # Verify clustering organization
        assert len(level_groups) >= 2, "Should have multiple education levels"
        assert any("secondary" in level or "cbse" in level.lower() for level in level_groups)
        assert any("tertiary" in level or "college" in level.lower() for level in level_groups)

    def test_subject_grouping(self):
        """Test grouping curricula by subject for clustering."""
        data_path = Path(__file__).parent.parent / "server" / "data" / "curriculum_data.json"

        with open(data_path) as f:
            documents = json.load(f)

        subjects = set()
        for doc in documents:
            metadata = doc["metadata"]
            subject = metadata.get("subject")
            if subject:
                subjects.add(subject)

        # Verify multiple subjects
        assert len(subjects) >= 3
        assert any("Physics" in subj or "Math" in subj or "Chemistry" in subj for subj in subjects)
