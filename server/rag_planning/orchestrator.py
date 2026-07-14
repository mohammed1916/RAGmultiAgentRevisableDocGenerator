"""Orchestrator - coordinates planning and retrieval."""

from typing import Optional, List, Dict

from .models import RetrievalPlanInput, RetrievalResult
from .planner import RetrievalPlanner
from .retriever import Retriever
from ..tools import OllamaClient, MilvusRAG
from ..base.logger import setup_logger
from ..base.exceptions import PlanningException, RetrievalException

logger = setup_logger(__name__)


class RetrievalOrchestrator:
    """Orchestrates the complete retrieval pipeline.

    Pipeline:
    1. User query → Planner (generates RetrievalPlan)
    2. RetrievalPlan → Retriever (executes against Milvus)
    3. Results → LLM (for answer generation)

    Designed for extensibility:
    - Phase 3 (evaluation/re-planning) can be inserted by:
      - Injecting callback in Retriever
      - Creating PipelineStage subclass
      - Wrapping orchestrator with decorator
    """

    def __init__(
        self,
        llm_client: Optional[OllamaClient] = None,
        rag_system: Optional[MilvusRAG] = None,
        planner: Optional[RetrievalPlanner] = None,
        retriever: Optional[Retriever] = None,
    ):
        """Initialize orchestrator with components.

        All parameters optional - will use defaults if not provided.
        Supports dependency injection for testing.

        Args:
            llm_client: LLM client for planning
            rag_system: MilvusRAG system for retrieval
            planner: RetrievalPlanner instance
            retriever: Retriever instance
        """
        self.llm_client = llm_client or OllamaClient()
        self.rag_system = rag_system or MilvusRAG()

        self.planner = planner or RetrievalPlanner(self.llm_client)
        self.retriever = retriever or Retriever(self.rag_system)

        logger.info("RetrievalOrchestrator initialized")

    def retrieve(self, query: str, session_history: Optional[List[Dict[str, str]]] = None) -> RetrievalResult:
        """Execute complete retrieval pipeline for a query.

        Pipeline:
        1. Plan: Analyze query → RetrievalPlan
        2. Retrieve: Execute plan → RetrievalResult

        Args:
            query: User's information need
            session_history: Optional conversation history

        Returns:
            RetrievalResult with documents ready for LLM

        Raises:
            PlanningException: If planning fails
            RetrievalException: If retrieval execution fails
        """
        logger.info(f"Starting retrieval for: {query[:80]}...")

        # Phase 1: Plan
        request = RetrievalPlanInput(
            query=query,
            session_history=session_history,
        )

        try:
            plan = self.planner.plan(request)
        except PlanningException:
            raise

        # Check if clarification needed
        if plan.needs_clarification:
            logger.warning(f"Query needs clarification: {plan.clarification_questions}")
            raise PlanningException(
                f"Query is ambiguous. Please clarify: {', '.join(plan.clarification_questions or [])}"
            )

        # Phase 2: Retrieve
        try:
            result = self.retriever.execute(plan)
        except RetrievalException:
            raise

        logger.info(f"Retrieval complete: {result.total_count} documents retrieved")
        return result

    def retrieve_with_plan(self, plan_request: RetrievalPlanInput) -> RetrievalResult:
        """Execute retrieval pipeline with explicit request object.

        Variant of retrieve() that accepts RetrievalPlanInput directly.
        Useful for testing and advanced use cases.

        Args:
            plan_request: RetrievalPlanInput with all planning parameters

        Returns:
            RetrievalResult

        Raises:
            PlanningException: If planning fails
            RetrievalException: If retrieval execution fails
        """
        plan = self.planner.plan(plan_request)

        if plan.needs_clarification:
            raise PlanningException(
                f"Query needs clarification: {', '.join(plan.clarification_questions or [])}"
            )

        return self.retriever.execute(plan)

    def get_available_collections(self) -> str:
        """Get summary of available collections.

        Useful for debugging and documentation.

        Returns:
            Formatted text describing available collections
        """
        return self.planner.prompt_builder.get_collections_summary()
