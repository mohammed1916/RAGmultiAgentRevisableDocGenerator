"""Retrieval Planner - analyzes queries and produces retrieval plans."""

import json
from typing import Optional, List, Dict

from .models import RetrievalPlanInput, RetrievalPlan, MetadataFilter
from .planner_prompt import PlannerPromptBuilder
from .config.collection_registry import CollectionRegistry
from ..tools import OllamaClient
from ..base.logger import setup_logger
from ..base.exceptions import PlanningException

logger = setup_logger(__name__)


class RetrievalPlanner:
    """Analyzes user queries and generates retrieval plans.

    Responsibilities:
    - Understand user information need
    - Select appropriate collections
    - Identify useful metadata filters
    - Estimate result count (top_k)
    - Detect ambiguous queries

    NOT responsible for:
    - Executing retrieval
    - Evaluating results
    - Storage/index details
    """

    def __init__(
        self,
        llm_client: Optional[OllamaClient] = None,
        registry: Optional[CollectionRegistry] = None,
        prompt_builder: Optional[PlannerPromptBuilder] = None,
    ):
        """Initialize planner with dependencies.

        Args:
            llm_client: LLM client for planning (uses default if None)
            registry: Collection registry (uses singleton if None)
            prompt_builder: Prompt builder (creates new if None)
        """
        self.client = llm_client or OllamaClient()
        self.registry = registry or CollectionRegistry()
        self.prompt_builder = prompt_builder or PlannerPromptBuilder(self.registry)

        logger.info(f"RetrievalPlanner initialized with {len(self.registry.get_all_collections())} collections")

    def plan(self, request: RetrievalPlanInput) -> RetrievalPlan:
        """Generate a retrieval plan for the user's query.

        Args:
            request: Planning request with query and optional context

        Returns:
            RetrievalPlan with collections, filters, top_k, clarification info

        Raises:
            PlanningException: If planning fails
        """
        logger.info(f"Planning retrieval for query: {request.query[:80]}...")

        # Build dynamic prompt
        prompt = self.prompt_builder.build_planning_prompt(
            request.query,
            request.session_history,
        )

        # Call LLM to generate plan
        try:
            response_dict = self.client.generate(prompt, temperature=0.2, max_tokens=500)
            # Extract text response from dict
            response_text = response_dict.get("response", "") if isinstance(response_dict, dict) else response_dict
            plan_dict = self._parse_plan_response(response_text)
        except Exception as e:
            logger.error(f"Planner LLM call failed: {e}")
            raise PlanningException(f"Failed to plan retrieval: {e}")

        # Validate and construct plan
        plan = self._construct_plan(request.query, plan_dict)

        logger.info(
            f"Generated plan: collections={plan.collections}, top_k={plan.top_k}, "
            f"filters={len(plan.filters)}, needs_clarification={plan.needs_clarification}"
        )

        return plan

    @staticmethod
    def _parse_plan_response(response: str) -> dict:
        """Extract and parse JSON from LLM response.

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
            logger.error(f"Failed to parse planner response as JSON: {response[:300]}")
            raise ValueError(f"Invalid JSON in planner response: {e}")

    def _construct_plan(self, query: str, plan_dict: dict) -> RetrievalPlan:
        """Construct and validate RetrievalPlan from parsed response.

        Args:
            query: Original user query
            plan_dict: Parsed plan dictionary from LLM

        Returns:
            Validated RetrievalPlan

        Raises:
            PlanningException: If plan is invalid
        """
        # Validate collection names
        requested_collections = plan_dict.get("collections", [])
        valid_collections = self.registry.validate_collections(requested_collections)

        # When the LLM cannot confidently route to any collection, treat the
        # query as ambiguous and request clarification rather than crashing.
        # This keeps planner.plan() total (never raises on empty routing) and
        # lets the caller decide how to surface the clarification.
        if not valid_collections:
            logger.info(
                f"No valid collections routed for query (requested={requested_collections}); "
                f"flagging for clarification"
            )
            llm_questions = plan_dict.get("clarification_questions")
            return RetrievalPlan(
                query=query,
                collections=[],
                filters=[],
                top_k=max(1, min(100, plan_dict.get("top_k", 5))),
                needs_clarification=True,
                clarification_questions=llm_questions or [
                    "Which exam or class is this for (e.g., CBSE Class 10, CBSE Class 12, JEE)?"
                ],
                reasoning=plan_dict.get("reasoning", "Query was too ambiguous to route to a collection."),
                confidence=max(0.0, min(1.0, plan_dict.get("confidence", 0.3))),
            )

        # Validate and construct filters
        filters = []
        for filter_dict in plan_dict.get("filters", []):
            try:
                # Validate metadata field exists in at least one selected collection
                field = filter_dict.get("field")
                valid_for_any = any(
                    self.registry.validate_metadata_filter(col, field)
                    for col in valid_collections
                )

                if not valid_for_any:
                    logger.warning(f"Filter field '{field}' not found in selected collections, skipping")
                    continue

                filters.append(MetadataFilter(**filter_dict))
            except Exception as e:
                logger.warning(f"Failed to construct filter {filter_dict}: {e}, skipping")

        # Construct final plan
        try:
            plan = RetrievalPlan(
                query=query,
                collections=valid_collections,
                filters=filters,
                top_k=max(1, min(100, plan_dict.get("top_k", 5))),  # Clamp 1-100
                needs_clarification=plan_dict.get("needs_clarification", False),
                clarification_questions=plan_dict.get("clarification_questions"),
                reasoning=plan_dict.get("reasoning", "No reasoning provided"),
                confidence=max(0.0, min(1.0, plan_dict.get("confidence", 0.8))),  # Clamp 0-1
            )
            return plan
        except Exception as e:
            logger.error(f"Failed to construct RetrievalPlan: {e}")
            raise PlanningException(f"Invalid plan structure: {e}")
