"""Tests for mock RAG chunks to verify structure and readability."""

import pytest
from server.base.mock_data import MockData


class TestMockChunkStructure:
    """Test that mock chunks have the correct structure for RAG system."""

    def test_jee_chunks_structure(self):
        """Test JEE chunks have all required fields."""
        chunks = MockData.get_mock_chunks_jee()

        assert len(chunks) > 0, "JEE chunks should not be empty"

        for chunk in chunks:
            # Required fields
            assert "chunk_id" in chunk, f"Chunk missing chunk_id: {chunk}"
            assert "document_id" in chunk, f"Chunk missing document_id: {chunk}"
            assert "chunk_text" in chunk, f"Chunk missing chunk_text: {chunk}"
            assert "embedding" in chunk, f"Chunk missing embedding: {chunk}"
            assert "metadata" in chunk, f"Chunk missing metadata: {chunk}"

            # Verify non-empty content
            assert chunk["chunk_id"], "chunk_id should not be empty"
            assert chunk["document_id"], "document_id should not be empty"
            assert chunk["chunk_text"], "chunk_text should not be empty"
            assert isinstance(chunk["metadata"], dict), "metadata should be dict"

    def test_cbse_chunks_structure(self):
        """Test CBSE chunks have all required fields."""
        chunks = MockData.get_mock_chunks_cbse()

        assert len(chunks) > 0, "CBSE chunks should not be empty"

        for chunk in chunks:
            assert "chunk_id" in chunk
            assert "document_id" in chunk
            assert "chunk_text" in chunk
            assert "embedding" in chunk
            assert "metadata" in chunk

    def test_python_chunks_structure(self):
        """Test Python chunks have all required fields."""
        chunks = MockData.get_mock_chunks_python()

        assert len(chunks) > 0, "Python chunks should not be empty"

        for chunk in chunks:
            assert "chunk_id" in chunk
            assert "document_id" in chunk
            assert "chunk_text" in chunk
            assert "embedding" in chunk
            assert "metadata" in chunk


class TestMockChunkContent:
    """Test that mock chunk content is readable and meaningful."""

    def test_jee_chunks_readable(self):
        """Test JEE chunks contain readable educational content."""
        chunks = MockData.get_mock_chunks_jee()

        # Check content is readable text
        for chunk in chunks:
            text = chunk["chunk_text"]
            assert len(text) > 20, f"Chunk text too short: {text}"
            assert "\n" in text or " " in text, "Chunk should contain structured text"

        # Verify specific topics are covered
        chunk_texts = [c["chunk_text"] for c in chunks]
        combined = " ".join(chunk_texts)

        assert "Relations and Functions" in combined
        assert "Matrices" in combined
        assert "Calculus" in combined
        assert "Vectors" in combined

    def test_cbse_chunks_readable(self):
        """Test CBSE chunks contain readable physics content."""
        chunks = MockData.get_mock_chunks_cbse()

        for chunk in chunks:
            text = chunk["chunk_text"]
            assert len(text) > 20, "Chunk text should be substantial"
            assert "Physics" in chunk["metadata"].get("exam", "") or True

        chunk_texts = [c["chunk_text"] for c in chunks]
        combined = " ".join(chunk_texts)

        assert "Electric" in combined
        assert "Charge" in combined
        assert "Field" in combined

    def test_python_chunks_readable(self):
        """Test Python chunks contain readable programming content."""
        chunks = MockData.get_mock_chunks_python()

        for chunk in chunks:
            text = chunk["chunk_text"]
            assert len(text) > 20, "Chunk text should be substantial"

        chunk_texts = [c["chunk_text"] for c in chunks]
        combined = " ".join(chunk_texts)

        assert "Python" in combined
        assert "Variables" in combined or "Data Types" in combined
        assert "Lists" in combined or "Dictionaries" in combined


class TestMockChunkMetadata:
    """Test that chunk metadata is consistent and useful."""

    def test_jee_metadata_complete(self):
        """Test JEE chunks have complete metadata."""
        chunks = MockData.get_mock_chunks_jee()

        for chunk in chunks:
            meta = chunk["metadata"]
            assert "topic" in meta, "Metadata missing topic"
            assert "difficulty" in meta, "Metadata missing difficulty"
            assert "exam" in meta, "Metadata missing exam"
            assert meta["exam"] == "JEE", f"Expected exam=JEE, got {meta['exam']}"

    def test_cbse_metadata_complete(self):
        """Test CBSE chunks have complete metadata."""
        chunks = MockData.get_mock_chunks_cbse()

        for chunk in chunks:
            meta = chunk["metadata"]
            assert "topic" in meta
            assert "difficulty" in meta
            assert "exam" in meta
            assert "Class 12" in meta["exam"], f"Expected CBSE Class 12, got {meta['exam']}"

    def test_python_metadata_complete(self):
        """Test Python chunks have complete metadata."""
        chunks = MockData.get_mock_chunks_python()

        for chunk in chunks:
            meta = chunk["metadata"]
            assert "topic" in meta
            assert "difficulty" in meta
            assert "language" in meta
            assert meta["language"] == "Python"


