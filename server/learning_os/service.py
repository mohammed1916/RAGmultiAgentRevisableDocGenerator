"""Profile-isolated application service for the AI Learning OS MVP.

State is persisted through :class:`LearningRepository` (SQLite) so profiles,
documents, tasks, flashcards and memories survive restarts. The public methods
below are the stable contract the API depends on; the storage backend can change
without touching the API layer.
"""

from datetime import date, datetime, timedelta, timezone
import os
from typing import Any, Dict, List, Optional

import requests

from ..agents.knowledge_graph import KnowledgeGraphAgent
from ..base.logger import setup_logger
from ..config import config
from .models import (
    DocumentCreate,
    LearningDocument,
    LearningProfile,
    LearningProfileCreate,
    ProfilePreferencesUpdate,
    Workspace,
    WorkspaceCreate,
)
from .repository import LearningRepository

logger = setup_logger(__name__)


class LearningOSService:
    """Manage learning resources while preserving profile-level isolation.

    All reads/writes go through the repository. Domain objects are Pydantic
    models serialized to JSON for storage and rehydrated on read, so validation
    still runs on the way in.
    """

    def __init__(
        self,
        repository: Optional[LearningRepository] = None,
        llm_client: Optional[Any] = None,
    ) -> None:
        self._repo = repository or LearningRepository()
        # Shared LLM client (optional) used by the knowledge-graph agent.
        self._graph_agent = KnowledgeGraphAgent(llm_client=llm_client)

    # ---------------------------------------------------------------- profiles

    def create_profile(self, request: LearningProfileCreate) -> LearningProfile:
        profile = LearningProfile(**request.model_dump())
        self._repo.upsert_entity(
            "profiles",
            profile.profile_id,
            profile.model_dump(mode="json"),
            user_id=profile.user_id,
        )
        # Initialise empty per-profile collections.
        for kind in ("subjects", "tasks", "flashcards", "memories"):
            self._repo.set_collection(kind, profile.profile_id, [])
        return profile

    def list_profiles(self, user_id: str) -> List[LearningProfile]:
        return [LearningProfile(**data) for data in self._repo.list_by_user("profiles", user_id)]

    def get_profile(self, profile_id: str, user_id: str) -> LearningProfile:
        data = self._repo.get_entity("profiles", profile_id)
        if data is None or data.get("user_id") != user_id:
            raise KeyError("Learning profile not found")
        return LearningProfile(**data)

    def update_preferences(
        self,
        profile_id: str,
        user_id: str,
        request: ProfilePreferencesUpdate,
    ) -> LearningProfile:
        profile = self.get_profile(profile_id, user_id)
        profile.preferences.update(request.preferences)
        profile.updated_at = datetime.now(timezone.utc)
        self._repo.upsert_entity(
            "profiles", profile.profile_id, profile.model_dump(mode="json"), user_id=user_id
        )
        return profile

    def archive_profile(self, profile_id: str, user_id: str, archived: bool = True) -> LearningProfile:
        """Soft-delete: mark a profile archived without destroying its data."""
        profile = self.get_profile(profile_id, user_id)
        profile.archived = archived
        profile.updated_at = datetime.now(timezone.utc)
        self._repo.upsert_entity(
            "profiles", profile.profile_id, profile.model_dump(mode="json"), user_id=user_id
        )
        return profile

    def delete_profile(self, profile_id: str, user_id: str) -> None:
        """Hard-delete a profile and all data scoped to it (owner-checked)."""
        self.get_profile(profile_id, user_id)  # raises KeyError if not owner
        self._repo.delete_profile_cascade(profile_id)

    # -------------------------------------------------------------- workspaces

    def create_workspace(self, request: WorkspaceCreate) -> Workspace:
        self.get_profile(request.profile_id, request.user_id)
        workspace = Workspace(**request.model_dump())
        self._repo.upsert_entity(
            "workspaces",
            workspace.workspace_id,
            workspace.model_dump(mode="json"),
            user_id=workspace.user_id,
            profile_id=workspace.profile_id,
        )
        return workspace

    def get_workspace(self, workspace_id: str, user_id: str) -> Workspace:
        data = self._repo.get_entity("workspaces", workspace_id)
        if data is None or data.get("user_id") != user_id:
            raise KeyError("Workspace not found")
        return Workspace(**data)

    # --------------------------------------------------------------- documents

    def create_document(self, request: DocumentCreate) -> LearningDocument:
        self.get_profile(request.profile_id, request.user_id)
        workspace = self.get_workspace(request.workspace_id, request.user_id)
        if workspace.profile_id != request.profile_id:
            raise ValueError("Workspace does not belong to the requested profile")
        document = LearningDocument(**request.model_dump())
        self._repo.upsert_entity(
            "documents",
            document.document_id,
            document.model_dump(mode="json"),
            user_id=document.user_id,
            profile_id=document.profile_id,
        )
        # Content changed -> the derived knowledge graph is stale.
        self._repo.delete_collection("graph", document.profile_id)
        return document

    def get_document(self, document_id: str, user_id: str) -> LearningDocument:
        data = self._repo.get_entity("documents", document_id)
        if data is None or data.get("user_id") != user_id:
            raise KeyError("Document not found")
        return LearningDocument(**data)

    def update_document(self, document_id: str, user_id: str, content: str) -> LearningDocument:
        document = self.get_document(document_id, user_id)
        document.content = content
        document.version += 1
        document.updated_at = datetime.now(timezone.utc)
        self._repo.upsert_entity(
            "documents",
            document.document_id,
            document.model_dump(mode="json"),
            user_id=document.user_id,
            profile_id=document.profile_id,
        )
        self._repo.delete_collection("graph", document.profile_id)
        return document

    def list_documents(self, profile_id: str, user_id: str) -> List[LearningDocument]:
        self.get_profile(profile_id, user_id)
        return [
            LearningDocument(**data)
            for data in self._repo.list_documents(profile_id, user_id)
        ]

    # -------------------------------------------------------------- demo data

    def ensure_demo_data(self, user_id: str) -> List[LearningProfile]:
        """Create a rich starter workspace once, then return the user's profiles."""
        if self._repo.has_profiles(user_id):
            return self.list_profiles(user_id)

        boards = self.create_profile(
            LearningProfileCreate(
                user_id=user_id,
                name="Class 12 Boards",
                exam="CBSE Boards",
                target_date=date.today() + timedelta(days=154),
                daily_study_hours=3.5,
                timezone="Asia/Kolkata",
                preferences={"revision_strategy": "spaced", "focus": "Physics"},
            )
        )
        jee = self.create_profile(
            LearningProfileCreate(
                user_id=user_id,
                name="JEE Preparation",
                exam="JEE Main",
                target_date=date.today() + timedelta(days=206),
                daily_study_hours=2.0,
                timezone="Asia/Kolkata",
                preferences={"revision_strategy": "spaced", "focus": "Problem solving"},
            )
        )
        self._repo.set_collection("subjects", boards.profile_id, [
            {"name": "Physics", "progress": 68, "mastery": 0.72, "color": "#06b6d4"},
            {"name": "Chemistry", "progress": 51, "mastery": 0.58, "color": "#f97316"},
            {"name": "Mathematics", "progress": 44, "mastery": 0.49, "color": "#8b5cf6"},
        ])
        self._repo.set_collection("subjects", jee.profile_id, [
            {"name": "Physics", "progress": 33, "mastery": 0.42, "color": "#06b6d4"},
            {"name": "Chemistry", "progress": 27, "mastery": 0.35, "color": "#f97316"},
            {"name": "Mathematics", "progress": 39, "mastery": 0.44, "color": "#8b5cf6"},
        ])
        workspace = self.create_workspace(
            WorkspaceCreate(user_id=user_id, profile_id=boards.profile_id, name="Physics workspace")
        )
        self.create_document(
            DocumentCreate(
                user_id=user_id,
                profile_id=boards.profile_id,
                workspace_id=workspace.workspace_id,
                title="Current Electricity - revision note",
                subject="Physics",
                chapter="Current Electricity",
                tags=["revision", "formula"],
                content=(
                    "# Current Electricity\n\n"
                    "## Ohm's law\n\nFor an ohmic conductor at constant temperature, `V = IR`.\n\n"
                    "## Resistance and resistivity\n\n`R = rho L / A`. Resistivity is a material property; resistance also depends on geometry.\n\n"
                    "## Revision prompt\n\nExplain why resistance changes with temperature and solve one Kirchhoff loop."
                ),
            )
        )
        self.create_document(
            DocumentCreate(
                user_id=user_id,
                profile_id=boards.profile_id,
                workspace_id=workspace.workspace_id,
                title="Electrostatics concept map",
                subject="Physics",
                chapter="Electrostatics",
                tags=["concept", "prerequisite"],
                content="# Electrostatics\n\nElectric charge -> electric field -> potential -> capacitance.",
            )
        )
        self._repo.set_collection("tasks", boards.profile_id, [
            {"id": "boards-physics", "title": "Physics", "parent": "Prepare for Boards", "status": "in_progress", "estimate": "4.5 h", "priority": "high"},
            {"id": "boards-electrostatics", "title": "Revise Electrostatics", "parent": "Physics", "status": "done", "estimate": "45 min", "priority": "medium"},
            {"id": "boards-current", "title": "Practice Kirchhoff loops", "parent": "Physics", "status": "in_progress", "estimate": "60 min", "priority": "high"},
            {"id": "boards-chemistry", "title": "Organic chemistry reaction sheet", "parent": "Chemistry", "status": "planned", "estimate": "50 min", "priority": "medium"},
            {"id": "boards-maths", "title": "Definite integrals mixed set", "parent": "Mathematics", "status": "planned", "estimate": "75 min", "priority": "high"},
        ])
        self._repo.set_collection("tasks", jee.profile_id, [
            {"id": "jee-mechanics", "title": "Mechanics problem set", "parent": "JEE Preparation", "status": "in_progress", "estimate": "90 min", "priority": "high"},
            {"id": "jee-algebra", "title": "Revise complex numbers", "parent": "Mathematics", "status": "planned", "estimate": "50 min", "priority": "medium"},
        ])
        self._repo.set_collection("flashcards", boards.profile_id, [
            {"id": "card-ohm", "front": "State Ohm's law.", "back": "At constant temperature, potential difference is proportional to current: V = IR.", "due": date.today().isoformat(), "stability": 4.2, "difficulty": 5.1, "reps": 4},
            {"id": "card-resistivity", "front": "How does resistance depend on geometry?", "back": "R = rho L / A, so it increases with length and decreases with cross-sectional area.", "due": date.today().isoformat(), "stability": 2.7, "difficulty": 6.0, "reps": 2},
        ])
        self._repo.set_collection("memories", boards.profile_id, [
            {"text": "Learner benefits from worked numerical examples before abstraction.", "importance": 0.8},
            {"text": "Kirchhoff loop questions have needed repeated practice.", "importance": 0.9},
        ])
        # Derive the knowledge graph from the seeded chapters. Best-effort here so
        # demo setup still succeeds if the LLM is momentarily unavailable; the
        # dashboard refresh endpoint can rebuild it on demand.
        try:
            self._build_and_store_graph(boards.profile_id)
        except Exception as error:
            logger.warning("Demo knowledge-graph build deferred: %s", error)
        return [boards, jee]

    # ------------------------------------------------------------- dashboards

    def dashboard(self, profile_id: str, user_id: str) -> Dict[str, Any]:
        profile = self.get_profile(profile_id, user_id)
        documents = self.list_documents(profile_id, user_id)
        tasks = self._repo.get_collection("tasks", profile_id)
        cards = self._repo.get_collection("flashcards", profile_id)
        subjects = self._repo.get_collection("subjects", profile_id)
        due_cards = [card for card in cards if card["due"] <= date.today().isoformat()]
        completed = sum(task["status"] == "done" for task in tasks)
        return {
            "profile": profile.model_dump(mode="json"),
            "subjects": subjects,
            "documents": [document.model_dump(mode="json") for document in documents],
            "tasks": tasks,
            "flashcards": due_cards,
            "memories": self._repo.get_collection("memories", profile_id),
            "analytics": {
                "study_minutes_this_week": 612 if profile.name == "Class 12 Boards" else 330,
                "streak": 8 if profile.name == "Class 12 Boards" else 4,
                "tasks_completed": completed,
                "task_total": len(tasks),
                "review_due": len(due_cards),
                "activity": [
                    {"day": "Mon", "minutes": 55}, {"day": "Tue", "minutes": 82},
                    {"day": "Wed", "minutes": 74}, {"day": "Thu", "minutes": 96},
                    {"day": "Fri", "minutes": 64}, {"day": "Sat", "minutes": 121},
                    {"day": "Sun", "minutes": 120},
                ],
            },
            "graph": self._graph_payload(profile_id),
        }

    def _graph_payload(self, profile_id: str) -> Dict[str, Any]:
        """Return the profile's cached knowledge graph for the dashboard.

        The dashboard is a read path, so it never triggers an LLM call: it serves
        the persisted graph, or an empty graph if one has not been built yet.
        Graphs are (re)built at document-write time and via ``refresh_graph``.
        There is no hardcoded fallback.
        """
        cached = self._repo.get_collection("graph", profile_id)
        if cached:
            # get_collection returns a list; the graph is stored as a single item.
            return cached[0]
        return {"nodes": [], "edges": []}

    def refresh_graph(self, profile_id: str, user_id: str) -> Dict[str, Any]:
        """Force a rebuild of the knowledge graph for a profile."""
        self.get_profile(profile_id, user_id)
        return self._build_and_store_graph(profile_id)

    def _build_and_store_graph(self, profile_id: str) -> Dict[str, Any]:
        subjects = self._repo.get_collection("subjects", profile_id)
        documents = self._repo.get_documents_by_profile(profile_id)
        graph = self._graph_agent.build(subjects=subjects, documents=documents)
        # Only cache a non-empty graph so we retry derivation once content exists.
        if graph.get("nodes"):
            self._repo.set_collection("graph", profile_id, [graph])
        return graph

    # ---------------------------------------------------------------- search

    def search(self, profile_id: str, user_id: str, query: str) -> List[Dict[str, Any]]:
        query_terms = {term for term in query.lower().split() if len(term) > 1}
        results = []
        for document in self.list_documents(profile_id, user_id):
            haystack = " ".join([document.title, document.content, " ".join(document.tags)]).lower()
            score = sum(term in haystack for term in query_terms)
            if score:
                results.append({
                    "document_id": document.document_id,
                    "title": document.title,
                    "subject": document.subject,
                    "chapter": document.chapter,
                    "excerpt": document.content[:280],
                    "score": round(score / max(1, len(query_terms)), 2),
                })
        return sorted(results, key=lambda item: item["score"], reverse=True)

    # ---------------------------------------------------------- tasks / cards

    def update_task_status(self, profile_id: str, user_id: str, task_id: str, status: str) -> Dict[str, Any]:
        self.get_profile(profile_id, user_id)
        tasks = self._repo.get_collection("tasks", profile_id)
        for task in tasks:
            if task["id"] == task_id:
                task["status"] = status
                self._repo.set_collection("tasks", profile_id, tasks)
                return task
        raise KeyError("Task not found")

    def review_flashcard(self, profile_id: str, user_id: str, card_id: str, rating: str) -> Dict[str, Any]:
        self.get_profile(profile_id, user_id)
        intervals = {"again": 1, "hard": 2, "good": 5, "easy": 10}
        cards = self._repo.get_collection("flashcards", profile_id)
        for card in cards:
            if card["id"] == card_id:
                interval = intervals[rating]
                card["due"] = (date.today() + timedelta(days=interval)).isoformat()
                card["reps"] += 1
                card["stability"] = round(card["stability"] + interval * 0.35, 2)
                card["difficulty"] = round(max(1.0, card["difficulty"] + (0.3 if rating == "again" else -0.15)), 2)
                self._repo.set_collection("flashcards", profile_id, cards)
                return card
        raise KeyError("Flashcard not found")

    # ---------------------------------------------------------------- tutor

    def tutor(self, profile_id: str, user_id: str, question: str) -> Dict[str, Any]:
        self.get_profile(profile_id, user_id)
        sources = self.search(profile_id, user_id, question)[:3]
        context_text = "\n\n".join(f"{item['title']}: {item['excerpt']}" for item in sources)
        prompt = (
            "You are a precise, encouraging study tutor. Answer only from the provided profile-scoped notes. "
            "If the notes do not contain enough information, say what is missing. Use short sections and one practice prompt.\n\n"
            f"Notes:\n{context_text or 'No matching notes available.'}\n\nQuestion: {question}"
        )
        base_url = config.ollama.base_url.rstrip("/")
        try:
            response = requests.post(
                f"{base_url}/api/generate",
                json={"model": config.ollama.model, "prompt": prompt, "stream": False},
                timeout=45,
            )
            response.raise_for_status()
            answer = response.json().get("response", "").strip()
            if answer:
                return {"answer": answer, "sources": sources, "provider": "ollama"}
        except requests.RequestException as error:
            logger.warning("Tutor LLM call failed, using local fallback: %s", error)
        fallback = "I found these profile notes: " + ", ".join(item["title"] for item in sources)
        if not sources:
            fallback = "I do not have a matching note in this profile yet. Add a note or ask a more specific question."
        return {"answer": fallback, "sources": sources, "provider": "local-fallback"}

    # ------------------------------------------------------------ infra status

    def infrastructure_status(self) -> Dict[str, Any]:
        ollama_url = config.ollama.base_url.rstrip("/")
        try:
            response = requests.get(f"{ollama_url}/api/tags", timeout=2)
            ollama = response.ok
        except requests.RequestException:
            ollama = False
        milvus_host = os.getenv("MILVUS_HOST", "localhost")
        milvus_port = int(os.getenv("MILVUS_PORT", "19530"))
        return {
            "ollama": {"available": ollama, "model": config.ollama.model},
            "milvus": {
                "available": self._tcp_available(milvus_host, milvus_port),
                "mode": "profile-filtered when configured",
            },
        }

    @staticmethod
    def _tcp_available(host: str, port: int) -> bool:
        import socket

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.5)
            return sock.connect_ex((host, port)) == 0

    def close(self) -> None:
        self._repo.close()
