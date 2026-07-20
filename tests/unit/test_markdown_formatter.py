"""Tests for markdown formatter in DOCX."""

import pytest
from pathlib import Path

from server.tools import MarkdownFormatter
from server.tools import DOCXGenerator


class TestMarkdownFormatter:
    """Test markdown formatting in documents."""

    def test_parse_bold_markdown(self):
        """Test parsing **bold** markdown."""
        text = "This is **bold** text"
        segments = MarkdownFormatter.simple_parse(text)

        assert len(segments) == 3
        assert segments[0] == ("This is ", {})
        assert segments[1] == ("bold", {"bold": True})
        assert segments[2] == (" text", {})

    def test_parse_italic_markdown(self):
        """Test parsing *italic* markdown."""
        text = "This is *italic* text"
        segments = MarkdownFormatter.simple_parse(text)

        assert len(segments) == 3
        assert segments[0] == ("This is ", {})
        assert segments[1] == ("italic", {"italic": True})
        assert segments[2] == (" text", {})

    def test_parse_bold_italic_markdown(self):
        """Test parsing ***bold+italic*** markdown."""
        text = "This is ***bold and italic*** text"
        segments = MarkdownFormatter.simple_parse(text)

        assert len(segments) == 3
        assert segments[0] == ("This is ", {})
        assert segments[1][0] == "bold and italic"
        assert segments[1][1] == {"bold": True, "italic": True}
        assert segments[2] == (" text", {})

    def test_parse_multiple_formats(self):
        """Test parsing text with multiple formatted sections."""
        text = "**Physics** (1.5 hours): Complete *organic reactions* ***now***"
        segments = MarkdownFormatter.simple_parse(text)

        # Should have segments for: Physics (bold), plain text, organic reactions (italic), now (bold+italic)
        formatted_count = sum(1 for _, fmt in segments if fmt)
        assert formatted_count == 3  # 3 formatted segments

    def test_parse_no_markdown(self):
        """Test parsing plain text with no markdown."""
        text = "Just plain text"
        segments = MarkdownFormatter.simple_parse(text)

        assert len(segments) == 1
        assert segments[0] == ("Just plain text", {})

    def test_docx_with_bold_bullet(self):
        """Test DOCX generation with bold text in bullets."""
        gen = DOCXGenerator()
        gen.create_document("Test Document")

        items = [
            "**Physics (1.5 hours):** Master kinematics",
            "*Chemistry (1.5 hours):* Complete mechanisms",
            "***Mathematics (2.5 hours):*** Focus on calculus",
        ]

        gen.add_bullet_list(items)

        # Save to output folder
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        filepath = output_dir / "test_markdown_bullets.docx"

        saved_path = gen.save(str(filepath))
        assert Path(saved_path).exists()

        # Verify file was created and has content
        assert Path(saved_path).stat().st_size > 0

    def test_docx_with_bold_paragraph(self):
        """Test DOCX generation with bold text in paragraphs."""
        gen = DOCXGenerator()
        gen.create_document("Test Document")

        text = "Today's plan: **Study Calculus**, *practice problems*, and ***review concepts***"
        gen.add_paragraph(text)

        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        filepath = output_dir / "test_markdown_paragraph.docx"

        saved_path = gen.save(str(filepath))
        assert Path(saved_path).exists()
        assert Path(saved_path).stat().st_size > 0

    def test_real_world_jee_content(self):
        """Test with real JEE preparation content."""
        gen = DOCXGenerator()
        gen.create_document("JEE Daily Study Plan - July 8, 2026")

        gen.add_heading("Morning Study Block", level=1)
        gen.add_paragraph(
            "Focus on **core concepts** with *3 hours* of dedicated study time and ***practice problems***."
        )

        gen.add_heading("Topics for Today", level=1)
        items = [
            "**Physics (1.5 hours):** Master kinematics and Newton's laws by solving 20 problems",
            "**Chemistry (1.5 hours):** Complete organic reaction mechanisms and 15 numerical problems",
            "**Mathematics (2.5 hours):** Focus on calculus fundamentals (*limits, derivatives*) through 30 practice problems",
            "**Core Activities (0.5 hours):** Dedicate 30 minutes to *revision* and 20 minutes to ***timed test***",
        ]

        gen.add_bullet_list(items)

        gen.add_heading("Progress Tracking", level=1)
        gen.add_paragraph(
            "You have **191 days** until exam. Current pace: ***on track***. "
            "No topics to *revise* today, focus on *learning*."
        )

        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        filepath = output_dir / "test_jee_markdown_content.docx"

        saved_path = gen.save(str(filepath))
        assert Path(saved_path).exists()
        assert Path(saved_path).stat().st_size > 0

        print(f"\nTest DOCX saved to: {saved_path}")
        print("DOCX file successfully created with markdown formatting:")
        print("- Bold text: **text**")
        print("- Italic text: *text*")
        print("- Bold+Italic text: ***text***")
