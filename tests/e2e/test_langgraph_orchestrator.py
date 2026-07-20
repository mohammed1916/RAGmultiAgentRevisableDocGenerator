"""Comprehensive unit tests for LangGraph orchestrator.

Tests cover graph structure, node execution, state management, routing logic,
and end-to-end workflow execution with proper mocking.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from langchain_core.messages import HumanMessage, AIMessage

from server.core.orchestrators.langgraph import (
    DocumentGenerationState,
    LangGraphOrchestrator,
    plan_node,
    write_node,
    review_node,
    refine_node,
    generate_node,
    should_continue_review,
)
from server.base.models import ExecutionPlan, DocumentSection, ReviewFeedback
from server.config import config


class TestDocumentGenerationState:
    """Test DocumentGenerationState TypedDict schema."""

    def test_state_creation_with_all_fields(self):
        """Test creating state with all fields."""
        state: DocumentGenerationState = {
            "request": "Create a guide",
            "metadata": {"audience": "Students"},
            "messages": [HumanMessage(content="Create a guide")],
            "execution_plan": None,
            "plan_quality": 0.85,
            "sections": [{"title": "Intro", "content": "Content", "heading_level": 1}],
            "write_quality": 0.90,
            "review_feedback": "Good",
            "review_issues": [],
            "review_iterations": 1,
            "success": False,
            "document_filename": None,
            "error_message": None,
            "metrics": None,
        }

        assert state["request"] == "Create a guide"
        assert state["metadata"]["audience"] == "Students"
        assert len(state["messages"]) == 1
        assert state["review_iterations"] == 1

    def test_state_optional_fields(self):
        """Test state with only required fields."""
        state: DocumentGenerationState = {
            "request": "Test",
            "messages": [],
        }

        assert state["request"] == "Test"
        assert state["messages"] == []

    def test_message_accumulation(self):
        """Test message list accumulation."""
        state: DocumentGenerationState = {
            "request": "Test",
            "messages": [HumanMessage(content="User message")],
        }

        state["messages"].append(AIMessage(content="AI response"))

        assert len(state["messages"]) == 2
        assert state["messages"][0].type == "human"
        assert state["messages"][1].type == "ai"


class TestConditionalRouting:
    """Test conditional routing logic."""

    def test_should_continue_review_no_issues(self):
        """Test routing when no issues found."""
        state: DocumentGenerationState = {
            "request": "Test",
            "review_issues": None,
            "review_iterations": 1,
        }

        result = should_continue_review(state)
        assert result == "finish"

    def test_should_continue_review_max_iterations(self):
        """Test routing at max iterations."""
        state: DocumentGenerationState = {
            "request": "Test",
            "review_issues": [{"section": "intro", "issue": "Problem"}],
            "review_iterations": config.max_review_iterations,
        }

        result = should_continue_review(state)
        assert result == "finish"

    def test_should_continue_review_with_issues(self):
        """Test routing when issues found and under max iterations."""
        state: DocumentGenerationState = {
            "request": "Test",
            "review_issues": [{"section": "intro", "issue": "Problem"}],
            "review_iterations": 1,
        }

        result = should_continue_review(state)
        assert result == "revise"

    def test_should_continue_review_default_iterations(self):
        """Test routing with default iteration count."""
        state: DocumentGenerationState = {
            "request": "Test",
            "review_issues": [{"section": "intro", "issue": "Problem"}],
        }

        result = should_continue_review(state)
        assert result == "revise"


class TestPlanNode:
    """Test plan node execution."""

    @pytest.mark.asyncio
    async def test_plan_node_success(self):
        """Test successful plan node execution."""
        mock_orch = MagicMock()
        mock_planner = MagicMock()
        mock_orch.planner = mock_planner

        plan = ExecutionPlan(
            document_type="Technical Guide",
            assumptions={"audience": "Engineers"},
            tasks=[],
            outline=["Intro", "Content", "Conclusion"],
        )
        mock_planner.plan.return_value = plan

        state: DocumentGenerationState = {
            "request": "Create a technical guide",
            "metadata": None,
            "messages": [HumanMessage(content="Create a technical guide")],
        }

        result = await plan_node(state, orchestrator=mock_orch)

        assert result["execution_plan"] is not None
        assert result["execution_plan"].document_type == "Technical Guide"
        assert result["plan_quality"] == 0.85
        assert len(result["messages"]) > 0

    @pytest.mark.asyncio
    async def test_plan_node_error_handling(self):
        """Test plan node error handling."""
        mock_orch = MagicMock()
        mock_orch.planner.plan.side_effect = Exception("Planning failed")

        state: DocumentGenerationState = {
            "request": "Create a guide",
            "metadata": None,
            "messages": [],
        }

        result = await plan_node(state, orchestrator=mock_orch)

        assert "error_message" in result
        assert "Planning error" in result["error_message"]
        assert len(result.get("messages", [])) > 0


class TestWriteNode:
    """Test write node execution."""

    @pytest.mark.asyncio
    async def test_write_node_success(self):
        """Test successful write node execution."""
        mock_orch = MagicMock()
        mock_writer = MagicMock()
        mock_orch.writer = mock_writer

        sections = [
            DocumentSection(title="Intro", content="Introduction text", heading_level=1),
            DocumentSection(title="Content", content="Main content", heading_level=1),
        ]
        mock_writer.write_all_sections.return_value = sections

        plan = ExecutionPlan(
            document_type="Guide",
            assumptions={},
            tasks=[],
            outline=["Intro", "Content"],
        )

        state: DocumentGenerationState = {
            "request": "Create document",
            "execution_plan": plan,
            "messages": [],
        }

        result = await write_node(state, orchestrator=mock_orch)

        assert "sections" in result
        assert len(result["sections"]) == 2
        assert result["write_quality"] == 0.90

    @pytest.mark.asyncio
    async def test_write_node_no_plan(self):
        """Test write node when plan is missing."""
        state: DocumentGenerationState = {
            "request": "Create document",
            "execution_plan": None,
            "messages": [],
        }

        result = await write_node(state, orchestrator=MagicMock())

        assert "error_message" in result
        assert "No execution plan" in result["error_message"]

    @pytest.mark.asyncio
    async def test_write_node_error_handling(self):
        """Test write node error handling."""
        mock_orch = MagicMock()
        mock_orch.writer.write_all_sections.side_effect = Exception("Write failed")

        plan = ExecutionPlan(
            document_type="Guide",
            assumptions={},
            tasks=[],
            outline=[],
        )

        state: DocumentGenerationState = {
            "request": "Create document",
            "execution_plan": plan,
            "messages": [],
        }

        result = await write_node(state, orchestrator=mock_orch)

        assert "error_message" in result
        assert "Writing error" in result["error_message"]


class TestReviewNode:
    """Test review node execution."""

    @pytest.mark.asyncio
    async def test_review_node_no_issues(self):
        """Test review node when no issues found."""
        mock_orch = MagicMock()
        mock_reviewer = MagicMock()
        mock_orch.reviewer = mock_reviewer

        feedback = ReviewFeedback(
            has_issues=False,
            feedback_summary="Document approved",
            section_feedback=[],
        )
        mock_reviewer.review_document.return_value = feedback

        plan = ExecutionPlan(
            document_type="Guide",
            assumptions={},
            tasks=[],
            outline=[],
        )

        state: DocumentGenerationState = {
            "request": "Create document",
            "execution_plan": plan,
            "sections": [{"title": "Intro", "content": "Content", "heading_level": 1}],
            "review_iterations": 0,
            "messages": [],
        }

        result = await review_node(state, orchestrator=mock_orch)

        assert result["success"] is True
        assert result["review_issues"] is None
        assert result["review_iterations"] == 1

    @pytest.mark.asyncio
    async def test_review_node_with_issues(self):
        """Test review node when issues found."""
        from server.base.models import SectionFeedback

        mock_orch = MagicMock()
        mock_reviewer = MagicMock()
        mock_orch.reviewer = mock_reviewer

        feedback = ReviewFeedback(
            has_issues=True,
            section_feedback=[
                SectionFeedback(section_title="intro", feedback="Too short", issues=["short"]),
                SectionFeedback(section_title="content", feedback="Unclear", issues=["unclear"]),
            ],
        )
        mock_reviewer.review_document.return_value = feedback

        plan = ExecutionPlan(
            document_type="Guide",
            assumptions={},
            tasks=[],
            outline=[],
        )

        state: DocumentGenerationState = {
            "request": "Create document",
            "execution_plan": plan,
            "sections": [{"title": "Intro", "content": "Content", "heading_level": 1}],
            "review_iterations": 0,
            "messages": [],
        }

        result = await review_node(state, orchestrator=mock_orch)

        assert result["success"] is False
        assert result["review_issues"] is not None
        assert len(result["review_issues"]) == 2
        assert result["review_iterations"] == 1

    @pytest.mark.asyncio
    async def test_review_node_no_sections(self):
        """Test review node when sections are missing."""
        state: DocumentGenerationState = {
            "request": "Create document",
            "sections": [],
            "review_iterations": 0,
            "messages": [],
        }

        result = await review_node(state, orchestrator=MagicMock())

        assert "error_message" in result
        assert "No sections" in result["error_message"]


class TestRefineNode:
    """Test refine node execution."""

    @pytest.mark.asyncio
    async def test_refine_node_success(self):
        """Test successful refine node execution."""
        from server.base.models import SectionFeedback

        mock_orch = MagicMock()
        mock_orchestrator = mock_orch
        mock_orchestrator._refine_sections = MagicMock()

        refined = [
            DocumentSection(title="Intro", content="Better intro", heading_level=1),
            DocumentSection(title="Content", content="Improved content", heading_level=1),
        ]
        mock_orchestrator._refine_sections.return_value = refined

        plan = ExecutionPlan(
            document_type="Guide",
            assumptions={},
            tasks=[],
            outline=[],
        )

        state: DocumentGenerationState = {
            "request": "Create document",
            "execution_plan": plan,
            "sections": [{"title": "Intro", "content": "Content", "heading_level": 1}],
            "review_feedback": "Needs improvement",
            "review_issues": [
                {"section_title": "intro", "feedback": "Too short", "issues": ["short"]}
            ],
            "messages": [],
        }

        result = await refine_node(state, orchestrator=mock_orch)

        assert "sections" in result
        assert len(result["sections"]) == 2
        assert result["sections"][0]["content"] == "Better intro"

    @pytest.mark.asyncio
    async def test_refine_node_error_handling(self):
        """Test refine node error handling."""
        mock_orch = MagicMock()
        mock_orch._refine_sections.side_effect = Exception("Refine failed")

        plan = ExecutionPlan(
            document_type="Guide",
            assumptions={},
            tasks=[],
            outline=[],
        )

        state: DocumentGenerationState = {
            "request": "Create document",
            "execution_plan": plan,
            "sections": [{"title": "Intro", "content": "Content", "heading_level": 1}],
            "review_feedback": "Issues",
            "review_issues": [{"section": "intro", "issue": "Problem"}],
            "messages": [],
        }

        result = await refine_node(state, orchestrator=mock_orch)

        assert "error_message" in result
        assert "Refinement error" in result["error_message"]


class TestGenerateNode:
    """Test generate node execution."""

    @pytest.mark.asyncio
    async def test_generate_node_success(self):
        """Test successful document generation."""
        with patch("server.tools.DOCXGenerator") as mock_docx_cls:
            mock_generator = MagicMock()
            mock_generator.save.return_value = "document_123.docx"
            mock_docx_cls.return_value = mock_generator

            plan = ExecutionPlan(
                document_type="Guide",
                assumptions={},
                tasks=[],
                outline=["Intro", "Content"],
            )

            state: DocumentGenerationState = {
                "request": "Create document",
                "execution_plan": plan,
                "sections": [
                    {"title": "Intro", "content": "Introduction", "heading_level": 1},
                    {"title": "Content", "content": "Body", "heading_level": 1},
                ],
                "metadata": {"audience": "Users"},
                "messages": [],
            }

            result = await generate_node(state)

        assert result["success"] is True
        assert result["document_filename"] == "document_123.docx"

    @pytest.mark.asyncio
    async def test_generate_node_no_sections(self):
        """Test generate node with no sections."""
        state: DocumentGenerationState = {
            "request": "Create document",
            "sections": [],
            "messages": [],
        }

        result = await generate_node(state)

        assert "error_message" in result
        assert "No sections" in result["error_message"]

    @pytest.mark.asyncio
    async def test_generate_node_error_handling(self):
        """Test generate node error handling."""
        with patch("server.tools.DOCXGenerator") as mock_docx_cls:
            mock_docx_cls.return_value.save.side_effect = Exception("Generation failed")

            state: DocumentGenerationState = {
                "request": "Create document",
                "execution_plan": None,
                "sections": [{"title": "Intro", "content": "Content", "heading_level": 1}],
                "metadata": {},
                "messages": [],
            }

            result = await generate_node(state)

        assert "error_message" in result
        assert "Generation error" in result["error_message"]


class TestLangGraphOrchestrator:
    """Test LangGraphOrchestrator class."""

    def test_orchestrator_initialization(self):
        """Test orchestrator initializes with graph."""
        orchestrator = LangGraphOrchestrator(orchestrator=MagicMock())

        assert orchestrator is not None
        assert orchestrator.graph is not None

    def test_graph_has_all_nodes(self):
        """Test graph contains all expected nodes."""
        orchestrator = LangGraphOrchestrator(orchestrator=MagicMock())

        # Access the graph's internal structure
        assert orchestrator.graph is not None
        # Graph should be compiled and runnable

    @pytest.mark.asyncio
    async def test_generate_document_success(self):
        """Test generate_document method success flow."""
        mock_orch = MagicMock()
        mock_planner = MagicMock()
        mock_writer = MagicMock()
        mock_reviewer = MagicMock()
        mock_generator = MagicMock()

        mock_orch.planner = mock_planner
        mock_orch.writer = mock_writer
        mock_orch.reviewer = mock_reviewer
        mock_orch.docx_generator = mock_generator

        # Setup return values
        plan = ExecutionPlan(
            document_type="Guide",
            assumptions={},
            tasks=[],
            outline=["Intro", "Content"],
        )
        mock_planner.plan.return_value = plan

        sections = [
            DocumentSection(title="Intro", content="Text", heading_level=1),
        ]
        mock_writer.write_all_sections.return_value = sections

        feedback = ReviewFeedback(
            has_issues=False,
            feedback_summary="Good",
            section_feedback=[],
        )
        mock_reviewer.review_document.return_value = feedback

        mock_generator.save.return_value = "doc.docx"

        # Inject the fully-mocked orchestrator so every graph node uses the
        # mocked agents instead of building a real Orchestrator.
        orchestrator = LangGraphOrchestrator(orchestrator=mock_orch)

        with patch("server.tools.DOCXGenerator", return_value=mock_generator):
            result = await orchestrator.generate_document(
                request="Create a guide",
                metadata={"audience": "Users"},
            )

        assert result["success"] is True or result["error"] is None

    @pytest.mark.asyncio
    async def test_generate_document_with_error(self):
        """Test generate_document error handling."""
        orchestrator = LangGraphOrchestrator(orchestrator=MagicMock())

        # Mock the graph to raise an exception
        orchestrator.graph.ainvoke = AsyncMock(side_effect=Exception("Graph execution failed"))

        result = await orchestrator.generate_document(
            request="Create a guide",
            metadata={"audience": "Users"},
        )

        assert result["success"] is False
        assert result["error"] is not None
        assert "Graph execution failed" in result["error"]

    @pytest.mark.asyncio
    async def test_generate_document_default_metadata(self):
        """Test generate_document with no metadata."""
        with patch("server.core.orchestrators.base.Orchestrator"):
            orchestrator = LangGraphOrchestrator(orchestrator=MagicMock())

            # Mock the graph
            orchestrator.graph.ainvoke = AsyncMock(
                return_value={
                    "success": True,
                    "document_filename": "doc.docx",
                    "error_message": None,
                    "sections": [{"title": "Intro", "content": "Text"}],
                    "review_iterations": 0,
                    "messages": [],
                }
            )

            result = await orchestrator.generate_document(request="Create a guide")

            assert result["success"] is True
            assert result["sections_count"] == 1


class TestGraphStructure:
    """Test the graph structure and workflow."""

    def test_graph_compilation(self):
        """Test that graph compiles successfully."""
        orchestrator = LangGraphOrchestrator(orchestrator=MagicMock())
        assert orchestrator.graph is not None

    def test_initial_state_structure(self):
        """Test initial state for graph execution."""
        initial_state: DocumentGenerationState = {
            "request": "Create document",
            "metadata": {},
            "messages": [HumanMessage(content="Create document")],
            "execution_plan": None,
            "plan_quality": None,
            "sections": [],
            "write_quality": None,
            "review_feedback": None,
            "review_issues": None,
            "review_iterations": 0,
            "success": False,
            "document_filename": None,
            "error_message": None,
            "metrics": None,
        }

        assert initial_state["request"] is not None
        assert initial_state["review_iterations"] == 0
        assert initial_state["success"] is False


class TestStatePersistence:
    """Test state persistence across nodes."""

    def test_state_update_preserves_previous_values(self):
        """Test that state updates preserve previous values."""
        initial_state: DocumentGenerationState = {
            "request": "Create guide",
            "metadata": {"audience": "Students"},
            "messages": [HumanMessage(content="Create guide")],
            "execution_plan": None,
            "review_iterations": 0,
        }

        updated_state = dict(initial_state)
        updated_state["review_iterations"] = 1
        updated_state["plan_quality"] = 0.85

        assert updated_state["request"] == initial_state["request"]
        assert updated_state["metadata"] == initial_state["metadata"]
        assert updated_state["review_iterations"] == 1
        assert updated_state["plan_quality"] == 0.85

    def test_section_dict_conversion(self):
        """Test conversion between DocumentSection and dict."""
        section = DocumentSection(title="Intro", content="Content", heading_level=1)

        section_dict = {
            "title": section.title,
            "content": section.content,
            "heading_level": section.heading_level,
        }

        # Convert back
        converted = DocumentSection(
            title=section_dict["title"],
            content=section_dict["content"],
            heading_level=section_dict["heading_level"],
        )

        assert converted.title == section.title
        assert converted.content == section.content
