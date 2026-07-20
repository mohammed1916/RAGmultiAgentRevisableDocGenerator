"""Data contracts for profile-isolated learning workspaces."""

from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


def _new_id() -> str:
    return str(uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class LearningProfileCreate(BaseModel):
    """Input required to create an isolated learning profile."""

    user_id: str = Field(min_length=1)
    name: str = Field(min_length=1, max_length=120)
    exam: Optional[str] = Field(default=None, max_length=120)
    target_date: Optional[date] = None
    daily_study_hours: float = Field(default=0.0, ge=0.0, le=24.0)
    language: str = Field(default="English", min_length=1, max_length=64)
    timezone: str = Field(default="UTC", min_length=1, max_length=64)
    preferences: Dict[str, Any] = Field(default_factory=dict)


class LearningProfile(LearningProfileCreate):
    """A learning goal and its isolated resources."""

    profile_id: str = Field(default_factory=_new_id)
    archived: bool = False
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


class ProfilePreferencesUpdate(BaseModel):
    """Partial preference update scoped to the profile owner."""

    preferences: Dict[str, Any] = Field(default_factory=dict)


class WorkspaceCreate(BaseModel):
    """Input required to create a workspace under a profile."""

    user_id: str = Field(min_length=1)
    profile_id: str = Field(min_length=1)
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=2000)
    settings: Dict[str, Any] = Field(default_factory=dict)


class Workspace(WorkspaceCreate):
    """A profile-owned document workspace."""

    workspace_id: str = Field(default_factory=_new_id)
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


class DocumentCreate(BaseModel):
    """Input required to add a knowledge artifact to a workspace."""

    user_id: str = Field(min_length=1)
    profile_id: str = Field(min_length=1)
    workspace_id: str = Field(min_length=1)
    title: str = Field(min_length=1, max_length=240)
    document_type: str = Field(default="markdown", min_length=1, max_length=64)
    content: str = ""
    subject: Optional[str] = Field(default=None, max_length=120)
    chapter: Optional[str] = Field(default=None, max_length=120)
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class LearningDocument(DocumentCreate):
    """A versioned document stored within one profile boundary."""

    document_id: str = Field(default_factory=_new_id)
    version: int = Field(default=1, ge=1)
    status: str = "draft"
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


class TaskStatusUpdate(BaseModel):
    """A task movement within a profile's learning plan."""

    status: str = Field(pattern="^(planned|in_progress|done)$")


class FlashcardReview(BaseModel):
    """A learner's self-assessed recall outcome."""

    rating: str = Field(pattern="^(again|hard|good|easy)$")


class StudyQuestion(BaseModel):
    """A profile-scoped tutoring prompt."""

    question: str = Field(min_length=1, max_length=4000)
