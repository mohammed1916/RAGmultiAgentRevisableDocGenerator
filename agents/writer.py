"""Writer Agent - generates document sections."""

import json
from typing import Dict, List, Optional

from tools.ollama_client import OllamaClient
from models import DocumentSection, ExecutionPlan
from exceptions import WriterException
from logger import setup_logger

logger = setup_logger(__name__)


class WriterAgent:
    """Agent responsible for writing document sections."""

    def __init__(self, ollama_client: OllamaClient):
        """Initialize the Writer Agent.

        Args:
            ollama_client: OllamaClient instance
        """
        self.client = ollama_client

    def write_section(
        self,
        request: str,
        plan: ExecutionPlan,
        section_index: int,
        previous_sections: List[DocumentSection] = None,
    ) -> DocumentSection:
        """Write a single section of the document.

        Args:
            request: Original user request
            plan: ExecutionPlan instance
            section_index: Index of section to write (into plan.outline)
            previous_sections: List of previously written sections

        Returns:
            DocumentSection instance

        Raises:
            WriterException: If writing fails
        """
        if section_index >= len(plan.outline):
            raise WriterException(f"Section index {section_index} out of bounds")

        section_title = plan.outline[section_index]
        logger.info(f"Writing section: {section_title}")

        prompt = self._build_writing_prompt(
            request, plan, section_title, previous_sections
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
        sections = []

        for i, section_title in enumerate(plan.outline):
            section = self.write_section(
                request, plan, i, previous_sections=sections
            )
            sections.append(section)

        logger.info(f"All {len(sections)} sections written")
        return sections

    def _build_writing_prompt(
        self,
        request: str,
        plan: ExecutionPlan,
        section_title: str,
        previous_sections: Optional[List[DocumentSection]] = None,
    ) -> str:
        """Build the writing prompt for a section.

        Args:
            request: Original request
            plan: ExecutionPlan instance
            section_title: Title of the section to write
            previous_sections: Previously written sections

        Returns:
            Formatted prompt
        """
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
- {len(section_title)} words minimum

"""

        if previous_sections:
            prompt += "\nPreviously written sections:\n"
            for prev in previous_sections:
                prompt += f"- {prev.title}: {prev.content[:200]}...\n"

        prompt += """
Return the section as JSON with:
- title: The section title
- content: The section content (1-2 paragraphs, professional tone)
- heading_level: 2 for main sections, 3 for subsections"""

        return prompt

    @staticmethod
    def _format_dict(d: Dict[str, str]) -> str:
        """Format a dictionary as readable text."""
        return "\n".join(f"- {k}: {v}" for k, v in d.items())

    @staticmethod
    def _format_list(lst: List[str]) -> str:
        """Format a list as readable text."""
        return "\n".join(f"{i+1}. {item}" for i, item in enumerate(lst))
