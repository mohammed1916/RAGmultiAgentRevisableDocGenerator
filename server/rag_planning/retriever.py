"""Retriever - executes retrieval plans against Milvus."""

import time
from typing import Callable, Optional, Dict, List

from .models import RetrievalPlan, RetrievalResult, Document, MetadataFilter
from ..tools import MilvusRAG
from ..base.logger import setup_logger
from ..base.exceptions import RetrievalException

logger = setup_logger(__name__)


class Retriever:
    """Executes retrieval plans against Milvus.

    Responsibilities:
    - Execute plan exactly as specified
    - Search specified collections
    - Apply metadata filters
    - Return results with metadata

    NOT responsible for:
    - Planning
    - Evaluating results
    - Re-planning
    """

    def __init__(
        self,
        rag_system: Optional[MilvusRAG] = None,
        registry: Optional["CollectionRegistry"] = None,
        on_result_callback: Optional[Callable[[RetrievalResult], None]] = None,
    ):
        """Initialize retriever with Milvus RAG system.

        Args:
            rag_system: MilvusRAG instance (creates default if None)
            registry: CollectionRegistry for logical->physical name mapping
                      (uses singleton if None)
            on_result_callback: Optional callback for result processing
                                (hook for future evaluation/re-planning stages)
        """
        from .config.collection_registry import CollectionRegistry

        self.rag = rag_system or MilvusRAG()
        self.registry = registry or CollectionRegistry()
        self.on_result_callback = on_result_callback

        logger.info(f"Retriever initialized (callback={'enabled' if on_result_callback else 'disabled'})")

    def execute(self, plan: RetrievalPlan) -> RetrievalResult:
        """Execute a retrieval plan.

        Args:
            plan: RetrievalPlan specifying what to retrieve

        Returns:
            RetrievalResult with documents and metadata

        Raises:
            RetrievalException: If retrieval fails
        """
        logger.info(
            f"Executing retrieval plan: collections={plan.collections}, "
            f"filters={len(plan.filters)}, top_k={plan.top_k}"
        )

        start_time = time.time()

        try:
            # Search specified collections
            documents = self._search_collections(plan)

            # Count per collection
            source_counts = {}
            for doc in documents:
                source_counts[doc.collection] = source_counts.get(doc.collection, 0) + 1

            execution_time_ms = (time.time() - start_time) * 1000

            result = RetrievalResult(
                plan=plan,
                documents=documents,
                total_count=len(documents),
                execution_time_ms=execution_time_ms,
                source_collections=source_counts,
            )

            logger.info(
                f"Retrieval complete: {len(documents)} documents from "
                f"{len(source_counts)} collections in {execution_time_ms:.1f}ms"
            )

            # Call callback if registered (for future evaluation/re-planning)
            if self.on_result_callback:
                try:
                    self.on_result_callback(result)
                except Exception as e:
                    logger.warning(f"Result callback failed: {e}")

            return result

        except Exception as e:
            logger.error(f"Retrieval failed: {e}")
            raise RetrievalException(f"Failed to execute retrieval plan: {e}")

    def _search_collections(self, plan: RetrievalPlan) -> List[Document]:
        """Search specified collections with filters and return documents.

        Args:
            plan: RetrievalPlan with collections and filters

        Returns:
            List of Document objects
        """
        # Translate logical/routing names (e.g. 'cbse_class_12') to physical
        # Milvus collection names (e.g. 'documents_class_12'). The planner is
        # storage-agnostic; the retriever owns this mapping.
        physical_collections = self.registry.to_physical_collections(plan.collections)
        # Reverse map to convert result collection names back to logical names
        physical_to_logical = {
            self.registry.get_collection(name).physical_collection: name
            for name in plan.collections
            if self.registry.get_collection(name)
        }

        if not physical_collections:
            logger.warning(f"No physical collections resolved for {plan.collections}")
            return []

        # Search all specified collections.
        # NOTE: metadata filters are applied post-search (see below) because
        # search_collections() does not yet accept a Milvus filter expression.
        # When it does, pass _build_filter_expression(plan.filters) through.
        raw_results = self.rag.search_collections(
            query=plan.query,
            collection_names=physical_collections,
            doc_type=None,
            top_k=plan.top_k,
        )

        # Apply metadata filtering on retrieved results
        filtered_results = self._apply_post_search_filters(raw_results, plan.filters)

        # Convert to Document objects (defensive against missing/None fields).
        # Map the physical collection name back to the logical name so results
        # stay consistent with plan.collections.
        documents = [
            Document(
                doc_id=result.get("doc_id") or "unknown",
                content=result.get("content") or "",
                collection=physical_to_logical.get(
                    result.get("collection"), result.get("collection", "unknown")
                ),
                metadata=result.get("metadata") or {},
                relevance_score=result.get("relevance_score", 0.0),
            )
            for result in filtered_results
        ]

        return documents

    @staticmethod
    def _build_filter_expression(filters: List[MetadataFilter]) -> Optional[str]:
        """Build Milvus filter expression from MetadataFilter list.

        Args:
            filters: List of filters to apply

        Returns:
            Milvus filter expression or None if no filters

        Note:
            This is a simplified version. For production, would need
            more robust Milvus expression building.
        """
        if not filters:
            return None

        expressions = [f.to_milvus_expr() for f in filters]
        valid_expressions = [e for e in expressions if e]

        if not valid_expressions:
            return None

        return " && ".join(valid_expressions)

    @staticmethod
    def _apply_post_search_filters(
        results: List[Dict],
        filters: List[MetadataFilter],
    ) -> List[Dict]:
        """Apply filters to search results (fallback for Milvus filtering).

        Args:
            results: Raw search results from Milvus
            filters: MetadataFilter list to apply

        Returns:
            Filtered results
        """
        if not filters:
            return results

        filtered = results
        for filter_obj in filters:
            filtered = [
                r for r in filtered
                if Retriever._matches_filter(r, filter_obj)
            ]

        return filtered

    @staticmethod
    def _matches_filter(result: Dict, filter_obj: MetadataFilter) -> bool:
        """Check if a result matches a filter.

        Args:
            result: Search result
            filter_obj: MetadataFilter to check

        Returns:
            True if result matches filter
        """
        metadata = result.get("metadata", {})
        field_value = metadata.get(filter_obj.field)

        if field_value is None:
            return False

        if filter_obj.operator == "eq":
            return str(field_value).lower() == str(filter_obj.value).lower()
        elif filter_obj.operator == "in":
            values = filter_obj.value if isinstance(filter_obj.value, list) else [filter_obj.value]
            return str(field_value).lower() in [str(v).lower() for v in values]
        elif filter_obj.operator == "contains":
            return str(filter_obj.value).lower() in str(field_value).lower()

        return True  # Default: accept if operator not recognized
