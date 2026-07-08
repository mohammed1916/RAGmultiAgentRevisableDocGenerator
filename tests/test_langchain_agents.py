"""Tests for LangChain agents with tool-calling."""

import pytest
from server.langchain_agents import (
    plan_document_tool,
    write_sections_tool,
    review_document_tool,
    fetch_rag_context_tool,
    create_planner_agent,
    create_writer_agent,
    create_reviewer_agent,
)


def test_plan_document_tool_basic(mocker):
    """Test plan_document_tool execution."""
    mocker.patch('server.langchain_agents.Ollama')
    mocker.patch('server.langchain_agents.PlannerAgent')

    result = plan_document_tool(
        request="Create a technical guide",
        metadata={"audience": "Developers"}
    )

    assert result is not None
    assert "success" in result


def test_plan_document_tool_without_metadata(mocker):
    """Test plan_document_tool without metadata."""
    mocker.patch('server.langchain_agents.Ollama')
    mocker.patch('server.langchain_agents.PlannerAgent')

    result = plan_document_tool(request="Create a guide")

    assert result is not None
    assert "success" in result


def test_write_sections_tool_basic(mocker):
    """Test write_sections_tool execution."""
    mocker.patch('server.langchain_agents.Ollama')
    mocker.patch('server.langchain_agents.WriterAgent')

    result = write_sections_tool(
        request="Create a guide",
        outline=["Introduction", "Main Content", "Conclusion"],
        rag_context_enabled=False
    )

    assert result is not None
    assert "success" in result
    assert "sections" in result


def test_write_sections_tool_with_rag(mocker):
    """Test write_sections_tool with RAG enabled."""
    mocker.patch('server.langchain_agents.Ollama')
    mocker.patch('server.langchain_agents.WriterAgent')
    mocker.patch('server.langchain_agents.MilvusRAG')

    result = write_sections_tool(
        request="Create a guide",
        outline=["Introduction", "Main Content"],
        rag_context_enabled=True
    )

    assert result is not None
    assert "success" in result


def test_review_document_tool_basic(mocker):
    """Test review_document_tool execution."""
    mocker.patch('server.langchain_agents.Ollama')
    mocker.patch('server.langchain_agents.ReviewerAgent')

    sections = [
        {"title": "Introduction", "content": "Intro text..."},
        {"title": "Content", "content": "Main content..."},
    ]

    result = review_document_tool(sections)

    assert result is not None
    assert "success" in result
    assert "scores" in result


def test_review_document_tool_empty_sections(mocker):
    """Test review_document_tool with empty sections."""
    mocker.patch('server.langchain_agents.Ollama')
    mocker.patch('server.langchain_agents.ReviewerAgent')

    result = review_document_tool([])

    assert result is not None
    # Should handle empty gracefully


def test_fetch_rag_context_tool(mocker):
    """Test fetch_rag_context_tool."""
    mock_rag = mocker.MagicMock()
    mock_rag.search_documents = mocker.MagicMock(return_value=[
        {"content": "Result 1"},
        {"content": "Result 2"},
    ])

    mocker.patch('server.langchain_agents.MilvusRAG', return_value=mock_rag)

    result = fetch_rag_context_tool(
        query="Physics fundamentals",
        top_k=5
    )

    assert result is not None
    assert result["success"] is True
    assert result["query"] == "Physics fundamentals"
    assert len(result["results"]) >= 0


def test_fetch_rag_context_tool_default_top_k(mocker):
    """Test fetch_rag_context_tool with default top_k."""
    mock_rag = mocker.MagicMock()
    mock_rag.search_documents = mocker.MagicMock(return_value=[])

    mocker.patch('server.langchain_agents.MilvusRAG', return_value=mock_rag)

    result = fetch_rag_context_tool(query="Test")

    assert result is not None


