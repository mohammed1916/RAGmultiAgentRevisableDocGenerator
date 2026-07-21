"""LangGraph-based multi-agent document orchestration.

Uses LangGraph StateGraph for complex workflow coordination with state management,
conditional routing, and agent node execution.
"""

from typing import TypedDict, Optional, List, Annotated

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.runnables import RunnableConfig

from .base import Orchestrator
from ...base.logger import setup_logger
from ...base.models import DocumentRequest, ExecutionPlan, DocumentSection, ReviewFeedback
from ...config import config

logger = setup_logger(__name__)


class DocumentGenerationState(TypedDict, total=False):
    """State schema for document generation workflow.

    Tracks the entire document generation pipeline with state updates at each node.
    """
    request: str
    metadata: Optional[dict]
    messages: Annotated[List[BaseMessage], add_messages]
    execution_plan: Optional[ExecutionPlan]
    plan_quality: Optional[float]
    sections: List[dict]
    write_quality: Optional[float]
    review_feedback: Optional[str]
    review_issues: Optional[List[dict]]
    review_iterations: int
    success: bool
    document_filename: Optional[str]
    error_message: Optional[str]
    metrics: Optional[dict]


async def plan_node(state: DocumentGenerationState, orchestrator: "Orchestrator") -> DocumentGenerationState:
    """Plan document structure.

    Node that calls planner agent to create execution plan from request.
    """
    logger.info("[PLAN] Starting document planning")

    try:
        doc_request = DocumentRequest(
            request=state["request"],
            metadata=state.get("metadata")
        )
        plan = orchestrator.planner.plan(doc_request.request)

        logger.info(f"[OK] Plan created: {plan.document_type} with {len(plan.outline)} sections")

        return {
            "execution_plan": plan,
            "plan_quality": 0.85,
            "messages": [AIMessage(content=f"Created {plan.document_type} plan")],
        }
    except Exception as e:
        logger.error(f"[ERROR] Planning failed: {str(e)}")
        return {
            "error_message": f"Planning error: {str(e)}",
            "messages": [AIMessage(content=f"Planning error: {str(e)}")],
        }


async def write_node(state: DocumentGenerationState, orchestrator: "Orchestrator") -> DocumentGenerationState:
    """Write document sections.

    Node that calls writer agent to generate document content based on plan.
    """
    logger.info("[WRITE] Starting document writing")

    if not state.get("execution_plan"):
        error_msg = "No execution plan available"
        logger.error(error_msg)
        return {"error_message": error_msg}

    try:
        sections = orchestrator.writer.write_all_sections(
            state["request"],
            state["execution_plan"]
        )

        logger.info(f"[OK] Written {len(sections)} sections")

        return {
            "sections": [
                {
                    "title": s.title,
                    "content": s.content,
                    "heading_level": s.heading_level,
                }
                for s in sections
            ],
            "write_quality": 0.90,
            "messages": [AIMessage(content=f"Written {len(sections)} document sections")],
        }
    except Exception as e:
        logger.error(f"[ERROR] Writing failed: {str(e)}")
        return {
            "error_message": f"Writing error: {str(e)}",
            "messages": [AIMessage(content=f"Writing error: {str(e)}")],
        }


