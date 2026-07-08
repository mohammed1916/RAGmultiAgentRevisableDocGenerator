"""Tests for Iterative Refinement engineering improvement."""

from unittest.mock import Mock, patch
import pytest

from orchestrator import Orchestrator
from models import (
    DocumentRequest,
    DocumentSection,
    ExecutionPlan,
    Task,
    SectionFeedback,
    ReviewFeedback,
)


class TestIterativeRefinement:
    """Test the iterative refinement feature."""

    @patch("orchestrator.OllamaClient")
    def test_refinement_identifies_section_issues(self, mock_ollama_class):
        """Test that refinement correctly identifies which sections have issues."""
        mock_client = Mock()
        mock_ollama_class.return_value = mock_client

        # Setup orchestrator
        orchestrator = Orchestrator()
        orchestrator.ollama_client = mock_client

        # Create test sections
        sections = [
            DocumentSection(
                title="Introduction",
                content="We'll use API Endpoint for requests.",
                heading_level=1,
            ),
            DocumentSection(
                title="Architecture",
                content="The Service Mesh handles all communication.",
                heading_level=1,
            ),
        ]

        plan = ExecutionPlan(
            document_type="Technical Design",
            assumptions={},
            tasks=[],
            outline=["Introduction", "Architecture"],
        )

        # Create feedback indicating inconsistency
        feedback = ReviewFeedback(
            has_issues=True,
            grammar_issues=[],
            consistency_issues=["Inconsistent service naming"],
            structure_issues=[],
            tone_issues=[],
            section_feedback=[
                SectionFeedback(
                    section_title="Architecture",
                    issues=["Inconsistent service naming"],
                    feedback="Section says 'Service Mesh' but Introduction uses 'API Endpoint'. "
                    "Clarify that Service Mesh is the unified entry point.",
                )
            ],
            corrections="Fix inconsistent terminology",
        )

        # Mock writer to return revised section
        mock_writer = Mock()
        revised_section = DocumentSection(
            title="Architecture",
            content="The Service Mesh (unified API Endpoint) handles all communication.",
            heading_level=1,
        )
        mock_writer.write_section.return_value = revised_section
        orchestrator.writer = mock_writer

        # Call refinement
        refined = orchestrator._refine_sections(
            "Create technical design",
            plan,
            sections,
            feedback,
        )

        # Verify
        assert len(refined) == 2
        assert refined[1].title == "Architecture"
        assert "Service Mesh (unified API Endpoint)" in refined[1].content
        mock_writer.write_section.assert_called_once()

    @patch("orchestrator.OllamaClient")
    def test_refinement_with_multiple_issues(self, mock_ollama_class):
        """Test refinement when multiple sections have issues."""
        mock_ollama_class.return_value = Mock()
        orchestrator = Orchestrator()
        mock_writer = Mock()
        orchestrator.writer = mock_writer

        sections = [
            DocumentSection(title="Section A", content="Content A", heading_level=1),
            DocumentSection(title="Section B", content="Content B", heading_level=1),
            DocumentSection(title="Section C", content="Content C", heading_level=1),
        ]

        plan = ExecutionPlan(
            document_type="Report",
            assumptions={},
            tasks=[],
            outline=["Section A", "Section B", "Section C"],
        )

        feedback = ReviewFeedback(
            has_issues=True,
            section_feedback=[
                SectionFeedback(
                    section_title="Section A",
                    issues=["Grammar error"],
                    feedback="Fix: 'recieve' should be 'receive'",
                ),
                SectionFeedback(
                    section_title="Section C",
                    issues=["Missing detail"],
                    feedback="Expand the conclusion with specific recommendations",
                ),
            ],
            corrections="Fix grammar and add details",
        )

        # Mock revised sections
        revised_a = DocumentSection(title="Section A", content="Content A fixed", heading_level=1)
        revised_c = DocumentSection(
            title="Section C", content="Content C with recommendations", heading_level=1
        )

        mock_writer.write_section.side_effect = [revised_a, revised_c]

        # Call refinement
        refined = orchestrator._refine_sections(
            "Test",
            plan,
            sections,
            feedback,
        )

        # Verify
        assert refined[0].content == "Content A fixed"
        assert refined[1].content == "Content B"  # Unchanged
        assert refined[2].content == "Content C with recommendations"
        assert mock_writer.write_section.call_count == 2

    @patch("orchestrator.OllamaClient")
    def test_refinement_with_feedback_parameter(self, mock_ollama_class):
        """Test that revision_feedback parameter is passed to writer."""
        mock_client = Mock()
        mock_ollama_class.return_value = mock_client
        writer_agent = Mock()

        orchestrator = Orchestrator()
        orchestrator.ollama_client = mock_client
        orchestrator.writer = writer_agent

        sections = [
            DocumentSection(title="Budget", content="$50K budget", heading_level=1),
        ]

        plan = ExecutionPlan(
            document_type="Proposal",
            assumptions={},
            tasks=[],
            outline=["Budget"],
        )

        feedback = ReviewFeedback(
            has_issues=True,
            section_feedback=[
                SectionFeedback(
                    section_title="Budget",
                    issues=["Inconsistent cost figure"],
                    feedback="Update budget to $75K to match ROI Analysis section",
                )
            ],
            corrections="Fix budget amount",
        )

        revised = DocumentSection(title="Budget", content="$75K budget", heading_level=1)
        writer_agent.write_section.return_value = revised

        # Call refinement
        orchestrator._refine_sections("Create proposal", plan, sections, feedback)

        # Verify write_section was called with revision_feedback
        writer_agent.write_section.assert_called_once()
        call_args = writer_agent.write_section.call_args

        assert call_args.kwargs["revision_feedback"] is not None
        assert "Update budget to $75K" in call_args.kwargs["revision_feedback"]

    @patch("orchestrator.OllamaClient")
    def test_refinement_preserves_other_sections(self, mock_ollama_class):
        """Test that refinement only changes sections with feedback."""
        mock_ollama_class.return_value = Mock()
        orchestrator = Orchestrator()
        mock_writer = Mock()
        orchestrator.writer = mock_writer

        sections = [
            DocumentSection(title="Good Section", content="Excellent content", heading_level=1),
            DocumentSection(title="Bad Section", content="Poor content", heading_level=1),
            DocumentSection(
                title="Another Good", content="Also excellent", heading_level=1
            ),
        ]

        plan = ExecutionPlan(
            document_type="Report",
            assumptions={},
            tasks=[],
            outline=["Good Section", "Bad Section", "Another Good"],
        )

        # Only feedback for one section
        feedback = ReviewFeedback(
            has_issues=True,
            section_feedback=[
                SectionFeedback(
                    section_title="Bad Section",
                    issues=["Low quality"],
                    feedback="Improve the content quality",
                )
            ],
            corrections="Improve",
        )

        revised = DocumentSection(title="Bad Section", content="Improved content", heading_level=1)
        mock_writer.write_section.return_value = revised

        refined = orchestrator._refine_sections("Test", plan, sections, feedback)

        # Verify sections without feedback are unchanged
        assert refined[0].content == "Excellent content"
        assert refined[1].content == "Improved content"
        assert refined[2].content == "Also excellent"

    @patch("orchestrator.OllamaClient")
    def test_nonexistent_section_handling(self, mock_ollama_class):
        """Test that refinement handles feedback for non-existent sections gracefully."""
        mock_ollama_class.return_value = Mock()
        orchestrator = Orchestrator()
        orchestrator.writer = Mock()

        sections = [
            DocumentSection(title="Section A", content="Content A", heading_level=1),
        ]

        plan = ExecutionPlan(
            document_type="Report",
            assumptions={},
            tasks=[],
            outline=["Section A"],
        )

        # Feedback references a section that doesn't exist
        feedback = ReviewFeedback(
            has_issues=True,
            section_feedback=[
                SectionFeedback(
                    section_title="NonExistent Section",
                    issues=["Some issue"],
                    feedback="Fix this",
                )
            ],
            corrections="Fix",
        )

        refined = orchestrator._refine_sections("Test", plan, sections, feedback)

        # Should return unchanged sections
        assert len(refined) == 1
        assert refined[0].content == "Content A"
        orchestrator.writer.write_section.assert_not_called()


