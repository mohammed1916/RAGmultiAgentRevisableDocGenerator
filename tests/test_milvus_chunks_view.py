"""Tests for viewing and listing chunks from Milvus RAG."""

import pytest
from server.tools.milvus_rag import MilvusRAG
from server.mock_data import MockData


class TestMilvusChunkViewing:
    """Test viewing chunks in Milvus RAG."""

    @pytest.fixture
    def rag_with_mock_chunks(self):
        """Initialize RAG and load mock chunks."""
        rag = MilvusRAG()

        # Load mock chunks
        jee_chunks = MockData.get_mock_chunks_jee()
        cbse_chunks = MockData.get_mock_chunks_cbse()
        python_chunks = MockData.get_mock_chunks_python()

        all_chunks = jee_chunks + cbse_chunks + python_chunks

        for chunk in all_chunks:
            rag.add_document(
                doc_id=chunk["chunk_id"],
                content=chunk["chunk_text"],
                doc_type=chunk["document_id"],
                metadata=chunk["metadata"],
            )

        yield rag

        rag.close()

    def test_list_all_documents(self, rag_with_mock_chunks):
        """Test listing all stored documents."""
        documents = rag_with_mock_chunks.list_all_documents()

        assert len(documents) >= 10, f"Expected at least 10 chunks, got {len(documents)}"

        # Check structure
        for doc in documents:
            assert "doc_id" in doc
            assert "content" in doc
            assert "document_type" in doc
            assert "metadata" in doc

    def test_list_all_has_required_chunks(self, rag_with_mock_chunks):
        """Test that all required chunks are listed."""
        documents = rag_with_mock_chunks.list_all_documents()
        doc_ids = [d["doc_id"] for d in documents]

        # Check JEE chunks
        assert "jee_001" in doc_ids
        assert "jee_002" in doc_ids
        assert "jee_003" in doc_ids
        assert "jee_004" in doc_ids

        # Check CBSE chunks
        assert "cbse_001" in doc_ids
        assert "cbse_002" in doc_ids
        assert "cbse_003" in doc_ids

        # Check Python chunks
        assert "py_001" in doc_ids
        assert "py_002" in doc_ids
        assert "py_003" in doc_ids

    def test_list_by_type_jee(self, rag_with_mock_chunks):
        """Test listing chunks by JEE document type."""
        documents = rag_with_mock_chunks.list_by_type("jee_math_curriculum")

        assert len(documents) == 4, f"Expected 4 JEE chunks, got {len(documents)}"

        # Verify all are JEE chunks
        for doc in documents:
            assert doc["document_type"] == "jee_math_curriculum"

    def test_list_by_type_cbse(self, rag_with_mock_chunks):
        """Test listing chunks by CBSE document type."""
        documents = rag_with_mock_chunks.list_by_type("cbse_physics_electrostatics")

        assert len(documents) == 3, f"Expected 3 CBSE chunks, got {len(documents)}"

        for doc in documents:
            assert doc["document_type"] == "cbse_physics_electrostatics"

    def test_list_by_type_python(self, rag_with_mock_chunks):
        """Test listing chunks by Python document type."""
        documents = rag_with_mock_chunks.list_by_type("python_week1_curriculum")

        assert len(documents) == 3, f"Expected 3 Python chunks, got {len(documents)}"

        for doc in documents:
            assert doc["document_type"] == "python_week1_curriculum"

    def test_list_by_type_empty(self, rag_with_mock_chunks):
        """Test listing chunks with non-existent type."""
        documents = rag_with_mock_chunks.list_by_type("nonexistent_type")

        assert len(documents) == 0

    def test_list_content_is_readable(self, rag_with_mock_chunks):
        """Test that listed chunk content is readable."""
        documents = rag_with_mock_chunks.list_all_documents()

        for doc in documents:
            content = doc["content"]
            assert isinstance(content, str), f"Content should be string for {doc['doc_id']}"
            assert len(content) > 0, f"Content should not be empty for {doc['doc_id']}"
            assert len(content) > 20, f"Content should be substantial for {doc['doc_id']}"

    def test_list_metadata_is_valid(self, rag_with_mock_chunks):
        """Test that metadata in listed documents is valid."""
        documents = rag_with_mock_chunks.list_all_documents()

        for doc in documents:
            metadata = doc["metadata"]
            assert isinstance(metadata, dict), f"Metadata should be dict for {doc['doc_id']}"

            # Check for expected fields based on type
            if "jee" in doc["document_type"].lower():
                assert "topic" in metadata
                assert "difficulty" in metadata
                assert "exam" in metadata

            elif "cbse" in doc["document_type"].lower():
                assert "topic" in metadata
                assert "difficulty" in metadata

            elif "python" in doc["document_type"].lower():
                assert "topic" in metadata
                assert "language" in metadata

    def test_get_specific_document(self, rag_with_mock_chunks):
        """Test retrieving a specific document by ID."""
        doc = rag_with_mock_chunks.get_document("jee_001")

        assert doc is not None
        assert doc.get("id") == "jee_001" or doc.get("doc_id") == "jee_001"
        assert "content" in doc or "chunk_text" in str(doc).lower()

    def test_get_nonexistent_document(self, rag_with_mock_chunks):
        """Test retrieving non-existent document returns None."""
        doc = rag_with_mock_chunks.get_document("nonexistent_id")

        assert doc is None

    def test_stats_show_all_chunks(self, rag_with_mock_chunks):
        """Test that statistics show correct chunk count."""
        stats = rag_with_mock_chunks.get_stats()

        assert "total_documents" in stats
        assert stats["total_documents"] >= 10

    def test_stats_show_indexed_status(self, rag_with_mock_chunks):
        """Test that statistics show indexing status."""
        stats = rag_with_mock_chunks.get_stats()

        assert "indexed" in stats
        assert stats["indexed"] is True


