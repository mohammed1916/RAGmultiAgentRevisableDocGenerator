"""Tests for the DOCX generator."""

import os
import tempfile
import pytest

from server.tools.docx_generator import DOCXGenerator
from server.models import DocumentSection, DocumentStructure
from server.exceptions import DOCXGenerationException


class TestDOCXGenerator:
    """Test cases for DOCXGenerator."""

    def test_create_document(self):
        """Test document creation."""
        gen = DOCXGenerator()
        gen.create_document("Test Title")

        assert gen.doc is not None

    def test_add_title(self):
        """Test adding a title."""
        gen = DOCXGenerator()
        gen.create_document()
        gen.add_title("Document Title")

        # Check that title was added
        assert len(gen.doc.paragraphs) > 0

    def test_add_heading(self):
        """Test adding headings."""
        gen = DOCXGenerator()
        gen.create_document()
        gen.add_heading("Heading 1", level=1)
        gen.add_heading("Heading 2", level=2)
        gen.add_heading("Heading 3", level=3)

        assert len(gen.doc.paragraphs) >= 3

    def test_add_heading_invalid_level(self):
        """Test adding heading with invalid level."""
        gen = DOCXGenerator()
        gen.create_document()

        with pytest.raises(ValueError):
            gen.add_heading("Invalid", level=4)

    def test_add_paragraph(self):
        """Test adding paragraphs."""
        gen = DOCXGenerator()
        gen.create_document()
        gen.add_paragraph("Test paragraph")

        assert any("Test paragraph" in p.text for p in gen.doc.paragraphs)

    def test_add_bullet_list(self):
        """Test adding bullet lists."""
        gen = DOCXGenerator()
        gen.create_document()

        items = ["Item 1", "Item 2", "Item 3"]
        gen.add_bullet_list(items)

        assert len(gen.doc.paragraphs) >= len(items)

    def test_add_numbered_list(self):
        """Test adding numbered lists."""
        gen = DOCXGenerator()
        gen.create_document()

        items = ["First", "Second", "Third"]
        gen.add_numbered_list(items)

        assert len(gen.doc.paragraphs) >= len(items)

    def test_add_table(self):
        """Test adding tables."""
        gen = DOCXGenerator()
        gen.create_document()

        data = [
            ["Header 1", "Header 2"],
            ["Row 1 Col 1", "Row 1 Col 2"],
            ["Row 2 Col 1", "Row 2 Col 2"],
        ]
        gen.add_table(3, 2, data)

        assert len(gen.doc.tables) > 0

    def test_add_page_break(self):
        """Test adding page breaks."""
        gen = DOCXGenerator()
        gen.create_document()
        gen.add_paragraph("Page 1")
        gen.add_page_break()
        gen.add_paragraph("Page 2")

        # Check that paragraphs were added
        assert len(gen.doc.paragraphs) >= 2

    def test_save_document(self):
        """Test saving document."""
        gen = DOCXGenerator()
        gen.create_document("Test")
        gen.add_paragraph("Test content")

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "test.docx")
            saved_path = gen.save(filepath)

            assert os.path.exists(saved_path)
            assert saved_path.endswith("test.docx")

    def test_save_without_creation(self):
        """Test saving without creating document first."""
        gen = DOCXGenerator()

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "test.docx")

            with pytest.raises(DOCXGenerationException):
                gen.save(filepath)

    def test_from_structure(self):
        """Test building document from structure."""
        gen = DOCXGenerator()

        sections = [
            DocumentSection(
                title="Introduction",
                content="This is the introduction.",
                heading_level=1,
            ),
            DocumentSection(
                title="Body",
                content="This is the body.",
                heading_level=1,
            ),
        ]

        structure = DocumentStructure(
            title="Test Document",
            sections=sections,
        )

        gen.from_structure(structure)

        assert gen.doc is not None
        assert len(gen.doc.paragraphs) > 0

    def test_full_workflow(self):
        """Test complete document creation workflow."""
        gen = DOCXGenerator()
        gen.create_document("Test Report")

        gen.add_heading("Executive Summary", level=1)
        gen.add_paragraph("This is a summary.")

        gen.add_heading("Details", level=2)
        gen.add_bullet_list(["Point 1", "Point 2", "Point 3"])

        gen.add_page_break()

        gen.add_heading("Conclusion", level=1)
        gen.add_paragraph("Final thoughts.")

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "report.docx")
            saved_path = gen.save(filepath)

            assert os.path.exists(saved_path)
