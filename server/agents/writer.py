"""Writer Agent - generates document sections."""

import json
from typing import Dict, List, Optional

from ..tools.ollama_client import OllamaClient
from ..tools.milvus_rag import MilvusRAG
from ..models import DocumentSection, ExecutionPlan
from ..exceptions import WriterException
from ..logger import setup_logger

logger = setup_logger(__name__)


class WriterAgent:
    """Agent responsible for writing document sections."""

    def __init__(self, ollama_client: OllamaClient, rag_system: Optional[MilvusRAG] = None):
        """Initialize the Writer Agent.

        Args:
            ollama_client: OllamaClient instance
            rag_system: Optional MilvusRAG instance for curriculum context
        """
        self.client = ollama_client
        self.rag = rag_system or MilvusRAG()  # Initialize default RAG if not provided

    def write_section(
        self,
        request: str,
        plan: ExecutionPlan,
        section_index: int,
        previous_sections: List[DocumentSection] = None,
        revision_feedback: Optional[str] = None,
    ) -> DocumentSection:
        """Write a single section of the document.

        Args:
            request: Original user request
            plan: ExecutionPlan instance
            section_index: Index of section to write (into plan.outline)
            previous_sections: List of previously written sections
            revision_feedback: Feedback from reviewer for revision (if rewriting)

        Returns:
            DocumentSection instance

        Raises:
            WriterException: If writing fails
        """
        if section_index >= len(plan.outline):
            raise WriterException(f"Section index {section_index} out of bounds")

        section_title = plan.outline[section_index]

        if revision_feedback:
            logger.info(f"Revising section: {section_title} based on feedback")
        else:
            logger.info(f"Writing section: {section_title}")

        prompt = self._build_writing_prompt(
            request, plan, section_title, previous_sections, revision_feedback
        )

        try:
            response = self.client.structured_generate(
                prompt,
                schema={
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "content": {"type": "string"},
                        "heading_level": {"type": "integer", "minimum": 1, "maximum": 3},
                    },
                    "required": ["title", "content", "heading_level"],
                },
            )

            parsed = response.get("parsed_response", {})

            section = DocumentSection(
                title=parsed.get("title", section_title),
                content=parsed.get("content", ""),
                heading_level=parsed.get("heading_level", 2),
            )

            if revision_feedback:
                logger.info(f"Section revised: {section.title} ({len(section.content)} chars)")
            else:
                logger.info(f"Section written: {section.title} ({len(section.content)} chars)")
            return section
        except Exception as e:
            raise WriterException(f"Failed to write section: {str(e)}")

    def write_all_sections(
        self,
        request: str,
        plan: ExecutionPlan,
    ) -> List[DocumentSection]:
        """Write all sections of the document in order.

        Args:
            request: Original user request
            plan: ExecutionPlan instance

        Returns:
            List of DocumentSection instances

        Raises:
            WriterException: If any section writing fails
        """
        # Special handling for todo lists
        if plan.document_type.lower() == "todo list":
            return self._generate_todo_section(request, plan)

        sections = []

        for i, section_title in enumerate(plan.outline):
            section = self.write_section(
                request, plan, i, previous_sections=sections
            )
            sections.append(section)

        logger.info(f"All {len(sections)} sections written")
        return sections

    def _generate_todo_section(self, request: str, plan: ExecutionPlan) -> List[DocumentSection]:
        """Generate a simple todo table from plan tasks.

        Args:
            request: Original request
            plan: ExecutionPlan with tasks

        Returns:
            List with single DocumentSection containing todo table
        """
        logger.info("Generating todo list from plan tasks")

        # Build markdown table
        markdown = "| # | Task | Priority | Deadline | Hours |\n"
        markdown += "|---|------|----------|----------|-------|\n"

        for task in plan.tasks:
            task_id = task.id
            description = task.description.replace("|", "\\|")[:50]
            # Infer priority from task description or use Medium as default
            priority = self._infer_priority(task.description)
            deadline = plan.assumptions.get("deadline", "1 week")
            hours = self._estimate_hours(task.description)

            markdown += f"| {task_id} | {description} | {priority} | {deadline} | {hours} |\n"

        section = DocumentSection(
            title="Priority Todo List",
            content=markdown,
            heading_level=1
        )

        logger.info(f"Todo section generated with {len(plan.tasks)} items")
        return [section]

    @staticmethod
    def _infer_priority(description: str) -> str:
        """Infer priority from task description.

        Args:
            description: Task description

        Returns:
            Priority level (High, Medium, Low)
        """
        desc_lower = description.lower()
        if any(word in desc_lower for word in ["critical", "urgent", "asap", "immediately", "high"]):
            return "High"
        elif any(word in desc_lower for word in ["low", "optional", "later", "secondary"]):
            return "Low"
        return "Medium"

    @staticmethod
    def _estimate_hours(description: str) -> int:
        """Estimate task duration in hours.

        Args:
            description: Task description

        Returns:
            Estimated hours
        """
        desc_lower = description.lower()
        if any(word in desc_lower for word in ["quick", "simple", "brief", "small"]):
            return 1
        elif any(word in desc_lower for word in ["complex", "detailed", "comprehensive", "extensive"]):
            return 8
        return 4

    def _build_writing_prompt(
        self,
        request: str,
        plan: ExecutionPlan,
        section_title: str,
        previous_sections: Optional[List[DocumentSection]] = None,
        revision_feedback: Optional[str] = None,
    ) -> str:
        """Build the writing prompt for a section.

        Args:
            request: Original request
            plan: ExecutionPlan instance
            section_title: Title of the section to write
            previous_sections: Previously written sections
            revision_feedback: Specific feedback from reviewer to address

        Returns:
            Formatted prompt
        """
        # Fetch relevant curriculum context from RAG
        rag_context = self._fetch_rag_context(request, section_title, plan.document_type)

        if revision_feedback:
            prompt = f"""You are an expert technical writer revising a document section based on reviewer feedback.

Original Request: {request}
Document Type: {plan.document_type}

Section to Revise: {section_title}

REVIEWER FEEDBACK (address these specific issues):
{revision_feedback}

Rewrite this section incorporating all feedback. Focus on:
- Fixing the specific issues mentioned above
- Maintaining consistency with the document context
- Keeping professional tone
- Ensuring clarity and completeness

"""
        else:
            prompt = f"""You are an expert technical writer. Write one section of a professional document.

Original Request: {request}

Document Type: {plan.document_type}

Assumptions:
{self._format_dict(plan.assumptions)}

Outline:
{self._format_list(plan.outline)}

Section to Write: {section_title}

Write this section in a professional, clear manner. The content should be:
- Substantive and detailed
- Professional in tone
- Consistent with the overall document context

"""

        if rag_context:
            prompt += f"\nRELEVANT CURRICULUM CONTEXT (from curriculum database):\n{rag_context}\n"

        if previous_sections:
            prompt += "\nPreviously written sections for context:\n"
            for prev in previous_sections:
                prompt += f"- {prev.title}: {prev.content[:200]}...\n"

        prompt += """
Return the section as JSON with:
- title: The section title
- content: The section content (substantive and well-written)
- heading_level: 2 for main sections, 3 for subsections"""

        return prompt

    def _fetch_rag_context(self, request: str, section_title: str, doc_type: str) -> str:
        """Fetch relevant curriculum context from RAG system.

        Args:
            request: User request
            section_title: Current section title
            doc_type: Document type

        Returns:
            Formatted RAG context or empty string if no results
        """
        try:
            # Search for relevant curriculum data
            search_query = f"{request} {section_title}"
            results = self.rag.search(search_query, top_k=3)

            if not results:
                return ""

            context = "Retrieved curriculum references:\n"
            for i, result in enumerate(results, 1):
                context += f"\n{i}. {result['doc_id']}:\n"
                context += f"   {result['content'][:300]}...\n"

            return context
        except Exception as e:
            logger.warning(f"RAG context fetch failed: {e}")
            return ""

    @staticmethod
    def _format_dict(d: Dict[str, str]) -> str:
        """Format a dictionary as readable text."""
        return "\n".join(f"- {k}: {v}" for k, v in d.items())

    @staticmethod
    def _format_list(lst: List[str]) -> str:
        """Format a list as readable text."""
        return "\n".join(f"{i+1}. {item}" for i, item in enumerate(lst))
