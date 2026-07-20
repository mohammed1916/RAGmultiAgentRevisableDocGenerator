"""Tests for Milvus-based RAG system."""

import pytest
from server.tools import MilvusRAG


class TestMilvusRAG:
    """Test Milvus RAG functionality (with mock mode)."""

    @pytest.fixture
    def rag(self):
        """Create RAG instance in mock mode."""
        rag = MilvusRAG(host="nonexistent", port=99999)  # Force mock mode
        yield rag
        rag.close()

    def test_add_document(self, rag):
        """Test adding document to RAG."""
        rag.add_document(
            doc_id="math_101",
            content="Relations and Functions: Domain, Range, Inverse Functions",
            doc_type="jee_math",
            metadata={"chapter": "1", "level": "advanced"},
        )

        doc = rag.get_document("math_101")
        assert doc is not None
        assert doc["content"] == "Relations and Functions: Domain, Range, Inverse Functions"
        assert doc["document_type"] == "jee_math"

    def test_search_documents(self, rag):
        """Test searching documents."""
        rag.add_document(
            "math_101",
            "Relations and Functions including domain and range",
            "jee_math",
        )
        rag.add_document(
            "math_102", "Calculus covering derivatives and integrals", "jee_math"
        )
        rag.add_document("physics_101", "Mechanics involving force and motion", "jee_physics")

        # Search for math topics
        results = rag.search("relations domain functions", top_k=2)

        assert len(results) > 0
        assert results[0]["doc_id"] == "math_101"

    def test_search_with_filter(self, rag):
        """Test searching with document type filter."""
        rag.add_document("math_101", "Mathematics content", "jee_math")
        rag.add_document("physics_101", "Physics content", "jee_physics")

        # Search only physics
        results = rag.search("content", doc_type="jee_physics", top_k=10)

        assert all(doc["document_type"] == "jee_physics" for doc in results)

    def test_delete_document(self, rag):
        """Test deleting a document."""
        rag.add_document("doc_1", "Content", "test")
        assert rag.get_document("doc_1") is not None

        rag.delete_document("doc_1")
        assert rag.get_document("doc_1") is None

    def test_get_stats(self, rag):
        """Test getting index statistics."""
        rag.add_document("doc_1", "Content 1", "type1")
        rag.add_document("doc_2", "Content 2", "type1")

        stats = rag.get_stats()
        assert stats["total_documents"] == 2
        assert stats["mode"] == "mock"
        assert stats["indexed"] is True

    def test_curriculum_data(self, rag):
        """Test indexing curriculum data."""
        curricula = {
            "jee_math": {
                "Relations and Functions": "Domain, Range, Inverse Functions, Graphing",
                "Matrices": "Properties, Operations, Determinants, Inverse",
                "Calculus": "Limits, Derivatives, Integrals, Applications",
            },
            "cbse_physics": {
                "Electrostatics": "Electric Field, Potential, Capacitors",
                "Optics": "Refraction, Lenses, Interference, Diffraction",
            },
        }

        # Index all
        for doc_type, chapters in curricula.items():
            for chapter, topics in chapters.items():
                rag.add_document(
                    doc_id=f"{doc_type}_{chapter.lower().replace(' ', '_')}",
                    content=f"{chapter}: {topics}",
                    doc_type=doc_type,
                    metadata={"chapter": chapter},
                )

        # Search for JEE math
        results = rag.search("calculus derivatives integrals", top_k=5)
        assert len(results) > 0

        # Verify stats
        stats = rag.get_stats()
        assert stats["total_documents"] == 5

    def test_relevance_scoring(self, rag):
        """Test relevance scoring in search results."""
        rag.add_document("doc_1", "Python programming basics", "course")
        rag.add_document("doc_2", "Advanced Python optimization", "course")
        rag.add_document("doc_3", "Java programming", "course")

        results = rag.search("Python", top_k=3)

        # Python docs should have higher scores
        python_results = [r for r in results if "Python" in r["content"]]
        assert len(python_results) >= 1

    def test_empty_search(self, rag):
        """Test searching on empty database."""
        results = rag.search("any query", top_k=5)
        assert results == []

    def test_large_document(self, rag):
        """Test adding large documents."""
        large_content = "word " * 1000  # 1000 words

        rag.add_document("large_doc", large_content, "test")

        doc = rag.get_document("large_doc")
        assert doc is not None
        assert len(doc["content"]) > 1000


class TestMilvusRAGIntegration:
    """Integration tests with mock curriculum data."""

    def test_jee_curriculum_rag(self):
        """Test RAG with full JEE curriculum."""
        rag = MilvusRAG(host="nonexistent", port=99999)

        jee_topics = {
            "relations_functions": "Domain Range Inverse Functions Graphing",
            "matrices": "Operations Determinants Inverse Matrix Properties",
            "calculus": "Limits Derivatives Integrals Applications",
            "vectors": "Scalar Triple Product Vector Product 3D",
            "coordinate_geometry": "Conic Sections 3D Geometry Lines Planes",
        }

        for topic_id, content in jee_topics.items():
            rag.add_document(
                doc_id=f"jee_math_{topic_id}",
                content=content,
                doc_type="jee_math",
            )

        # Search for calculus
        results = rag.search("calculus derivatives integrals", top_k=3)
        assert len(results) > 0
        assert "jee_math_calculus" in results[0]["doc_id"]

        rag.close()

    def test_cbse_curriculum_rag(self):
        """Test RAG with CBSE curriculum."""
        rag = MilvusRAG(host="nonexistent", port=99999)

        cbse_topics = {
            "electrostatics": "Electric Field Potential Capacitors Dielectrics",
            "optics": "Refraction Lenses Interference Diffraction",
            "waves": "Sound Waves Light Waves Doppler Effect",
            "thermodynamics": "First Law Second Law Heat Capacity",
        }

        for topic_id, content in cbse_topics.items():
            rag.add_document(
                doc_id=f"cbse_physics_{topic_id}",
                content=content,
                doc_type="cbse_physics",
            )

        # Search
        results = rag.search("optics refraction lenses", top_k=3)
        assert len(results) > 0

        rag.close()

    def test_multi_language_curriculum(self):
        """Test RAG with multiple subjects."""
        rag = MilvusRAG(host="nonexistent", port=99999)

        documents = [
            ("math_1", "Algebra Polynomials Equations", "jee_math"),
            ("physics_1", "Mechanics Force Motion Energy", "jee_physics"),
            ("chemistry_1", "Bonding Atoms Molecules Reactions", "jee_chemistry"),
            ("python_1", "Variables Functions Classes Modules", "programming_python"),
        ]

        for doc_id, content, doc_type in documents:
            rag.add_document(doc_id, content, doc_type)

        # Search should find relevant docs
        math_results = rag.search("algebra polynomials", top_k=10)
        physics_results = rag.search("mechanics force", top_k=10)

        assert any("math_1" in r["doc_id"] for r in math_results)
        assert any("physics_1" in r["doc_id"] for r in physics_results)

        rag.close()
