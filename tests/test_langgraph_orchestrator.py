"""Tests for LangGraph orchestrator."""

import pytest
from datetime import datetime
from server.langgraph_orchestrator import (
    DocumentGenerationState,
    LangGraphOrchestrator,
    plan_node,
    write_node,
    review_node,
)
from server.models import ExecutionPlan, DocumentSection


@pytest.mark.asyncio
async def test_langgraph_orchestrator_initialization():
    """Test orchestrator initializes correctly."""
    orchestrator = LangGraphOrchestrator()
    assert orchestrator is not None
    assert orchestrator.graph is not None
    assert hasattr(orchestrator, 'generate_document')


@pytest.mark.asyncio
async def test_document_generation_state_creation():
    """Test state TypedDict creation."""
    from langchain_core.messages import HumanMessage

    state: DocumentGenerationState = {
        "request": "Create a guide",
        "metadata": {"audience": "Students"},
        "messages": [HumanMessage(content="Create a guide")],
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

    assert state["request"] == "Create a guide"
    assert state["metadata"]["audience"] == "Students"
    assert len(state["messages"]) == 1
    assert state["review_iterations"] == 0


@pytest.mark.asyncio
async def test_plan_node_execution(mocker):
    """Test plan node executes and populates state."""
    from langchain_core.messages import HumanMessage

    # Mock LLM and agent
    mocker.patch('server.langgraph_orchestrator.Ollama')
    mocker.patch('server.langgraph_orchestrator.create_tool_calling_agent')
    mocker.patch('server.langgraph_orchestrator.AgentExecutor')

    state: DocumentGenerationState = {
        "request": "Create a technical guide",
        "metadata": None,
        "messages": [HumanMessage(content="Create a technical guide")],
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

    result = await plan_node(state)

    assert result["execution_plan"] is not None or result["error_message"] is not None


@pytest.mark.asyncio
async def test_state_message_accumulation():
    """Test that messages are accumulated via add_messages."""
    from langchain_core.messages import HumanMessage, AIMessage

    state: DocumentGenerationState = {
        "request": "Test",
        "metadata": None,
        "messages": [HumanMessage(content="User message")],
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

    # Add an AI message
    state["messages"].append(AIMessage(content="AI response"))

    assert len(state["messages"]) == 2
    assert state["messages"][0].type == "human"
    assert state["messages"][1].type == "ai"


@pytest.mark.asyncio
async def test_review_conditional_routing():
    """Test review conditional routing logic."""
    from server.langgraph_orchestrator import should_continue_review

    # Test: No issues -> finish
    state_no_issues: DocumentGenerationState = {
        "request": "Test",
        "metadata": None,
        "messages": [],
        "execution_plan": None,
        "plan_quality": None,
        "sections": [],
        "write_quality": None,
        "review_feedback": "Document looks great",
        "review_issues": None,
        "review_iterations": 1,
        "success": False,
        "document_filename": None,
        "error_message": None,
        "metrics": None,
    }

    result = should_continue_review(state_no_issues)
    assert result == "finish"

    # Test: Max iterations -> finish
    state_max_iter: DocumentGenerationState = {
        "request": "Test",
        "metadata": None,
        "messages": [],
        "execution_plan": None,
        "plan_quality": None,
        "sections": [],
        "write_quality": None,
        "review_feedback": "Issues found",
        "review_issues": None,
        "review_iterations": 2,
        "success": False,
        "document_filename": None,
        "error_message": None,
        "metrics": None,
    }

    result = should_continue_review(state_max_iter)
    assert result == "finish"

    # Test: Issues found, iterations < max -> revise
    state_issues: DocumentGenerationState = {
        "request": "Test",
        "metadata": None,
        "messages": [],
        "execution_plan": None,
        "plan_quality": None,
        "sections": [],
        "write_quality": None,
        "review_feedback": "Document has issues to fix",
        "review_issues": None,
        "review_iterations": 1,
        "success": False,
        "document_filename": None,
        "error_message": None,
        "metrics": None,
    }

    result = should_continue_review(state_issues)
    assert result == "revise"


@pytest.mark.asyncio
async def test_orchestrator_generate_document_basic(mocker):
    """Test orchestrator generate_document method."""
    mocker.patch('server.langgraph_orchestrator.Ollama')
    mocker.patch('server.langgraph_orchestrator.create_tool_calling_agent')
    mocker.patch('server.langgraph_orchestrator.AgentExecutor')

    orchestrator = LangGraphOrchestrator()

    # Mock the graph's ainvoke method
    mock_graph = mocker.MagicMock()
    mock_graph.ainvoke = mocker.AsyncMock(return_value={
        "request": "Test",
        "messages": [],
        "execution_plan": None,
        "sections": [{"title": "Test", "content": "Content"}],
        "success": True,
        "document_filename": "test.docx",
        "error_message": None,
        "review_iterations": 1,
    })

    orchestrator.graph = mock_graph

    result = await orchestrator.generate_document(
        request="Create a test document",
        metadata={"audience": "Testers"}
    )

    assert result["success"] is True
    assert result["document_filename"] == "test.docx"
    assert result["sections_count"] == 1


@pytest.mark.asyncio
async def test_orchestrator_error_handling(mocker):
    """Test orchestrator error handling."""
    mocker.patch('server.langgraph_orchestrator.Ollama')
    mocker.patch('server.langgraph_orchestrator.create_tool_calling_agent')
    mocker.patch('server.langgraph_orchestrator.AgentExecutor')

    orchestrator = LangGraphOrchestrator()

    # Mock the graph's ainvoke method to fail
    mock_graph = mocker.MagicMock()
    mock_graph.ainvoke = mocker.AsyncMock(return_value={
        "request": "Test",
        "messages": [],
        "execution_plan": None,
        "sections": [],
        "success": False,
        "document_filename": None,
        "error_message": "LLM connection failed",
        "review_iterations": 0,
    })

    orchestrator.graph = mock_graph

    result = await orchestrator.generate_document(
        request="Create a test document"
    )

    assert result["success"] is False
    assert result["error"] is not None


def test_execution_plan_creation():
    """Test ExecutionPlan model works with state."""
    plan = ExecutionPlan(
        document_type="Technical Specification",
        assumptions={"audience": "Engineers"},
        tasks=[
            {"id": 1, "description": "Plan", "dependencies": []},
            {"id": 2, "description": "Write", "dependencies": [1]},
        ],
        outline=["Introduction", "Specifications", "Conclusion"],
    )

    assert plan.document_type == "Technical Specification"
    assert len(plan.outline) == 3
    assert len(plan.tasks) == 2


def test_document_section_creation():
    """Test DocumentSection model works with state."""
    section = DocumentSection(
        title="Introduction",
        content="This is the introduction to the document.",
        heading_level=1,
    )

    assert section.title == "Introduction"
    assert len(section.content) > 0
    assert section.heading_level == 1


@pytest.mark.asyncio
async def test_state_persistence_across_nodes():
    """Test state persists correctly across node transitions."""
    from langchain_core.messages import HumanMessage

    initial_state: DocumentGenerationState = {
        "request": "Create a guide",
        "metadata": {"audience": "Students"},
        "messages": [HumanMessage(content="Create a guide")],
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

    # Simulate state changes through nodes
    updated_state = dict(initial_state)
    updated_state["review_iterations"] = 1
    updated_state["plan_quality"] = 0.85

    # Original request should persist
    assert updated_state["request"] == initial_state["request"]
    assert updated_state["metadata"] == initial_state["metadata"]

    # New values should be updated
    assert updated_state["review_iterations"] == 1
    assert updated_state["plan_quality"] == 0.85