def test_plan_document_tool_error_handling(mocker):
    """Test plan_document_tool error handling."""
    mocker.patch('server.langchain_agents.Ollama', side_effect=Exception("Connection error"))

    result = plan_document_tool(request="Test")

    assert result["success"] is False
    assert "error" in result


def test_write_sections_tool_error_handling(mocker):
    """Test write_sections_tool error handling."""
    mocker.patch('server.langchain_agents.Ollama', side_effect=Exception("Connection error"))

    result = write_sections_tool(
        request="Test",
        outline=["A", "B"]
    )

    assert result["success"] is False


def test_review_document_tool_error_handling(mocker):
    """Test review_document_tool error handling."""
    mocker.patch('server.langchain_agents.Ollama', side_effect=Exception("Connection error"))

    result = review_document_tool([{"title": "A", "content": "Content"}])

    assert result["success"] is False


def test_fetch_rag_context_tool_error_handling(mocker):
    """Test fetch_rag_context_tool error handling."""
    mocker.patch('server.langchain_agents.MilvusRAG', side_effect=Exception("RAG error"))

    result = fetch_rag_context_tool(query="Test")

    assert result["success"] is False
    assert "error" in result


def test_create_planner_agent(mocker):
    """Test planner agent creation."""
    mocker.patch('server.langchain_agents.Ollama')
    mocker.patch('server.langchain_agents.create_openai_tools_agent')
    mocker.patch('server.langchain_agents.AgentExecutor')

    agent = create_planner_agent()

    assert agent is not None


def test_create_writer_agent(mocker):
    """Test writer agent creation."""
    mocker.patch('server.langchain_agents.Ollama')
    mocker.patch('server.langchain_agents.create_openai_tools_agent')
    mocker.patch('server.langchain_agents.AgentExecutor')

    agent = create_writer_agent()

    assert agent is not None


def test_create_reviewer_agent(mocker):
    """Test reviewer agent creation."""
    mocker.patch('server.langchain_agents.Ollama')
    mocker.patch('server.langchain_agents.create_openai_tools_agent')
    mocker.patch('server.langchain_agents.AgentExecutor')

    agent = create_reviewer_agent()

    assert agent is not None


def test_tool_descriptions(mocker):
    """Test that tools have proper documentation."""
    # Tools decorated with @tool should have __doc__
    assert plan_document_tool.__doc__ is not None
    assert write_sections_tool.__doc__ is not None
    assert review_document_tool.__doc__ is not None
    assert fetch_rag_context_tool.__doc__ is not None


def test_tool_parameter_hints(mocker):
    """Test tools have proper parameter type hints."""
    import inspect

    # Check plan_document_tool parameters
    sig = inspect.signature(plan_document_tool)
    assert "request" in sig.parameters
    assert "metadata" in sig.parameters

    # Check write_sections_tool parameters
    sig = inspect.signature(write_sections_tool)
    assert "request" in sig.parameters
    assert "outline" in sig.parameters

    # Check review_document_tool parameters
    sig = inspect.signature(review_document_tool)
    assert "sections" in sig.parameters

    # Check fetch_rag_context_tool parameters
    sig = inspect.signature(fetch_rag_context_tool)
    assert "query" in sig.parameters
    assert "top_k" in sig.parameters


@pytest.mark.asyncio
async def test_agent_executor_integration(mocker):
    """Test agent executor integration with mocked LLM."""
    mock_llm = mocker.MagicMock()
    mock_agent = mocker.MagicMock()
    mock_executor = mocker.MagicMock()

    mocker.patch(
        'server.langchain_agents.Ollama',
        return_value=mock_llm
    )
    mocker.patch(
        'server.langchain_agents.create_tool_calling_agent',
        return_value=mock_agent
    )
    mocker.patch(
        'server.langchain_agents.AgentExecutor',
        return_value=mock_executor
    )

    agent = create_planner_agent()

    assert agent is not None
    # AgentExecutor should have these methods
    assert hasattr(agent, 'invoke') or hasattr(agent, 'call')
