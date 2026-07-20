"""Pydantic models for retrieval planning system."""

from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional, Literal
from datetime import datetime


class CollectionMetadata(BaseModel):
    """Metadata for a knowledge source collection."""

    name: str = Field(..., description="Logical/semantic collection identifier used for routing (e.g. 'cbse_class_12')")
    display_name: str = Field(..., description="Human-readable name")
    description: str = Field(..., description="What this collection contains")
    milvus_collection: Optional[str] = Field(
        default=None,
        description="Physical Milvus collection name. Defaults to `name` if not set. "
        "Decouples routing/semantic names from storage names.",
    )
    document_count: Optional[int] = Field(default=None, description="Number of documents")
    metadata_fields: Dict[str, str] = Field(
        default_factory=dict,
        description="Available metadata fields and their types (e.g., {'subject': 'string', 'difficulty': 'string'})",
    )

    @property
    def physical_collection(self) -> str:
        """Physical Milvus collection name (falls back to logical name)."""
        return self.milvus_collection or self.name


class MetadataFilter(BaseModel):
    """A metadata filter to apply during retrieval."""

    field: str = Field(..., description="Metadata field name")
    value: Any = Field(..., description="Filter value (supports string, list, numeric)")
    operator: Literal["eq", "in", "contains", "gte", "lte"] = Field(
        default="eq", description="Filter operator"
    )

    def to_milvus_expr(self) -> str:
        """Convert to Milvus filter expression.

        Returns:
            Milvus-compatible filter expression string
        """
        if self.operator == "eq":
            if isinstance(self.value, str):
                return f'metadata like "%{self.field}:{self.value}%"'
            return f"metadata[{self.field}] == {self.value}"
        elif self.operator == "in":
            if isinstance(self.value, list):
                values_str = " || ".join(f'metadata like "%{self.field}:{v}%"' for v in self.value)
                return f"({values_str})"
        elif self.operator == "contains":
            return f'metadata like "%{self.field}%{self.value}%"'
        # Add more operators as needed
        return ""


class RetrievalPlanInput(BaseModel):
    """Input to the retrieval planner."""

    query: str = Field(..., description="User's information need/question")
    session_history: Optional[List[Dict[str, str]]] = Field(
        default=None,
        description="Conversation history [{role: 'user'|'assistant', content: str}]",
    )
    user_context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional user profile/preferences {level: 'beginner'|'intermediate'|'advanced', ...}",
    )


class RetrievalPlan(BaseModel):
    """Structured retrieval plan output by planner.

    This is the contract between planner and retriever.
    Storage-agnostic - pure information about what to retrieve.
    """

    query: str = Field(..., description="Original query")
    collections: List[str] = Field(..., description="Collection names to search")
    filters: List[MetadataFilter] = Field(default_factory=list, description="Metadata filters to apply")
    top_k: int = Field(default=5, ge=1, le=100, description="Number of results to retrieve")
    needs_clarification: bool = Field(
        default=False, description="Whether user query needs clarification"
    )
    clarification_questions: Optional[List[str]] = Field(
        default=None, description="Questions to ask user if needs_clarification=true"
    )
    reasoning: str = Field(..., description="Explanation of planning decisions")
    confidence: float = Field(
        default=0.8, ge=0.0, le=1.0, description="Planner's confidence in this plan (0-1)"
    )

    class Config:
        frozen = True  # Immutable - plans should not change after creation


class Document(BaseModel):
    """A retrieved document."""

    doc_id: str = Field(..., description="Unique document identifier")
    content: str = Field(..., description="Document content")
    collection: str = Field(..., description="Source collection name")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Document metadata")
    relevance_score: float = Field(
        default=0.0,
        description="Relevance score from search. COSINE similarity ranges [-1, 1]; higher is more relevant.",
    )


class RetrievalResult(BaseModel):
    """Result of executing a retrieval plan.

    Designed to be extensible for future evaluation/re-planning phases.
    """

    plan: RetrievalPlan = Field(..., description="The plan that was executed")
    documents: List[Document] = Field(..., description="Retrieved documents")
    total_count: int = Field(..., description="Total documents retrieved")
    execution_time_ms: float = Field(..., description="Time taken to retrieve (milliseconds)")
    source_collections: Dict[str, int] = Field(
        default_factory=dict, description="Document count per collection {collection: count}"
    )

    # Extension fields for Phase 3 (future evaluator)
    evaluation_metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="Metadata added by evaluation stage (Phase 3)"
    )

    class Config:
        frozen = False  # Mutable for Phase 3 to add evaluation data


class ClarificationResponse(BaseModel):
    """User's response to clarification questions."""

    original_query: str = Field(...)
    clarification_answers: Dict[str, str] = Field(..., description="Question -> Answer mapping")
    refined_query: Optional[str] = Field(
        default=None, description="Refined query after clarification"
    )
