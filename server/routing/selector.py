"""Collection selector - applies filtering rules to routing decisions."""

from typing import List, Dict, Optional

from .models import RouterDecision, SelectorConfig, CollectionMetadata
from .config.collection_registry import CollectionRegistry
from ..base.logger import setup_logger

logger = setup_logger(__name__)


class CollectionSelector:
    """Applies filtering rules to router decisions.

    Responsibilities:
    - Filter by confidence threshold
    - Filter by source type
    - Limit maximum number of collections
    - Apply custom selection rules
    - Handle fallbacks
    """

    def __init__(self, registry: Optional[CollectionRegistry] = None):
        """Initialize selector.

        Args:
            registry: CollectionRegistry instance (uses singleton if None)
        """
        self.registry = registry or CollectionRegistry()

    def select(
        self,
        decision: RouterDecision,
        config: SelectorConfig,
    ) -> List[str]:
        """Apply selection rules to router's decision.

        Args:
            decision: Raw router decision with confidence scores
            config: Selection configuration with filtering rules

        Returns:
            List of selected collection names after filtering
        """
        selected = list(decision.selected_collections)
        original_count = len(selected)

        # Step 1: Filter by confidence threshold
        selected = self._filter_by_confidence(selected, decision.collection_scores, config.min_confidence)
        if not selected:
            logger.debug("Confidence filter removed all collections, resetting to original")
            selected = list(decision.selected_collections)

        # Step 2: Filter by source type
        if config.source_types:
            selected = self._filter_by_source_type(selected, config.source_types)
            if not selected:
                logger.debug("Source type filter removed all collections, resetting")
                selected = list(decision.selected_collections)

        # Step 3: Limit to max collections
        if len(selected) > config.max_collections:
            selected = self._limit_by_confidence(selected, decision.collection_scores, config.max_collections)

        logger.info(f"Selection filter: {original_count} → {len(selected)} collections")
        return selected

    @staticmethod
    def _filter_by_confidence(
        selected: List[str],
        scores: Dict[str, float],
        min_confidence: float,
    ) -> List[str]:
        """Filter collections by confidence threshold.

        Args:
            selected: List of selected collection names
            scores: Confidence scores per collection
            min_confidence: Minimum confidence threshold (0-1)

        Returns:
            Filtered list of collection names
        """
        if min_confidence <= 0:
            return selected

        filtered = [
            name for name in selected
            if scores.get(name, 0) >= min_confidence
        ]

        if len(filtered) < len(selected):
            removed = [name for name in selected if name not in filtered]
            logger.debug(f"Confidence threshold ({min_confidence:.2f}) removed: {removed}")

        return filtered

    def _filter_by_source_type(self, selected: List[str], source_types: List[str]) -> List[str]:
        """Filter collections by source type.

        Args:
            selected: List of selected collection names
            source_types: Allowed source types

        Returns:
            Filtered list of collection names
        """
        filtered = []

        for name in selected:
            col = self.registry.get_collection(name)
            if col and col.source_type in source_types:
                filtered.append(name)
            else:
                logger.debug(f"Filtered out {name} (not in source types: {source_types})")

        return filtered

    @staticmethod
    def _limit_by_confidence(
        selected: List[str],
        scores: Dict[str, float],
        max_collections: int,
    ) -> List[str]:
        """Limit collections to max count, keeping highest confidence ones.

        Args:
            selected: List of selected collection names
            scores: Confidence scores per collection
            max_collections: Maximum number of collections to keep

        Returns:
            Limited list of collection names
        """
        if len(selected) <= max_collections:
            return selected

        # Sort by confidence (descending)
        scored = [
            (name, scores.get(name, 0))
            for name in selected
        ]
        scored.sort(key=lambda x: x[1], reverse=True)

        selected_names = [name for name, _ in scored[:max_collections]]
        removed = [name for name in selected if name not in selected_names]

        logger.debug(f"Limited to {max_collections} collections, removed: {removed}")
        return selected_names

    def should_use_fallback(self, retrieval_results: Optional[List], decision: RouterDecision) -> bool:
        """Determine if fallback collections should be used.

        Fallback is triggered when:
        - Primary collections returned no results
        - Fallback collections are defined in decision

        Args:
            retrieval_results: Results from primary retrieval
            decision: Router decision with fallback_collections

        Returns:
            True if fallback should be used
        """
        if not decision.fallback_collections:
            return False

        if retrieval_results is None or len(retrieval_results) == 0:
            logger.info("Retrieval returned no results, using fallback collections")
            return True

        return False
