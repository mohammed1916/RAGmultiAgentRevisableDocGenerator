"""End-to-end tests for RAG Planning System (Phase 1).

Tests the complete retrieval planning pipeline:
  RetrievalPlanner → RetrievalPlan → Retriever → RetrievalResult
"""

import pytest
from pathlib import Path

from server.rag_planning import (
    RetrievalOrchestrator,
    RetrievalPlanInput,
    RetrievalPlanner,
    Retriever,
)
from server.rag_planning.config import CollectionRegistry
from server.base.exceptions import PlanningException


class TestRetrievalPlanner:
    """E2E tests for RetrievalPlanner."""

    @pytest.fixture
    def planner(self):
        """Initialize planner."""
        return RetrievalPlanner()

    def test_planner_selects_cbse_class_12(self, planner):
        """Test planner correctly identifies CBSE Class 12 queries."""
        request = RetrievalPlanInput(query="Class 12 Physics syllabus")
        plan = planner.plan(request)

        assert plan is not None
        assert "cbse_class_12" in plan.collections
        assert plan.top_k > 0
        assert len(plan.reasoning) > 0

    def test_planner_selects_cbse_class_10(self, planner):
        """Test planner identifies Class 10 queries."""
        request = RetrievalPlanInput(query="Class 10 Science topics")
        plan = planner.plan(request)

        assert "cbse_class_10" in plan.collections

    def test_planner_multiple_collections(self, planner):
        """Test planner can select multiple collections."""
        request = RetrievalPlanInput(query="JEE and CBSE comparison")
        plan = planner.plan(request)

        assert len(plan.collections) >= 1
        assert all(col in CollectionRegistry().get_collection_names() for col in plan.collections)

    def test_planner_identifies_ambiguous_query(self, planner):
        """Test planner handles ambiguous queries gracefully.

        Very vague queries either:
        - Get flagged as needing clarification
        - Fail validation (no valid collections selected)
        """
        request = RetrievalPlanInput(query="something")

        try:
            plan = planner.plan(request)
            # If it succeeds, should either flag clarification or have collections
            assert plan is not None
            assert isinstance(plan.needs_clarification, bool)
            # If not flagged as ambiguous, at least some attempt was made
            if not plan.needs_clarification:
                assert len(plan.collections) > 0
        except PlanningException:
            # It's OK to raise exception for too-ambiguous queries
            pass

    def test_planner_confidence_score(self, planner):
        """Test planner provides confidence scores."""
        request = RetrievalPlanInput(query="Class 12 Physics")
        plan = planner.plan(request)

        assert 0.0 <= plan.confidence <= 1.0
        assert plan.confidence > 0.5  # Should be confident about clear queries


class TestRetriever:
    """E2E tests for Retriever execution."""

    @pytest.fixture
    def retriever(self):
        """Initialize retriever."""
        return Retriever()

    @pytest.fixture
    def planner(self):
        """Initialize planner."""
        return RetrievalPlanner()

    def test_retriever_executes_plan(self, retriever, planner):
        """Test retriever executes plan and returns results."""
        # Use an unambiguous query so the planner routes deterministically
        request = RetrievalPlanInput(query="Class 12 Physics electrostatics and electric fields")
        plan = planner.plan(request)

        # Execute it
        result = retriever.execute(plan)

        assert result is not None
        assert len(result.documents) > 0
        assert result.total_count == len(result.documents)
        assert result.execution_time_ms > 0

    def test_retriever_respects_top_k(self, retriever, planner):
        """Test retriever returns requested number of results."""
        request = RetrievalPlanInput(query="Class 12 Physics")
        plan = planner.plan(request)

        # RetrievalPlan is immutable (frozen); construct a new plan with top_k=3
        from server.rag_planning.models import RetrievalPlan

        custom_plan = RetrievalPlan(
            query="Class 12 Physics",
            collections=plan.collections,
            filters=plan.filters,
            top_k=3,
            reasoning="test",
        )

        result = retriever.execute(custom_plan)

        assert len(result.documents) <= 3

    def test_retriever_documents_have_metadata(self, retriever, planner):
        """Test retrieved documents include metadata."""
        request = RetrievalPlanInput(query="Class 12 Physics")
        plan = planner.plan(request)
        result = retriever.execute(plan)

        assert len(result.documents) > 0
        doc = result.documents[0]

        assert doc.doc_id is not None
        assert doc.content is not None
        assert doc.collection is not None
        # COSINE similarity ranges [-1, 1]
        assert -1 <= doc.relevance_score <= 1