async def review_node(state: DocumentGenerationState, orchestrator: "Orchestrator") -> DocumentGenerationState:
    """Review document quality.

    Node that calls reviewer agent to evaluate document and provide feedback.
    """
    logger.info("[REVIEW] Starting document review")

    if not state.get("sections"):
        error_msg = "No sections to review"
        logger.error(error_msg)
        return {"error_message": error_msg}

    try:
        # Convert dict sections back to DocumentSection objects for reviewer
        sections = [
            DocumentSection(
                title=s["title"],
                content=s["content"],
                heading_level=s.get("heading_level", 1),
            )
            for s in state["sections"]
        ]

        feedback = orchestrator.reviewer.review_document(
            state["execution_plan"].document_type if state.get("execution_plan") else "Document",
            sections
        )

        state["review_iterations"] = state.get("review_iterations", 0) + 1

        if feedback.has_issues:
            logger.warning(f"Issues found: {len(feedback.section_feedback)} sections need revision")
            return {
                "success": False,
                "review_feedback": feedback.corrections or "Issues found during review",
                "review_issues": [
                    {
                        "section_title": sf.section_title,
                        "feedback": sf.feedback,
                        "issues": sf.issues,
                    }
                    for sf in feedback.section_feedback
                ],
                "review_iterations": state["review_iterations"],
                "messages": [AIMessage(content=f"Review complete: Issues found in {len(feedback.section_feedback)} sections")],
            }
        else:
            logger.info("[OK] Review passed - no issues found")
            return {
                "review_feedback": "Document approved",
                "review_issues": None,
                "review_iterations": state["review_iterations"],
                "success": True,
                "messages": [AIMessage(content="Review complete: Document approved")],
            }
    except Exception as e:
        logger.error(f"[ERROR] Review failed: {str(e)}")
        return {
            "error_message": f"Review error: {str(e)}",
            "messages": [AIMessage(content=f"Review error: {str(e)}")],
        }


async def refine_node(state: DocumentGenerationState, orchestrator: "Orchestrator") -> DocumentGenerationState:
    """Refine document based on review feedback.

    Node that revises sections based on reviewer feedback.
    """
    logger.info("[REFINE] Refining document")

    try:
        sections = [
            DocumentSection(
                title=s["title"],
                content=s["content"],
                heading_level=s.get("heading_level", 1),
            )
            for s in state["sections"]
        ]

        feedback = ReviewFeedback(
            has_issues=True,
            feedback_summary=state.get("review_feedback", ""),
            section_feedback=state.get("review_issues", []),
        )

        refined_sections = orchestrator._refine_sections(
            state["request"],
            state["execution_plan"],
            sections,
            feedback
        )

        logger.info(f"[OK] Refined {len(refined_sections)} sections")

        return {
            "sections": [
                {
                    "title": s.title,
                    "content": s.content,
                    "heading_level": s.heading_level,
                }
                for s in refined_sections
            ],
            "messages": [AIMessage(content=f"Refined {len(refined_sections)} sections based on feedback")],
        }
    except Exception as e:
        logger.error(f"[ERROR] Refinement failed: {str(e)}")
        return {
            "error_message": f"Refinement error: {str(e)}",
            "messages": [AIMessage(content=f"Refinement error: {str(e)}")],
        }


async def generate_node(state: DocumentGenerationState) -> DocumentGenerationState:
    """Generate final document file.

    Node that creates output document (DOCX) from approved sections.
    """
    logger.info("[GENERATE] Generating output document")

    try:
        import os
        from datetime import datetime
        from ...tools import DOCXGenerator

        if not state.get("sections"):
            return {"error_message": "No sections to generate document from"}

        # Create document
        generator = DOCXGenerator()
        title = "Generated Study Plan"
        if state.get("execution_plan"):
            title = state["execution_plan"].document_type

        generator.create_document(title=title)

        # Add sections
        for section in state["sections"]:
            if isinstance(section, dict):
                generator.add_heading(section.get("title", ""), level=section.get("heading_level", 1))
                content = section.get("content", "")
                # Use markdown rendering for markdown content (tables, lists, etc)
                if "|" in content or "*" in content or "-" in content:
                    generator.add_markdown_section(content)
                else:
                    generator.add_paragraph(content)
            else:
                generator.add_heading(section.title, level=section.heading_level)
                content = section.content
                # Use markdown rendering for markdown content (tables, lists, etc)
                if "|" in content or "*" in content or "-" in content:
                    generator.add_markdown_section(content)
                else:
                    generator.add_paragraph(content)

        # Save document to the same directory /files and /download read from.
        output_dir = config.document_output_dir
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(output_dir, f"document_{timestamp}.docx")
        saved_path = generator.save(filepath)
        # /files and /download key off the bare filename, not the full path.
        filename = os.path.basename(saved_path)
        logger.info(f"[OK] Document generated: {filename}")

        return {
            "document_filename": filename,
            "success": True,
            "messages": [AIMessage(content=f"Document generated: {filename}")],
        }
    except Exception as e:
        logger.error(f"[ERROR] Generation failed: {str(e)}")
        return {
            "error_message": f"Generation error: {str(e)}",
            "messages": [AIMessage(content=f"Generation error: {str(e)}")],
        }


