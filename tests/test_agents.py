"""Tests for the agent components."""

from unittest.mock import Mock, MagicMock, patch
import pytest

from agents.planner import PlannerAgent
from agents.writer import WriterAgent
from agents.reviewer import ReviewerAgent
from models import ExecutionPlan, Task, DocumentSection
from exceptions import (
    PlannerException,
    WriterException,
    ReviewerException,
)


class TestPlannerAgent:
    """Test cases for PlannerAgent."""

    def test_plan_success(self):
        """Test successful planning."""
        mock_client = Mock()
        mock_client.structured_generate.return_value = {
            "parsed_response": {
                "document_type": "Technical Report",
                "assumptions": {"audience": "Technical"},
                "tasks": [
                    {
                        "id": 1,
                        "description": "Research topic",
                        "dependencies": [],
                    },
                ],
                "outline": ["Introduction", "Methodology"],
            },
        }

        planner = PlannerAgent(mock_client)
        plan = planner.plan("Create a technical report about Python")

        assert plan.document_type == "Technical Report"
        assert len(plan.tasks) > 0
        assert len(plan.outline) > 0

    def test_plan_failure(self):
        """Test planning failure."""
        mock_client = Mock()
        mock_client.structured_generate.side_effect = Exception("API error")

        planner = PlannerAgent(mock_client)

        with pytest.raises(PlannerException):
            planner.plan("Create a document")


class TestWriterAgent:
    """Test cases for WriterAgent."""

    def test_write_section_success(self):
        """Test successful section writing."""
        mock_client = Mock()
        mock_client.structured_generate.return_value = {
            "parsed_response": {
                "title": "Introduction",
                "content": "This is the introduction section.",
                "heading_level": 1,
            },
        }

        writer = WriterAgent(mock_client)

        plan = ExecutionPlan(
            document_type="Report",
            assumptions={},
            tasks=[],
            outline=["Introduction", "Body"],
        )

        section = writer.write_section("Test request", plan, 0)

        assert section.title == "Introduction"
        assert section.content == "This is the introduction section."

    def test_write_section_out_of_bounds(self):
        """Test writing section with invalid index."""
        mock_client = Mock()
        writer = WriterAgent(mock_client)

        plan = ExecutionPlan(
            document_type="Report",
            assumptions={},
            tasks=[],
            outline=["Introduction"],
        )

        with pytest.raises(WriterException):
            writer.write_section("Test request", plan, 5)

    def test_write_all_sections(self):
        """Test writing all sections."""
        mock_client = Mock()
        mock_client.structured_generate.return_value = {
            "parsed_response": {
                "title": "Section",
                "content": "Content",
                "heading_level": 1,
            },
        }

        writer = WriterAgent(mock_client)

        plan = ExecutionPlan(
            document_type="Report",
            assumptions={},
            tasks=[],
            outline=["Introduction", "Body", "Conclusion"],
        )

        sections = writer.write_all_sections("Test request", plan)

        assert len(sections) == 3

    def test_write_section_failure(self):
        """Test section writing failure."""
        mock_client = Mock()
        mock_client.structured_generate.side_effect = Exception("API error")

        writer = WriterAgent(mock_client)

        plan = ExecutionPlan(
            document_type="Report",
            assumptions={},
            tasks=[],
            outline=["Introduction"],
        )

        with pytest.raises(WriterException):
            writer.write_section("Test request", plan, 0)


class TestReviewerAgent:
    """Test cases for ReviewerAgent."""

    def test_review_document_success(self):
        """Test successful document review."""
        mock_client = Mock()
        mock_client.structured_generate.return_value = {
            "parsed_response": {
                "has_issues": False,
                "grammar_issues": [],
                "consistency_issues": [],
                "structure_issues": [],
                "tone_issues": [],
                "corrections": "Document looks good",
            },
        }

        reviewer = ReviewerAgent(mock_client)

        sections = [
            DocumentSection(
                title="Introduction",
                content="Introduction content",
                heading_level=1,
            ),
        ]

        feedback = reviewer.review_document("Test Report", sections)

        assert feedback.has_issues is False

    def test_review_document_with_issues(self):
        """Test document review with issues found."""
        mock_client = Mock()
        mock_client.structured_generate.return_value = {
            "parsed_response": {
                "has_issues": True,
                "grammar_issues": ["Spelling error in section 1"],
                "consistency_issues": ["Inconsistent terminology"],
                "structure_issues": [],
                "tone_issues": [],
                "corrections": "Fix spelling and terminology",
            },
        }

        reviewer = ReviewerAgent(mock_client)

        sections = [
            DocumentSection(
                title="Introduction",
                content="Introducton content",
                heading_level=1,
            ),
        ]

        feedback = reviewer.review_document("Test Report", sections)

        assert feedback.has_issues is True
        assert len(feedback.grammar_issues) > 0

    def test_score_document_success(self):
        """Test successful document scoring."""
        mock_client = Mock()
        mock_client.structured_generate.return_value = {
            "parsed_response": {
                "relevance": 5,
                "completeness": 4,
                "coherence": 4,
                "structure": 5,
                "overall": 4,
            },
        }

        reviewer = ReviewerAgent(mock_client)

        sections = [
            DocumentSection(
                title="Introduction",
                content="Content",
                heading_level=1,
            ),
        ]

        score = reviewer.score_document("Test Report", sections)

        assert score.relevance == 5
        assert score.overall == 4

    def test_review_failure(self):
        """Test review failure."""
        mock_client = Mock()
        mock_client.structured_generate.side_effect = Exception("API error")

        reviewer = ReviewerAgent(mock_client)

        sections = [
            DocumentSection(
                title="Introduction",
                content="Content",
                heading_level=1,
            ),
        ]

        with pytest.raises(ReviewerException):
            reviewer.review_document("Test Report", sections)

    def test_score_failure(self):
        """Test scoring failure."""
        mock_client = Mock()
        mock_client.structured_generate.side_effect = Exception("API error")

        reviewer = ReviewerAgent(mock_client)

        sections = [
            DocumentSection(
                title="Introduction",
                content="Content",
                heading_level=1,
            ),
        ]

        with pytest.raises(ReviewerException):
            reviewer.score_document("Test Report", sections)
