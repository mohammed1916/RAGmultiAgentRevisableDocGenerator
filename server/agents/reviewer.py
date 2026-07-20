"""Reviewer Agent - reviews and scores documents."""

import json
from typing import List

from ..tools import OllamaClient
from ..base.models import DocumentSection, ReviewFeedback, QualityScore, SectionFeedback
from ..base.exceptions import ReviewerException
from ..base.logger import setup_logger

logger = setup_logger(__name__)


class ReviewerAgent:
    """Agent responsible for reviewing documents."""

    def __init__(self, ollama_client: OllamaClient):
        """Initialize the Reviewer Agent.

        Args:
            ollama_client: OllamaClient instance
        """
        self.client = ollama_client

    def review_document(
        self, title: str, sections: List[DocumentSection]
    ) -> ReviewFeedback:
        """Review a document for quality issues and identify specific sections needing fixes.

        Args:
            title: Document title
            sections: List of document sections

        Returns:
            ReviewFeedback instance with section-specific issues

        Raises:
            ReviewerException: If review fails
        """
        logger.info("Starting document review with section-specific feedback")

        document_text = self._format_document(title, sections)
        prompt = self._build_review_prompt(document_text, sections)

        try:
            response = self.client.structured_generate(
                prompt,
                schema={
                    "type": "object",
                    "properties": {
                        "has_issues": {"type": "boolean"},
                        "grammar_issues": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "consistency_issues": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "structure_issues": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "tone_issues": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "section_feedback": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "section_title": {"type": "string"},
                                    "issues": {"type": "array", "items": {"type": "string"}},
                                    "feedback": {"type": "string"},
                                },
                                "required": ["section_title", "issues", "feedback"],
                            },
                        },
                        "corrections": {"type": "string"},
                    },
                    "required": ["has_issues", "corrections"],
                },
            )

            parsed = response.get("parsed_response", {})

            section_feedbacks = [
                SectionFeedback(
                    section_title=sf.get("section_title", "Unknown"),
                    issues=sf.get("issues", []),
                    feedback=sf.get("feedback", ""),
                )
                for sf in parsed.get("section_feedback", [])
            ]

            feedback = ReviewFeedback(
                has_issues=parsed.get("has_issues", False),
                grammar_issues=parsed.get("grammar_issues", []),
                consistency_issues=parsed.get("consistency_issues", []),
                structure_issues=parsed.get("structure_issues", []),
                tone_issues=parsed.get("tone_issues", []),
                section_feedback=section_feedbacks,
                corrections=parsed.get("corrections", ""),
            )

            if feedback.has_issues:
                logger.warning(f"Review found {len(section_feedbacks)} sections with issues")
                for sf in section_feedbacks:
                    logger.warning(f"  - {sf.section_title}: {sf.feedback[:100]}...")
            else:
                logger.info("Review passed - no issues found")

            return feedback
        except Exception as e:
            raise ReviewerException(f"Failed to review document: {str(e)}")

    def score_document(
        self, title: str, sections: List[DocumentSection]
    ) -> QualityScore:
        """Score a document on quality dimensions.

        Args:
            title: Document title
            sections: List of document sections

        Returns:
            QualityScore instance

        Raises:
            ReviewerException: If scoring fails
        """
        logger.info("Scoring document quality")

        document_text = self._format_document(title, sections)
        prompt = self._build_scoring_prompt(document_text)

        try:
            response = self.client.structured_generate(
                prompt,
                schema={
                    "type": "object",
                    "properties": {
                        "relevance": {"type": "integer", "minimum": 1, "maximum": 5},
                        "completeness": {"type": "integer", "minimum": 1, "maximum": 5},
                        "coherence": {"type": "integer", "minimum": 1, "maximum": 5},
                        "structure": {"type": "integer", "minimum": 1, "maximum": 5},
                        "overall": {"type": "integer", "minimum": 1, "maximum": 5},
                    },
                    "required": ["relevance", "completeness", "coherence", "structure", "overall"],
                },
            )

            parsed = response.get("parsed_response", {})

            score = QualityScore(
                relevance=parsed.get("relevance", 3),
                completeness=parsed.get("completeness", 3),
                coherence=parsed.get("coherence", 3),
                structure=parsed.get("structure", 3),
                overall=parsed.get("overall", 3),
            )

            logger.info(f"Document scored: {score}")
            return score
        except Exception as e:
            raise ReviewerException(f"Failed to score document: {str(e)}")

    def _build_review_prompt(self, document_text: str, sections: List[DocumentSection] = None) -> str:
        """Build the review prompt with section-specific feedback.

        Args:
            document_text: Complete document text
            sections: List of document sections (for targeted review)

        Returns:
            Formatted prompt
        """
        section_list = ""
        if sections:
            section_list = "\n\nSections to review:\n"
            for i, section in enumerate(sections, 1):
                section_list += f"{i}. {section.title}\n"

        return f"""You are an expert document reviewer. Review this document for quality issues.

Document:
{document_text}
{section_list}

Perform a thorough review checking for:
1. Grammar and spelling errors
2. Consistency (terminology, style, formatting across sections)
3. Structure and logical flow
4. Professional tone alignment
5. Alignment with document purpose

For each section that has issues, provide specific feedback on what needs to be fixed.

Return JSON with:
- has_issues: boolean indicating if any issues were found
- grammar_issues: list of grammar/spelling problems (general)
- consistency_issues: list of consistency problems across sections
- structure_issues: list of structural or flow problems
- tone_issues: list of tone inconsistencies
- section_feedback: array of objects, each with:
  * section_title: name of the section
  * issues: array of specific issues found in that section
  * feedback: detailed description of what to fix in this section
- corrections: text describing all recommended corrections"""

    def _build_scoring_prompt(self, document_text: str) -> str:
        """Build the scoring prompt.

        Args:
            document_text: Complete document text

        Returns:
            Formatted prompt
        """
        return f"""You are an expert document evaluator. Score this document on multiple dimensions.

Document:
{document_text}

Score the document on a scale of 1-5 for:
1. Relevance: Does it address the original request?
2. Completeness: Are all important topics covered?
3. Coherence: Is the content logically organized and connected?
4. Structure: Is the document well-structured and easy to follow?
5. Overall: Overall quality of the document

Return JSON with scores for each dimension (1-5) and an overall score."""

    @staticmethod
    def _format_document(title: str, sections: List[DocumentSection]) -> str:
        """Format document for review.

        Args:
            title: Document title
            sections: List of document sections

        Returns:
            Formatted document text
        """
        text = f"Title: {title}\n\n"
        for section in sections:
            text += f"{section.title}\n{section.content}\n\n"
        return text
