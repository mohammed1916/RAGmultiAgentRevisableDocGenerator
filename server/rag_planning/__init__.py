"""Retrieval Planning System - Phase 1 of RAG pipeline.

Analyzes user queries and generates structured retrieval plans.
Designed to be extensible for future evaluation/re-planning phases.
"""

from .models import (
    RetrievalPlanInput,
    RetrievalPlan,
    RetrievalResult,
    Document,
    MetadataFilter,
    CollectionMetadata,
    ClarificationResponse,
)
from .planner import RetrievalPlanner
from .retriever import Retriever
from .orchestrator import RetrievalOrchestrator
from .config import CollectionRegistry

__all__ = [
    "RetrievalPlanInput",
    "RetrievalPlan",
    "RetrievalResult",
    "Document",
    "MetadataFilter",
    "CollectionMetadata",
    "ClarificationResponse",
    "RetrievalPlanner",
    "Retriever",
    "RetrievalOrchestrator",
    "CollectionRegistry",
]