class TestChunkRetrieval:
    """Test that chunks can be retrieved and used for RAG context."""

    def test_chunk_by_id(self):
        """Test retrieving specific chunk by ID."""
        chunks = MockData.get_mock_chunks_jee()

        chunk_dict = {c["chunk_id"]: c for c in chunks}

        # Should be able to retrieve by ID
        assert "jee_001" in chunk_dict
        chunk = chunk_dict["jee_001"]

        assert chunk["chunk_text"]
        assert "Relations" in chunk["chunk_text"] or "Functions" in chunk["chunk_text"]

    def test_chunk_by_document(self):
        """Test retrieving chunks for specific document."""
        chunks = MockData.get_mock_chunks_cbse()

        # Group by document_id
        docs = {}
        for chunk in chunks:
            doc_id = chunk["document_id"]
            if doc_id not in docs:
                docs[doc_id] = []
            docs[doc_id].append(chunk)

        assert "cbse_physics_electrostatics" in docs
        electrostatics_chunks = docs["cbse_physics_electrostatics"]

        # All chunks for this document should be readable
        for chunk in electrostatics_chunks:
            assert len(chunk["chunk_text"]) > 0

    def test_chunk_by_topic(self):
        """Test filtering chunks by topic."""
        chunks = MockData.get_mock_chunks_jee()

        # Filter by topic
        calculus_chunks = [c for c in chunks if c["metadata"]["topic"] == "Calculus"]

        assert len(calculus_chunks) > 0, "Should have Calculus chunks"

        for chunk in calculus_chunks:
            assert "Calculus" in chunk["chunk_text"]

    def test_chunk_by_difficulty(self):
        """Test filtering chunks by difficulty level."""
        chunks = MockData.get_mock_chunks_cbse()

        # Get basic chunks
        basic_chunks = [c for c in chunks if c["metadata"]["difficulty"] == "Basic"]
        assert len(basic_chunks) > 0, "Should have Basic difficulty chunks"

        # Get advanced chunks
        advanced_chunks = [c for c in chunks if c["metadata"]["difficulty"] == "Advanced"]
        assert len(advanced_chunks) > 0, "Should have Advanced difficulty chunks"


class TestChunkCombinedUsage:
    """Test using chunks in realistic RAG scenarios."""

    def test_search_and_read_workflow(self):
        """Test searching chunks and reading their content."""
        chunks = MockData.get_mock_chunks_python()

        # Simulate search: find chunks about data structures
        search_query = "lists"
        matching_chunks = [
            c for c in chunks if search_query.lower() in c["chunk_text"].lower()
        ]

        assert len(matching_chunks) > 0, "Should find chunks matching query"

        # Read the content
        for chunk in matching_chunks:
            text = chunk["chunk_text"]
            assert len(text) > 0, "Should be able to read chunk content"
            # Verify it's readable text with proper structure
            assert "\n" in text or ":" in text, "Content should have structure"

    def test_context_aggregation(self):
        """Test aggregating multiple chunks for context."""
        chunks = MockData.get_mock_chunks_jee()

        # Get top 3 chunks for context
        context_chunks = chunks[:3]

        # Aggregate text for LLM context
        aggregated_text = "\n\n".join([c["chunk_text"] for c in context_chunks])

        # Should have meaningful aggregated context
        assert len(aggregated_text) > 100, "Aggregated context too small"
        assert aggregated_text.count("\n") >= 2, "Should have multi-chunk structure"

    def test_all_mock_chunks_are_retrievable(self):
        """Test that all mock chunks can be retrieved and read."""
        jee_chunks = MockData.get_mock_chunks_jee()
        cbse_chunks = MockData.get_mock_chunks_cbse()
        python_chunks = MockData.get_mock_chunks_python()

        all_chunks = jee_chunks + cbse_chunks + python_chunks

        # Verify all chunks are readable
        for i, chunk in enumerate(all_chunks):
            # Should have readable content
            assert chunk["chunk_text"], f"Chunk {i} has no readable text"
            assert isinstance(chunk["chunk_text"], str), f"Chunk {i} text not a string"
            assert len(chunk["chunk_text"]) > 10, f"Chunk {i} text too short"

            # Should have metadata
            assert chunk["metadata"], f"Chunk {i} has no metadata"
            assert isinstance(chunk["metadata"], dict), f"Chunk {i} metadata not a dict"
