"""Dynamic prompt builder for routing system."""

from typing import List

from .models import CollectionMetadata
from .config.collection_registry import CollectionRegistry
from ..base.logger import setup_logger

logger = setup_logger(__name__)


class PromptBuilder:
    """Builds dynamic routing prompts based on available collections.

    Prompt is regenerated on each use to adapt to registry changes.
    """

    def __init__(self, registry: CollectionRegistry = None):
        """Initialize prompt builder.

        Args:
            registry: CollectionRegistry instance (uses singleton if None)
        """
        self.registry = registry or CollectionRegistry()

    def build_routing_prompt(self, query: str) -> str:
        """Build a routing prompt for the given query.

        Dynamically constructs prompt based on active collections in registry.

        Args:
            query: User query

        Returns:
            Formatted prompt for LLM router
        """
        active_collections = self.registry.get_active_collections()

        if not active_collections:
            logger.warning("No active collections for routing")
            return ""

        prompt = f"""You are an intelligent router for an educational knowledge base system.

Your task is to determine which knowledge source collection(s) a user's query should be routed to.

=== AVAILABLE COLLECTIONS ===

"""

        for col in active_collections:
            prompt += self._format_collection_info(col)

        prompt += f"""
=== USER QUERY ===
{query}

=== ROUTING INSTRUCTIONS ===

1. Analyze the user's query to understand what they need
2. Identify which collection(s) best match the query
3. You MAY select multiple collections if the query spans topics from different sources
4. ALWAYS prioritize active collections

Examples of good routing:
- "Class 12 Physics syllabus" → cbse_class_12
- "JEE Main syllabus" → jee
- "I'm preparing for boards and JEE" → cbse_class_12, jee
- "Compare CBSE and JEE Electrostatics" → cbse_class_12, jee

=== YOUR RESPONSE ===

Respond ONLY with valid JSON in this exact format (no markdown, no extra text):

{{
  "selected_collections": ["collection_name_1", "collection_name_2"],
  "reasoning": "Brief explanation of why these collections were selected",
  "collection_scores": {{
    "cbse_class_12": 0.95,
    "jee": 0.3
  }},
  "fallback_collections": ["collection_name_for_no_results"]
}}

Notes:
- selected_collections: List of collection names to search
- reasoning: 1-2 sentences explaining the routing decision
- collection_scores: Confidence score (0-1) for each collection (include all active ones)
- fallback_collections: Collections to try if selected ones return no results
"""

        return prompt

    @staticmethod
    def _format_collection_info(col: CollectionMetadata) -> str:
        """Format collection metadata for prompt.

        Args:
            col: Collection metadata

        Returns:
            Formatted text block
        """
        text = f"\n{col.display_name}:\n"
        text += f"  - Name: {col.name}\n"
        text += f"  - Description: {col.description}\n"
        text += f"  - Type: {col.source_type}\n"

        if col.keywords:
            keywords_str = ", ".join(col.keywords[:8])
            text += f"  - Keywords: {keywords_str}\n"

        if col.tags:
            tags_str = ", ".join(col.tags[:5])
            text += f"  - Topics: {tags_str}\n"

        if col.document_count:
            text += f"  - Documents: {col.document_count}\n"

        return text

    def get_collection_context(self) -> str:
        """Get a text description of all active collections for debugging/logging.

        Returns:
            Formatted text describing available collections
        """
        return self.registry.get_description_text()
