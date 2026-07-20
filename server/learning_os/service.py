"""In-memory implementation of the first AI-LOS storage boundary.

The public service API is deliberately storage-agnostic so a persistent repository
can replace these dictionaries without changing route behavior.
"""

from datetime import datetime, timezone
from typing import Dict, List

from .models import (
    DocumentCreate,
    LearningDocument,
    LearningProfile,
    LearningProfileCreate,
    ProfilePreferencesUpdate,
    Workspace,
    WorkspaceCreate,
)


class LearningOSService:
    """Manage learning resources while preserving profile-level isolation."""

    def __init__(self) -> None:
        self._profiles: Dict[str, LearningProfile] = {}
        self._workspaces: Dict[str, Workspace] = {}
        self._documents: Dict[str, LearningDocument] = {}

    def create_profile(self, request: LearningProfileCreate) -> LearningProfile:
        profile = LearningProfile(**request.model_dump())
        self._profiles[profile.profile_id] = profile
        return profile

    def get_profile(self, profile_id: str, user_id: str) -> LearningProfile:
        profile = self._profiles.get(profile_id)
        if profile is None or profile.user_id != user_id:
            raise KeyError("Learning profile not found")
        return profile

    def update_preferences(
        self,
        profile_id: str,
        user_id: str,
        request: ProfilePreferencesUpdate,
    ) -> LearningProfile:
        profile = self.get_profile(profile_id, user_id)
        profile.preferences.update(request.preferences)
        profile.updated_at = datetime.now(timezone.utc)
        return profile

    def create_workspace(self, request: WorkspaceCreate) -> Workspace:
        self.get_profile(request.profile_id, request.user_id)
        workspace = Workspace(**request.model_dump())
        self._workspaces[workspace.workspace_id] = workspace
        return workspace

    def get_workspace(self, workspace_id: str, user_id: str) -> Workspace:
        workspace = self._workspaces.get(workspace_id)
        if workspace is None or workspace.user_id != user_id:
            raise KeyError("Workspace not found")
        return workspace

    def create_document(self, request: DocumentCreate) -> LearningDocument:
        self.get_profile(request.profile_id, request.user_id)
        workspace = self.get_workspace(request.workspace_id, request.user_id)
        if workspace.profile_id != request.profile_id:
            raise ValueError("Workspace does not belong to the requested profile")

        document = LearningDocument(**request.model_dump())
        self._documents[document.document_id] = document
        return document

    def get_document(self, document_id: str, user_id: str) -> LearningDocument:
        document = self._documents.get(document_id)
        if document is None or document.user_id != user_id:
            raise KeyError("Document not found")
        return document

    def list_documents(self, profile_id: str, user_id: str) -> List[LearningDocument]:
        self.get_profile(profile_id, user_id)
        return [
            document
            for document in self._documents.values()
            if document.profile_id == profile_id and document.user_id == user_id
        ]