class TestIterativeRefinementIntegration:
    """Integration tests for refinement in the full pipeline."""

    @patch("tools.ollama_client.requests.get")
    @patch("tools.ollama_client.requests.post")
    def test_refinement_loop_improves_quality(self, mock_post, mock_get):
        """Test that refinement loop actually improves document quality."""
        mock_get.return_value.json.return_value = {"models": []}
        mock_get.return_value.status_code = 200

        # Mock responses for iteration 1
        planner_response = {
            "document_type": "Proposal",
            "assumptions": {},
            "tasks": [{"id": 1, "description": "Task", "dependencies": []}],
            "outline": ["Introduction", "Budget"],
        }

        writer_response_intro = {
            "title": "Introduction",
            "content": "We need to implement a new system.",
            "heading_level": 1,
        }

        writer_response_budget = {
            "title": "Budget",
            "content": "Estimated cost is $50K based on implementation details.",
            "heading_level": 1,
        }

        # First review finds inconsistency
        review_response_1 = {
            "has_issues": True,
            "grammar_issues": [],
            "consistency_issues": [],
            "structure_issues": [],
            "tone_issues": [],
            "section_feedback": [
                {
                    "section_title": "Budget",
                    "issues": ["Cost inconsistency"],
                    "feedback": "Introduction mentions new system but budget doesn't specify for what",
                }
            ],
            "corrections": "Clarify what the $50K budget is for",
        }

        # Mock refined budget response
        writer_response_budget_revised = {
            "title": "Budget",
            "content": "Estimated cost is $50K for implementing the new system as described above.",
            "heading_level": 1,
        }

        # Second review passes
        review_response_2 = {
            "has_issues": False,
            "grammar_issues": [],
            "consistency_issues": [],
            "structure_issues": [],
            "tone_issues": [],
            "section_feedback": [],
            "corrections": "Document is now consistent",
        }

        score_response = {
            "relevance": 5,
            "completeness": 4,
            "coherence": 5,
            "structure": 5,
            "overall": 4,
        }

        call_count = [0]

        def mock_post_side_effect(*args, **kwargs):
            call_count[0] += 1

            if call_count[0] == 1:  # Planner
                return Mock(json=lambda: {"response": str(planner_response)}, status_code=200)
            elif call_count[0] == 2:  # Writer - Introduction
                return Mock(
                    json=lambda: {"response": str(writer_response_intro)}, status_code=200
                )
            elif call_count[0] == 3:  # Writer - Budget
                return Mock(
                    json=lambda: {"response": str(writer_response_budget)}, status_code=200
                )
            elif call_count[0] == 4:  # Reviewer - Iteration 1
                return Mock(
                    json=lambda: {"response": str(review_response_1)}, status_code=200
                )
            elif call_count[0] == 5:  # Writer - Budget Revised
                return Mock(
                    json=lambda: {"response": str(writer_response_budget_revised)}, status_code=200
                )
            elif call_count[0] == 6:  # Reviewer - Iteration 2
                return Mock(
                    json=lambda: {"response": str(review_response_2)}, status_code=200
                )
            else:  # Scorer
                return Mock(json=lambda: {"response": str(score_response)}, status_code=200)

        mock_post.side_effect = mock_post_side_effect

        orchestrator = Orchestrator()
        request = DocumentRequest(
            request="Create a proposal for a new system"
        )

        with patch("config.config.document_output_dir", "/tmp/test_docs"):
            response = orchestrator.generate_document(request)

        # Verify refinement occurred
        assert response.success is True
        assert response.metrics.review_iterations == 1
        # Final budget content should have the revised version
        assert "implementing the new system" in " ".join([s.content for s in response.execution_plan.outline])
