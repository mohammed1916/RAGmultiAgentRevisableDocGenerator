"""Pydantic models for routing system."""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class CollectionMetadata(BaseModel):
    """Metadata for a knowledge source collection."""

    name: str = Field(..., description="Unique collection name (e.g., 'cbse_class_10')")
    display_name: str = Field(..., description="Human-readable name (e.g., 'CBSE Class 10')")
    description: str = Field(..., description="Brief description of collection contents")
    source_type: str = Field(..., description="Category: 'cbse', 'jee', 'neet', 'gate', 'upsc', etc.")
    keywords: List[str] = Field(default_factory=list, description="Search keywords (e.g., ['Class 10', 'secondary'])")
    tags: List[str] = Field(default_factory=list, description="Tags for filtering (e.g., ['board', 'science'])")
    active: bool = Field(default=True, description="Whether collection is available for routing")
    document_count: Optional[int] = Field(default=None, description="Number of documents in collection")
    last_updated: Optional[str] = Field(default=None, description="ISO timestamp of last update")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Custom metadata for future extensibility")


class RouterDecision(BaseModel):
    """Router's decision for a query."""

    query: str = Field(..., description="Original user query")
    selected_collections: List[str] = Field(..., description="List of collection names to search")
    reasoning: str = Field(..., description="Explanation of routing decision")
    collection_scores: Dict[str, float] = Field(
        default_factory=dict,
        description="Confidence scores for each collection (0-1)"
    )
    fallback_collections: Optional[List[str]] = Field(
        default=None,
        description="Collections to use if selected ones return no results"
    )


class SelectorConfig(BaseModel):
    """Configuration for selection filtering."""

    min_confidence: float = Field(default=0.6, ge=0.0, le=1.0, description="Minimum confidence threshold")
    source_types: Optional[List[str]] = Field(default=None, description="Only select from these source types")
    max_collections: int = Field(default=5, ge=1, description="Maximum collections to select")
    allow_multiple: bool = Field(default=True, description="Allow multiple collections in one query")


class RouterRequest(BaseModel):
    """Request to router."""

    query: str = Field(..., description="User query")
    selector_config: Optional[SelectorConfig] = Field(default_factory=SelectorConfig, description="Selection rules")


class RouterResponse(BaseModel):
    """Response from router."""

    decision: RouterDecision = Field(..., description="Routing decision with confidence scores")
    collections_info: List[CollectionMetadata] = Field(..., description="Metadata of selected collections")
