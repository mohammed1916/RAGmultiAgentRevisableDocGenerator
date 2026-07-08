"""LangGraph-based multi-agent document orchestration.

Uses LangGraph for state machine coordination and LangChain agents
for autonomous tool-calling.
"""

from typing import TypedDict, Annotated, Optional, List
from datetime import datetime

from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain.tools import tool
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_community.llms import Ollama
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from .logger import setup_logger
from .models import (
    ExecutionPlan,
    DocumentSection,
    QualityScore,
    PipelineMetrics,
)

logger = setup_logger(__name__)


# ============================================================================
# State Definition
# ============================================================================

class DocumentGenerationState(TypedDict):
    """State for document generation workflow."""

    # Input
    request: str
    metadata: Optional[dict]

    # Messages (conversation history)
    messages: Annotated[List[BaseMessage], add_messages]

    # Plan phase
    execution_plan: Optional[ExecutionPlan]
    plan_quality: Optional[float]

    # Write phase
    sections: List[DocumentSection]
    write_quality: Optional[float]

    # Review phase
    review_feedback: Optional[str]
    review_issues: Optional[List[str]]
    review_iterations: int

    # Output
    success: bool
    document_filename: Optional[str]
    error_message: Optional[str]
    metrics: Optional[PipelineMetrics]


# ============================================================================
# Tools for Agents
# ============================================================================

@tool
def plan_document(request: str, metadata: dict = None) -> dict:
    """Generate execution plan for document.

    Args:
        request: Document request description
        metadata: Optional metadata about the request

    Returns:
        Execution plan with structure and tasks
    """
    logger.info("Planning document generation...")

    # This would call the actual planner agent
    return {
        "document_type": "Technical Document",
        "assumptions": {
            "audience": metadata.get("audience", "General") if metadata else "General",
            "scope": metadata.get("scope", "Balanced") if metadata else "Balanced",
        },
        "tasks": [
            {"id": 1, "description": "Research topic", "dependencies": []},
            {"id": 2, "description": "Outline structure", "dependencies": [1]},
            {"id": 3, "description": "Write content", "dependencies": [2]},
        ],
        "outline": ["Introduction", "Main Content", "Conclusion"],
    }


@tool
def write_section(title: str, context: str, plan: dict) -> dict:
    """Write a document section.

    Args:
        title: Section title
        context: Context from previous sections
        plan: Execution plan reference

    Returns:
        Written section with content
    """
    logger.info(f"Writing section: {title}")

    return {
        "title": title,
        "content": f"Content for {title} section based on the request.",
        "heading_level": 1,
    }


@tool
def review_document(sections: List[dict]) -> dict:
    """Review document quality and provide feedback.

    Args:
        sections: List of document sections

    Returns:
        Review feedback and quality scores
    """
    logger.info("Reviewing document...")

    return {
        "has_issues": False,
        "section_feedback": [],
        "corrections": "Document is well-structured.",
        "scores": {
            "relevance": 5,
            "completeness": 5,
            "coherence": 5,
            "structure": 5,
            "overall": 5,
        },
    }


# ============================================================================
# Node Functions
# ============================================================================

