"""LLM-based router for collection selection."""

import json
from typing import Optional

from .models import RouterRequest, RouterResponse, RouterDecision, CollectionMetadata
from .prompt_builder import PromptBuilder
from .config.collection_registry import CollectionRegistry
from ..tools import OllamaClient
from ..base.logger import setup_logger

logger = setup_logger(__name__)


class QueryRouter:
    """Routes queries to appropriate Milvus collections using LLM.

    The router:
    1. Receives a user query
    2. Builds dynamic prompt based on available collections
    3. Uses LLM to determine which collection(s) to search
    4. Returns structured routing decision with confidence scores
    """

    def __init__(
        self,
        llm_client: Optional[OllamaClient] = None,
        registry: Optional[CollectionRegistry] = None,
        prompt_builder: Optional[PromptBuilder] = None,
    ):
        """Initialize router.

        Args:
            llm_client: OllamaClient instance (uses default if None)
            registry: CollectionRegistry instance (uses singleton if None)
            prompt_builder: PromptBuilder instance (creates new if None)
        """
        self.client = llm_client or OllamaClient()
        self.registry = registry or CollectionRegistry()
        self.prompt_builder = prompt_builder or PromptBuilder(self.registry)

    def route(self, request: RouterRequest) -> RouterResponse:
        """Route a query to appropriate collections.

        Args:
            request: RouterRequest containing query and selector config

        Returns:
            RouterResponse with decision and collection metadata

        Raises:
            ValueError: If routing fails or no collections selected
        """
        query = request.query
        logger.info(f"Routing query: {query[:80]}...")

        # Build dynamic prompt
        prompt = self.prompt_builder.build_routing_prompt(query)

        # Get LLM routing decision
        try:
            response = self.client.generate(prompt, temperature=0.3, max_tokens=500)
            decision_json = self._extract_json_from_response(response)
            decision = RouterDecision(**decision_json)
        except Exception as e:
            logger.error(f"Router LLM call failed: {e}")
            raise ValueError(f"Failed to route query: {e}")

        # Apply selector filtering
        selected_names = self._apply_selector(decision, request.selector_config)

        if not selected_names:
            logger.warning(f"No collections selected after filtering for: {query[:80]}...")
            raise ValueError("No valid collections selected for this query")

        # Get collection metadata
        collections_info = [
            self.registry.get_collection(name)
            for name in selected_names
            if self.registry.get_collection(name)
        ]

        logger.info(f"Routed to {len(collections_info)} collections: {selected_names}")

        return RouterResponse(
            decision=RouterDecision(
                query=query,
                selected_collections=selected_names,
                reasoning=decision.reasoning,
                collection_scores=decision.collection_scores,
                fallback_collections=decision.fallback_collections,
            ),
            collections_info=collections_info,
        )

    @staticmethod
    def _extract_json_from_response(response: str) -> dict:
        """Extract JSON from LLM response, handling markdown code blocks.

        Args:
            response: Raw LLM response

        Returns:
            Parsed JSON dictionary

        Raises:
            ValueError: If JSON extraction fails
        """
        # Remove markdown code blocks if present
        if "```json" in response:
            response = response.split("```json")[1].split("```")[0]
        elif "```" in response:
            response = response.split("```")[1].split("```")[0]

        response = response.strip()

        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse router response as JSON: {response[:200]}")
            raise ValueError(f"Invalid JSON in router response: {e}")

    def _apply_selector(self, decision: RouterDecision, selector_config) -> list:
        """Apply selector filtering to router's decision.

        Filters collections based on confidence threshold, source type, max count, etc.

        Args:
            decision: Router's raw decision
            selector_config: SelectorConfig with filtering rules

        Returns:
            List of filtered collection names
        """
        selected = decision.selected_collections

        # Filter by confidence threshold
        if selector_config.min_confidence > 0:
            filtered = [
                name for name in selected
                if decision.collection_scores.get(name, 0) >= selector_config.min_confidence
            ]
            if not filtered:
                logger.debug(f"Confidence threshold filtered all collections, falling back to original")
                filtered = selected

            selected = filtered

        # Filter by source type if specified
        if selector_config.source_types:
            filtered = [
                name for name in selected
                if self.registry.get_collection(name) and
                self.registry.get_collection(name).source_type in selector_config.source_types
            ]
            selected = filtered or selected  # Keep original if filtering removes all

        # Limit to max collections
        if len(selected) > selector_config.max_collections:
            # Keep highest confidence ones
            scored = [
                (name, decision.collection_scores.get(name, 0))
                for name in selected
            ]
            scored.sort(key=lambda x: x[1], reverse=True)
            selected = [name for name, _ in scored[:selector_config.max_collections]]

        return selected

    def get_available_collections_info(self) -> str:
        """Get human-readable info about available collections.

        Useful for debugging and documentation.

        Returns:
            Formatted text describing available collections
        """
        return self.prompt_builder.get_collection_context()