def should_continue_review(state: DocumentGenerationState) -> str:
    """Conditional routing for review loop.

    Determines whether to continue reviewing/refining or finish.
    Returns: "revise" to refine sections, "finish" to end review.
    """
    max_iterations = config.max_review_iterations
    current_iterations = state.get("review_iterations", 0)
    has_issues = state.get("review_issues") is not None

    if not has_issues:
        logger.info("No issues - moving to document generation")
        return "finish"

    if current_iterations >= max_iterations:
        logger.warning(f"Max review iterations ({max_iterations}) reached")
        return "finish"

    logger.info(f"Issues found (iteration {current_iterations}/{max_iterations}) - refining")
    return "revise"


class LangGraphOrchestrator:
    """LangGraph-based orchestrator for document generation.

    Uses StateGraph to define multi-agent workflow with:
    - State machine for tracking generation progress
    - Agent nodes for planning, writing, reviewing, refining
    - Conditional routing for iterative refinement
    - Message accumulation for audit trail
    """

    def __init__(self, orchestrator: "Orchestrator" = None):
        """Initialize LangGraph workflow.

        Args:
            orchestrator: A shared :class:`Orchestrator` reused by every node.
                Passing one avoids rebuilding the LLM client, Milvus RAG and the
                embedding model on each node call. One is created if omitted.
        """
        self.orchestrator = orchestrator or Orchestrator()
        self.graph = self._build_graph()
        logger.info("LangGraph orchestrator initialized")

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph StateGraph workflow.

        Creates a DAG with nodes for each stage and conditional edges
        for the review loop.
        """
        from functools import partial

        graph = StateGraph(DocumentGenerationState)

        # Bind the shared orchestrator into each agent node so the LLM client,
        # Milvus RAG and embedding model are constructed once, not per node.
        graph.add_node("plan", partial(plan_node, orchestrator=self.orchestrator))
        graph.add_node("write", partial(write_node, orchestrator=self.orchestrator))
        graph.add_node("review", partial(review_node, orchestrator=self.orchestrator))
        graph.add_node("refine", partial(refine_node, orchestrator=self.orchestrator))
        graph.add_node("generate", generate_node)

        # Add edges
        graph.add_edge(START, "plan")
        graph.add_edge("plan", "write")
        graph.add_edge("write", "review")

        # Conditional routing from review
        graph.add_conditional_edges(
            "review",
            should_continue_review,
            {
                "revise": "refine",
                "finish": "generate",
            }
        )

        # After refine, go back to review
        graph.add_edge("refine", "review")

        # Generate leads to end
        graph.add_edge("generate", END)

        return graph.compile()

    async def generate_document(self, request: str, metadata: dict = None) -> dict:
        """Generate document through LangGraph workflow.

        Executes the full planning → writing → review → generate pipeline
        with state tracking and conditional routing.

        Args:
            request: Document generation request
            metadata: Optional metadata (audience, scope, tone, sections)

        Returns:
            Dictionary with success status and generation details
        """
        logger.info(f"[START] Starting document generation: {request[:100]}...")

        initial_state: DocumentGenerationState = {
            "request": request,
            "metadata": metadata or {},
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

        try:
            result = await self.graph.ainvoke(
                initial_state,
                config=RunnableConfig(run_name="document_generation")
            )

            return {
                "success": result.get("success", False),
                "document_filename": result.get("document_filename"),
                "error": result.get("error_message"),
                "sections_count": len(result.get("sections", [])),
                "iterations": result.get("review_iterations", 0),
                "messages": len(result.get("messages", [])),
            }
        except Exception as e:
            logger.error(f"✗ Document generation failed: {str(e)}")
            return {
                "success": False,
                "document_filename": None,
                "error": str(e),
                "sections_count": 0,
                "iterations": 0,
                "messages": 0,
            }
