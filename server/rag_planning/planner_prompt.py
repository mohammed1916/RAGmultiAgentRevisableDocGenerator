"""Dynamic prompt builder for retrieval planner."""

from typing import List, Optional, Dict

from .models import CollectionMetadata
from .config.collection_registry import CollectionRegistry
from ..base.logger import setup_logger

logger = setup_logger(__name__)


class PlannerPromptBuilder:
    """Builds dynamic planning prompts based on available collections.

    Prompt adapts automatically when collections are added/removed.
    No hardcoded knowledge of collections - all from registry.
    """

    def __init__(self, registry: Optional[CollectionRegistry] = None):
        """Initialize prompt builder.

        Args:
            registry: CollectionRegistry instance (uses singleton if None)
        """
        self.registry = registry or CollectionRegistry()

    def build_planning_prompt(
        self,
        query: str,
        session_history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """Build a planning prompt for the planner.

        Dynamically includes available collections and their descriptions.

        Args:
            query: User's information need
            session_history: Optional conversation history

        Returns:
            Formatted prompt for LLM planner
        """
        collections = self.registry.get_all_collections()

        if not collections:
            logger.warning("No collections available for planning")
            return ""

        prompt = """You are a Retrieval Planner for an educational knowledge base system.

Your ONLY responsibility is to plan retrieval, NOT to retrieve documents or answer questions.

You will analyze the user's query and output a structured plan for how the retrieval system should search.

=== YOUR DECISION SCOPE ===

You DECIDE:
1. Which collection(s) should be searched
2. What metadata filters to apply (if any)
3. How many results (top_k) to retrieve
4. Whether the query needs clarification

You DO NOT DECIDE:
- Reranking, hybrid search, fallback strategies (retriever handles these)
- ANN search parameters, index-specific behavior
- Result evaluation or re-planning (evaluation stage handles these)

=== AVAILABLE COLLECTIONS ===

"""

        for col in collections:
            prompt += self._format_collection_info(col)

        prompt += """
=== SESSION HISTORY (if any) ===

"""
        if session_history:
            for msg in session_history[-5:]:  # Last 5 messages for context
                role = msg.get("role", "unknown").upper()
                content = msg.get("content", "")[:200]
                prompt += f"{role}: {content}\n"
        else:
            prompt += "(No prior conversation)"

        prompt += f"""

=== USER QUERY ===

{query}

=== PLANNING INSTRUCTIONS ===

1. Analyze the query to understand the user's information need
2. Identify relevant collection(s)
3. Determine if metadata filters would help (e.g., filter by subject)
4. Estimate appropriate top_k based on query specificity
5. Flag if the query is ambiguous and needs clarification

Examples of good planning:
- "Class 12 Physics" → collections: [cbse_class_12], filters: [subject=Physics], top_k: 5
- "JEE Main preparation" → collections: [jee], filters: [], top_k: 8
- "Compare CBSE and JEE" → collections: [cbse_class_12, jee], filters: [], top_k: 8
- "Something for class X" → needs_clarification: true

=== YOUR OUTPUT ===

Respond ONLY with valid JSON (no markdown, no extra text):

{{
  "collections": ["collection_name_1", "collection_name_2"],
  "filters": [
    {{"field": "subject", "value": "Physics", "operator": "eq"}},
    {{"field": "difficulty", "value": ["easy", "medium"], "operator": "in"}}
  ],
  "top_k": 5,
  "needs_clarification": false,
  "clarification_questions": null,
  "reasoning": "Explanation of planning decisions",
  "confidence": 0.9
}}

Field requirements:
- collections: List of valid collection names from above
- filters: List of metadata filters (empty list if none)
- top_k: Integer between 1-100
- needs_clarification: Boolean
- clarification_questions: List of questions if needs_clarification=true, else null
- reasoning: Brief explanation of why these collections/filters were chosen
- confidence: Your confidence in this plan (0.0-1.0)
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
        text = f"\n{col.display_name} (collection: {col.name})\n"
        text += f"  Description: {col.description.strip()}\n"

        if col.document_count:
            text += f"  Documents: {col.document_count:,}\n"

        if col.metadata_fields:
            fields = ", ".join(col.metadata_fields.keys())
            text += f"  Available metadata filters: {fields}\n"

        return text

    def get_collections_summary(self) -> str:
        """Get summary of available collections for logging/debugging.

        Returns:
            Formatted text describing collections
        """
        return self.registry.get_description_text()