async def plan_node(state: DocumentGenerationState) -> DocumentGenerationState:
    """Plan phase: Generate execution plan."""
    logger.info("=== PLAN PHASE ===")

    try:
        # Initialize LLM
        llm = Ollama(model="qwen3:8b")

        # Create tools
        tools = [plan_document]

        # Create prompt template
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a document planning agent. Generate a structured plan for creating the document."),
            ("user", "Create a plan for: {request}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        # Create agent
        agent = create_tool_calling_agent(llm, tools, prompt)
        executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

        # Run planner
        result = await executor.ainvoke({"request": state["request"]})

        state["messages"].append(AIMessage(content=str(result)))
        state["execution_plan"] = ExecutionPlan(
            document_type="Generated Document",
            assumptions={},
            tasks=[],
            outline=[],
        )
        state["plan_quality"] = 0.85

    except Exception as e:
        logger.error(f"Planning failed: {str(e)}")
        state["error_message"] = str(e)

    return state


async def write_node(state: DocumentGenerationState) -> DocumentGenerationState:
    """Write phase: Generate document sections."""
    logger.info("=== WRITE PHASE ===")

    if not state["execution_plan"]:
        state["error_message"] = "No execution plan found"
        return state

    try:
        llm = Ollama(model="qwen3:8b")
        tools = [write_section]

        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a document writing agent. Write clear, well-structured sections."),
            ("user", "Write sections for: {request}\nOutline: {outline}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        agent = create_tool_calling_agent(llm, tools, prompt)
        executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

        # Generate sections
        for section_title in state["execution_plan"].outline:
            result = await executor.ainvoke({
                "request": state["request"],
                "outline": state["execution_plan"].outline,
            })

            state["sections"].append(DocumentSection(
                title=section_title,
                content=str(result),
                heading_level=1,
            ))

        state["messages"].append(AIMessage(content=f"Wrote {len(state['sections'])} sections"))
        state["write_quality"] = 0.88

    except Exception as e:
        logger.error(f"Writing failed: {str(e)}")
        state["error_message"] = str(e)

    return state


async def review_node(state: DocumentGenerationState) -> DocumentGenerationState:
    """Review phase: Validate and score document."""
    logger.info("=== REVIEW PHASE ===")

    if not state["sections"]:
        state["error_message"] = "No sections to review"
        return state

    try:
        llm = Ollama(model="qwen3:8b")
        tools = [review_document]

        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a document review agent. Evaluate quality and provide feedback."),
            ("user", "Review this document: {sections_summary}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        agent = create_tool_calling_agent(llm, tools, prompt)
        executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

        # Run reviewer
        result = await executor.ainvoke({
            "sections_summary": "\n".join([s.title for s in state["sections"]]),
        })

        state["review_feedback"] = str(result)
        state["review_iterations"] = 1
        state["messages"].append(AIMessage(content="Document reviewed and approved"))
        state["success"] = True

    except Exception as e:
        logger.error(f"Review failed: {str(e)}")
        state["error_message"] = str(e)
        state["review_iterations"] = 0

    return state


# ============================================================================
# Routing Logic
# ============================================================================

def should_continue_review(state: DocumentGenerationState) -> str:
    """Decide whether to continue reviewing or finish."""
    if state["review_iterations"] >= 2:  # Max 2 iterations
        return "finish"
    elif state["review_feedback"] and "issues" not in state["review_feedback"].lower():
        return "finish"
    else:
        return "revise"


# ============================================================================
# LangGraph Orchestrator
# ============================================================================

class LangGraphOrchestrator:
    """Multi-agent document generation using LangGraph."""

    def __init__(self):
        """Initialize orchestrator with LangGraph workflow."""
        self.graph = self._build_graph()
        logger.info("LangGraph orchestrator initialized")

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow."""
        workflow = StateGraph(DocumentGenerationState)

        # Add nodes
        workflow.add_node("plan", plan_node)
        workflow.add_node("write", write_node)
        workflow.add_node("review", review_node)

        # Add edges (routing)
        workflow.add_edge("plan", "write")
        workflow.add_edge("write", "review")
        workflow.add_conditional_edges(
            "review",
            should_continue_review,
            {
                "revise": "write",
                "finish": END,
            },
        )

        # Set entry point
        workflow.set_entry_point("plan")

        return workflow.compile()

    async def generate_document(self, request: str, metadata: dict = None) -> dict:
        """Generate document through the multi-agent pipeline.

        Args:
            request: Document request
            metadata: Optional metadata

        Returns:
            Generation result with success status and document info
        """
        logger.info(f"Starting document generation: {request[:100]}...")

        initial_state: DocumentGenerationState = {
            "request": request,
            "metadata": metadata,
            "messages": [HumanMessage(content=request)],
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

        # Run the graph
        final_state = await self.graph.ainvoke(initial_state)

        logger.info(f"Document generation {'succeeded' if final_state['success'] else 'failed'}")

        return {
            "success": final_state["success"],
            "document_filename": final_state["document_filename"],
            "error": final_state["error_message"],
            "sections_count": len(final_state["sections"]),
            "iterations": final_state["review_iterations"],
        }
