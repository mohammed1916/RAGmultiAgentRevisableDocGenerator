"""LangChain agents with tool-calling integration.

Wraps existing Planner, Writer, and Reviewer agents as LangChain tools.
"""

from typing import Optional
from langchain.tools import tool
from langchain_community.llms import Ollama
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from .logger import setup_logger
from .agents.planner import PlannerAgent
from .agents.writer import WriterAgent
from .agents.reviewer import ReviewerAgent
from .tools.milvus_rag import MilvusRAG

logger = setup_logger(__name__)


# ============================================================================
# Tool Definitions
# ============================================================================

@tool
def plan_document_tool(
    request: str,
    metadata: Optional[dict] = None,
) -> dict:
    """Generate execution plan for document generation.

    Uses the Planner agent to create a structured plan including:
    - Document type and scope
    - Assumptions about the request
    - Outline and tasks with dependencies

    Args:
        request: Natural language request for document
        metadata: Optional context (audience, scope, tone, etc.)

    Returns:
        Execution plan with outline and task structure
    """
    logger.info(f"Planning for request: {request[:100]}...")

    try:
        llm = Ollama(model="qwen3:8b")
        planner = PlannerAgent(llm)

        # Convert metadata to assumptions
        assumptions = metadata or {}

        # Generate plan
        plan = planner.generate_plan(
            request=request,
            context=assumptions,
        )

        logger.info(f"Generated plan with {len(plan.outline)} sections")

        return {
            "document_type": plan.document_type,
            "assumptions": plan.assumptions,
            "outline": plan.outline,
            "tasks": [
                {
                    "id": t.get("id", i),
                    "description": t.get("description", ""),
                    "dependencies": t.get("dependencies", []),
                }
                for i, t in enumerate(plan.tasks, 1)
            ],
            "success": True,
        }

    except Exception as e:
        logger.error(f"Planning failed: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "outline": [],
            "tasks": [],
        }


@tool
def write_sections_tool(
    request: str,
    outline: list,
    rag_context_enabled: bool = True,
) -> dict:
    """Write document sections with RAG context.

    Uses the Writer agent to generate content for each section,
    optionally grounding in curriculum RAG context.

    Args:
        request: Document request
        outline: List of section titles
        rag_context_enabled: Whether to fetch RAG context

    Returns:
        List of written sections with content
    """
    logger.info(f"Writing {len(outline)} sections")

    try:
        llm = Ollama(model="qwen3:8b")
        writer = WriterAgent(llm)

        # Initialize RAG if enabled
        rag = None
        if rag_context_enabled:
            rag = MilvusRAG()

        sections = []

        for section_title in outline:
            # Fetch RAG context if available
            rag_content = ""
            if rag:
                try:
                    results = rag.search_documents(section_title, top_k=3)
                    rag_content = "\n".join([r.get("content", "") for r in results])
                except Exception as e:
                    logger.warning(f"RAG search failed: {e}")

            # Write section
            section = writer.write_section(
                title=section_title,
                request=request,
                context=rag_content,
            )

            sections.append({
                "title": section.title,
                "content": section.content,
                "heading_level": section.heading_level,
            })

        logger.info(f"Written {len(sections)} sections")

        return {
            "success": True,
            "sections": sections,
            "section_count": len(sections),
        }

    except Exception as e:
        logger.error(f"Writing failed: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "sections": [],
        }


@tool
def review_document_tool(sections: list) -> dict:
    """Review document quality and provide scores.

    Uses the Reviewer agent to evaluate document quality on:
    - Relevance to request
    - Completeness of coverage
    - Coherence of content
    - Structure and organization

    Args:
        sections: List of written sections

    Returns:
        Review feedback with quality scores
    """
    logger.info(f"Reviewing {len(sections)} sections")

    try:
        llm = Ollama(model="qwen3:8b")
        reviewer = ReviewerAgent(llm)

        # Build section content for review
        section_summaries = [f"- {s['title']}: {s['content'][:200]}..." for s in sections]

        # Review document
        scores = reviewer.review_document(
            sections=sections,
            feedback_requests=section_summaries,
        )

        logger.info(f"Review complete: {scores.overall}/5")

        return {
            "success": True,
            "scores": {
                "relevance": scores.relevance,
                "completeness": scores.completeness,
                "coherence": scores.coherence,
                "structure": scores.structure,
                "overall": scores.overall,
            },
            "feedback": scores.feedback,
        }

    except Exception as e:
        logger.error(f"Review failed: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "scores": {},
        }


@tool
def fetch_rag_context_tool(query: str, top_k: int = 5) -> dict:
    """Retrieve curriculum context from RAG vector database.

    Args:
        query: Search query for curriculum
        top_k: Number of top results to return

    Returns:
        Retrieved curriculum documents
    """
    logger.info(f"Fetching RAG context for: {query}")

    try:
        rag = MilvusRAG()
        results = rag.search_documents(query, top_k=top_k)

        logger.info(f"Retrieved {len(results)} context documents")

        return {
            "success": True,
            "query": query,
            "results": results,
            "count": len(results),
        }

    except Exception as e:
        logger.error(f"RAG fetch failed: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "results": [],
        }


# ============================================================================
# Agent Executors
# ============================================================================

def create_planner_agent():
    """Create LangChain planner agent with tool-calling."""
    llm = Ollama(model="qwen3:8b")
    tools = [plan_document_tool]

    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert document planner. Your role is to:
1. Analyze document requests
2. Create comprehensive outlines
3. Identify key sections and tasks
4. Break down complex documents into manageable parts

Always provide structured, hierarchical plans."""),
        ("user", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    agent = create_tool_calling_agent(llm, tools, prompt)
    return AgentExecutor(agent=agent, tools=tools, verbose=True)


def create_writer_agent():
    """Create LangChain writer agent with tool-calling."""
    llm = Ollama(model="qwen3:8b")
    tools = [write_sections_tool, fetch_rag_context_tool]

    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert document writer. Your role is to:
1. Write clear, well-organized sections
2. Ground content in provided context
3. Ensure consistency across sections
4. Maintain appropriate tone and style

Fetch RAG context when you need curriculum or reference material."""),
        ("user", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    agent = create_tool_calling_agent(llm, tools, prompt)
    return AgentExecutor(agent=agent, tools=tools, verbose=True)


def create_reviewer_agent():
    """Create LangChain reviewer agent with tool-calling."""
    llm = Ollama(model="qwen3:8b")
    tools = [review_document_tool]

    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert document reviewer. Your role is to:
1. Evaluate document quality across multiple dimensions
2. Identify gaps and inconsistencies
3. Provide constructive feedback
4. Score quality on a 1-5 scale

Focus on: relevance, completeness, coherence, structure."""),
        ("user", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    agent = create_tool_calling_agent(llm, tools, prompt)
    return AgentExecutor(agent=agent, tools=tools, verbose=True)