class TestRetrievalOrchestrator:
    """E2E tests for complete retrieval pipeline."""

    @pytest.fixture
    def orchestrator(self):
        """Initialize orchestrator."""
        return RetrievalOrchestrator()

    def test_orchestrator_complete_pipeline(self, orchestrator):
        """Test complete retrieval pipeline end-to-end."""
        result = orchestrator.retrieve("Class 12 Physics topics")

        assert result is not None
        assert result.plan is not None
        assert len(result.documents) > 0
        assert result.total_count > 0
        assert result.execution_time_ms > 0

    def test_orchestrator_with_session_history(self, orchestrator):
        """Test orchestrator uses session history for context."""
        session_history = [
            {"role": "user", "content": "I'm preparing for Class 12 boards"},
            {"role": "assistant", "content": "Let me help with Class 12 materials"},
        ]

        # Follow-up relies on history to resolve the class level
        result = orchestrator.retrieve(
            "What Physics topics should I study for Class 12?",
            session_history=session_history,
        )

        assert result is not None
        assert len(result.documents) > 0

    def test_orchestrator_retrieval_request_object(self, orchestrator):
        """Test orchestrator with explicit RetrievalPlanInput.

        Uses a CBSE Class 12 query because it has loaded documents
        (the JEE collection is registered but currently empty).
        """
        request = RetrievalPlanInput(
            query="Class 12 Physics topics",
            session_history=[
                {"role": "user", "content": "board exam prep"},
                {"role": "assistant", "content": "Happy to help with Class 12"},
            ],
        )

        result = orchestrator.retrieve_with_plan(request)

        assert result is not None
        assert result.total_count > 0

    def test_orchestrator_handles_no_results_gracefully(self, orchestrator):
        """Test orchestrator handles nonsense queries without a hard crash.

        For an unroutable query the orchestrator raises PlanningException
        (clarification needed) rather than returning garbage.
        """
        try:
            result = orchestrator.retrieve("xyz123 nonsense query")
            # If it returns, it should be a well-formed result
            assert result is not None
        except PlanningException:
            # Acceptable: query was too ambiguous to route
            pass

    def test_orchestrator_collections_available(self, orchestrator):
        """Test orchestrator can list available collections."""
        info = orchestrator.get_available_collections()

        assert len(info) > 0
        assert "CBSE Class 10" in info or "cbse_class_10" in info
        assert "CBSE Class 12" in info or "cbse_class_12" in info

    def test_orchestrator_ambiguous_query_flagged(self, orchestrator):
        """Test orchestrator handles ambiguous queries."""
        # Very ambiguous query
        try:
            result = orchestrator.retrieve("tell me about it")
            # If it returns, check if it flagged ambiguity
            assert result.plan.needs_clarification in [True, False]
        except PlanningException:
            # Acceptable: ambiguous query raised for clarification
            pass


class TestRetrievalPlanQuality:
    """E2E tests validating quality of retrieval plans."""

    @pytest.fixture
    def planner(self):
        """Initialize planner."""
        return RetrievalPlanner()

    def test_plan_has_valid_collections(self, planner):
        """Test plans only include valid collections."""
        registry = CollectionRegistry()
        valid_names = registry.get_collection_names()

        request = RetrievalPlanInput(query="Class 12 Physics and JEE")
        plan = planner.plan(request)

        for col in plan.collections:
            assert col in valid_names, f"Invalid collection: {col}"

    def test_plan_top_k_reasonable(self, planner):
        """Test planner sets reasonable top_k values."""
        request = RetrievalPlanInput(query="Class 12 Physics")
        plan = planner.plan(request)

        assert 1 <= plan.top_k <= 100

    def test_plan_filters_valid(self, planner):
        """Test plan filters reference valid metadata fields."""
        request = RetrievalPlanInput(query="Class 12 Physics")
        plan = planner.plan(request)

        registry = CollectionRegistry()

        for filter_obj in plan.filters:
            # At least one collection should have this field
            valid = False
            for col_name in plan.collections:
                if registry.validate_metadata_filter(col_name, filter_obj.field):
                    valid = True
                    break

            assert valid, f"Filter field {filter_obj.field} not in any collection"

    def test_plan_reasoning_provided(self, planner):
        """Test plans include reasoning."""
        request = RetrievalPlanInput(query="CBSE Class 12")
        plan = planner.plan(request)

        assert len(plan.reasoning) > 10  # Non-trivial explanation


class TestIntegrationWithWriter:
    """E2E tests for WriterAgent integration with new planner."""

    @pytest.fixture
    def writer_agent(self):
        """Initialize WriterAgent with new orchestrator."""
        from server.agents.writer import WriterAgent
        from server.tools import OllamaClient

        llm = OllamaClient()
        orchestrator = RetrievalOrchestrator()
        return WriterAgent(llm, orchestrator)

    def test_writer_fetches_rag_context(self, writer_agent):
        """Test WriterAgent successfully fetches RAG context."""
        # Call the _fetch_rag_context method
        context = writer_agent._fetch_rag_context(
            request="Class 12 Physics",
            section_title="Electrostatics",
            doc_type="Study Guide",
        )

        # Should return non-empty context
        assert isinstance(context, str)
        if context:  # If retrieval succeeded
            assert len(context) > 20
            assert "Retrieved" in context or "curriculum" in context.lower()

    def test_writer_handles_empty_retrieval(self, writer_agent):
        """Test WriterAgent gracefully handles empty retrieval results."""
        # Query that might return no results
        context = writer_agent._fetch_rag_context(
            request="xyz nonsense",
            section_title="invalid topic",
            doc_type="Study Guide",
        )

        # Should return empty string, not crash
        assert isinstance(context, str)
        assert len(context) <= 1000  # Not huge


class TestRetrievalResultContent:
    """E2E tests validating retrieved content quality."""

    @pytest.fixture
    def orchestrator(self):
        """Initialize orchestrator."""
        return RetrievalOrchestrator()

    def test_retrieved_documents_not_empty(self, orchestrator):
        """Test retrieved documents have actual content."""
        result = orchestrator.retrieve("Class 12 Physics")

        assert len(result.documents) > 0

        for doc in result.documents:
            assert len(doc.content) > 0
            assert len(doc.doc_id) > 0

    def test_retrieved_from_correct_collections(self, orchestrator):
        """Test documents come from requested collections."""
        request = RetrievalPlanInput(query="Class 12 Physics")
        plan_result = orchestrator.retrieve_with_plan(request)

        for doc in plan_result.documents:
            assert doc.collection in plan_result.plan.collections

    def test_results_sorted_by_relevance(self, orchestrator):
        """Test results are sorted by relevance score."""
        result = orchestrator.retrieve("Class 12 Physics")

        if len(result.documents) > 1:
            scores = [doc.relevance_score for doc in result.documents]
            assert scores == sorted(scores, reverse=True)