class TestChunkSearchAndRetrieve:
    """Test searching and retrieving chunks."""

    @pytest.fixture
    def rag_with_chunks(self):
        """Initialize RAG with mock chunks."""
        rag = MilvusRAG()

        jee_chunks = MockData.get_mock_chunks_jee()
        for chunk in jee_chunks:
            rag.add_document(
                doc_id=chunk["chunk_id"],
                content=chunk["chunk_text"],
                doc_type=chunk["document_id"],
                metadata=chunk["metadata"],
            )

        yield rag
        rag.close()

    def test_search_returns_results(self, rag_with_chunks):
        """Test that search returns results."""
        results = rag_with_chunks.search("Functions", top_k=3)

        assert len(results) > 0, "Search should return results"

    def test_search_results_have_content(self, rag_with_chunks):
        """Test that search results include content."""
        results = rag_with_chunks.search("Matrices", top_k=3)

        for result in results:
            assert "content" in result
            assert len(result["content"]) > 0

    def test_search_by_document_type(self, rag_with_chunks):
        """Test filtering search by document type."""
        results = rag_with_chunks.search("Functions", top_k=10)

        assert len(results) > 0

    def test_search_ordering_by_relevance(self, rag_with_chunks):
        """Test that search results are ordered by relevance."""
        results = rag_with_chunks.search("Functions", top_k=3)

        # Results should be ordered by relevance_score
        scores = [r["relevance_score"] for r in results]
        assert scores == sorted(scores, reverse=True), "Results should be ordered by relevance"


class TestChunkViewingEdgeCases:
    """Test edge cases in chunk viewing."""

    def test_empty_storage_list_all(self):
        """Test listing when storage is empty."""
        rag = MilvusRAG()
        documents = rag.list_all_documents()

        assert isinstance(documents, list)
        # Should be empty initially
        assert len(documents) == 0
        rag.close()

    def test_empty_storage_list_by_type(self):
        """Test listing by type when storage is empty."""
        rag = MilvusRAG()
        documents = rag.list_by_type("any_type")

        assert isinstance(documents, list)
        assert len(documents) == 0
        rag.close()

    def test_single_chunk_operations(self):
        """Test operations with single chunk."""
        rag = MilvusRAG()

        # Add one chunk
        rag.add_document(
            doc_id="test_001",
            content="Test content about functions",
            doc_type="test_type",
            metadata={"topic": "Test"},
        )

        # List all
        all_docs = rag.list_all_documents()
        assert len(all_docs) == 1

        # List by type
        typed_docs = rag.list_by_type("test_type")
        assert len(typed_docs) == 1

        # Get specific
        doc = rag.get_document("test_001")
        assert doc is not None

        rag.close()
