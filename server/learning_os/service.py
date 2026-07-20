"""Profile-isolated application service for the AI Learning OS MVP."""

from datetime import date, datetime, timedelta, timezone
import os
from typing import Any, Dict, List

import requests

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
    """Manage learning resources while preserving profile-level isolation.

    The maps are an intentionally small repository implementation. The API only
    speaks in profile-scoped objects, allowing a SQL/Milvus repository to replace
    these maps without changing the client contract.
    """

    def __init__(self) -> None:
        self._profiles: Dict[str, LearningProfile] = {}
        self._workspaces: Dict[str, Workspace] = {}
        self._documents: Dict[str, LearningDocument] = {}
        self._subjects: Dict[str, List[Dict[str, Any]]] = {}
        self._tasks: Dict[str, List[Dict[str, Any]]] = {}
        self._flashcards: Dict[str, List[Dict[str, Any]]] = {}
        self._memories: Dict[str, List[Dict[str, Any]]] = {}

    def create_profile(self, request: LearningProfileCreate) -> LearningProfile:
        profile = LearningProfile(**request.model_dump())
        self._profiles[profile.profile_id] = profile
        self._subjects.setdefault(profile.profile_id, [])
        self._tasks.setdefault(profile.profile_id, [])
        self._flashcards.setdefault(profile.profile_id, [])
        self._memories.setdefault(profile.profile_id, [])
        return profile

    def list_profiles(self, user_id: str) -> List[LearningProfile]:
        return [profile for profile in self._profiles.values() if profile.user_id == user_id]

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

    def update_document(self, document_id: str, user_id: str, content: str) -> LearningDocument:
        document = self.get_document(document_id, user_id)
        document.content = content
        document.version += 1
        document.updated_at = datetime.now(timezone.utc)
        return document

    def list_documents(self, profile_id: str, user_id: str) -> List[LearningDocument]:
        self.get_profile(profile_id, user_id)
        return [
            document
            for document in self._documents.values()
            if document.profile_id == profile_id and document.user_id == user_id
        ]

    def ensure_demo_data(self, user_id: str) -> List[LearningProfile]:
        """Create a rich but local-only starter workspace for a new learner."""
        existing = self.list_profiles(user_id)
        if existing:
            return existing

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
        self._subjects[boards.profile_id] = [
            {"name": "Physics", "progress": 68, "mastery": 0.72, "color": "#06b6d4"},
            {"name": "Chemistry", "progress": 51, "mastery": 0.58, "color": "#f97316"},
            {"name": "Mathematics", "progress": 44, "mastery": 0.49, "color": "#8b5cf6"},
        ]
        self._subjects[jee.profile_id] = [
            {"name": "Physics", "progress": 33, "mastery": 0.42, "color": "#06b6d4"},
            {"name": "Chemistry", "progress": 27, "mastery": 0.35, "color": "#f97316"},
            {"name": "Mathematics", "progress": 39, "mastery": 0.44, "color": "#8b5cf6"},
        ]
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
        self._tasks[boards.profile_id] = [
            {"id": "boards-physics", "title": "Physics", "parent": "Prepare for Boards", "status": "in_progress", "estimate": "4.5 h", "priority": "high"},
            {"id": "boards-electrostatics", "title": "Revise Electrostatics", "parent": "Physics", "status": "done", "estimate": "45 min", "priority": "medium"},
            {"id": "boards-current", "title": "Practice Kirchhoff loops", "parent": "Physics", "status": "in_progress", "estimate": "60 min", "priority": "high"},
            {"id": "boards-chemistry", "title": "Organic chemistry reaction sheet", "parent": "Chemistry", "status": "planned", "estimate": "50 min", "priority": "medium"},
            {"id": "boards-maths", "title": "Definite integrals mixed set", "parent": "Mathematics", "status": "planned", "estimate": "75 min", "priority": "high"},
        ]
        self._tasks[jee.profile_id] = [
            {"id": "jee-mechanics", "title": "Mechanics problem set", "parent": "JEE Preparation", "status": "in_progress", "estimate": "90 min", "priority": "high"},
            {"id": "jee-algebra", "title": "Revise complex numbers", "parent": "Mathematics", "status": "planned", "estimate": "50 min", "priority": "medium"},
        ]
        self._flashcards[boards.profile_id] = [
            {"id": "card-ohm", "front": "State Ohm's law.", "back": "At constant temperature, potential difference is proportional to current: V = IR.", "due": date.today().isoformat(), "stability": 4.2, "difficulty": 5.1, "reps": 4},
            {"id": "card-resistivity", "front": "How does resistance depend on geometry?", "back": "R = rho L / A, so it increases with length and decreases with cross-sectional area.", "due": date.today().isoformat(), "stability": 2.7, "difficulty": 6.0, "reps": 2},
        ]
        self._memories[boards.profile_id] = [
            {"text": "Learner benefits from worked numerical examples before abstraction.", "importance": 0.8},
            {"text": "Kirchhoff loop questions have needed repeated practice.", "importance": 0.9},
        ]
        return [boards, jee]

    def dashboard(self, profile_id: str, user_id: str) -> Dict[str, Any]:
        profile = self.get_profile(profile_id, user_id)
        documents = self.list_documents(profile_id, user_id)
        tasks = self._tasks.get(profile_id, [])
        cards = self._flashcards.get(profile_id, [])
        subjects = self._subjects.get(profile_id, [])
        due_cards = [card for card in cards if card["due"] <= date.today().isoformat()]
        completed = sum(task["status"] == "done" for task in tasks)
        return {
            "profile": profile.model_dump(mode="json"),
            "subjects": subjects,
            "documents": [document.model_dump(mode="json") for document in documents],
            "tasks": tasks,
            "flashcards": due_cards,
            "memories": self._memories.get(profile_id, []),
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
        self._subjects.get(profile_id, [])
        return {
            "nodes": [
                {"id": "vectors", "label": "Vectors", "kind": "prerequisite", "progress": 0.83},
                {"id": "electrostatics", "label": "Electrostatics", "kind": "chapter", "progress": 0.78},
                {"id": "capacitance", "label": "Capacitance", "kind": "concept", "progress": 0.54},
                {"id": "current", "label": "Current Electricity", "kind": "chapter", "progress": 0.68},
                {"id": "kirchhoff", "label": "Kirchhoff's Laws", "kind": "concept", "progress": 0.42},
            ],
            "edges": [
                {"source": "vectors", "target": "electrostatics", "label": "requires"},
                {"source": "electrostatics", "target": "capacitance", "label": "enables"},
                {"source": "capacitance", "target": "current", "label": "supports"},
                {"source": "current", "target": "kirchhoff", "label": "contains"},
            ],
        }

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

    def update_task_status(self, profile_id: str, user_id: str, task_id: str, status: str) -> Dict[str, Any]:
        self.get_profile(profile_id, user_id)
        for task in self._tasks.get(profile_id, []):
            if task["id"] == task_id:
                task["status"] = status
                return task
        raise KeyError("Task not found")

    def review_flashcard(self, profile_id: str, user_id: str, card_id: str, rating: str) -> Dict[str, Any]:
        self.get_profile(profile_id, user_id)
        intervals = {"again": 1, "hard": 2, "good": 5, "easy": 10}
        for card in self._flashcards.get(profile_id, []):
            if card["id"] == card_id:
                interval = intervals[rating]
                card["due"] = (date.today() + timedelta(days=interval)).isoformat()
                card["reps"] += 1
                card["stability"] = round(card["stability"] + interval * 0.35, 2)
                card["difficulty"] = round(max(1.0, card["difficulty"] + (0.3 if rating == "again" else -0.15)), 2)
                return card
        raise KeyError("Flashcard not found")

    def tutor(self, profile_id: str, user_id: str, question: str) -> Dict[str, Any]:
        self.get_profile(profile_id, user_id)
        sources = self.search(profile_id, user_id, question)[:3]
        context = "\n\n".join(f"{item['title']}: {item['excerpt']}" for item in sources)
        prompt = (
            "You are a precise, encouraging study tutor. Answer only from the provided profile-scoped notes. "
            "If the notes do not contain enough information, say what is missing. Use short sections and one practice prompt.\n\n"
            f"Notes:\n{context or 'No matching notes available.'}\n\nQuestion: {question}"
        )
        try:
            response = requests.post(
                f"{os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434').rstrip('/')}/api/generate",
                json={"model": os.getenv("OLLAMA_MODEL", "qwen3:0.6b"), "prompt": prompt, "stream": False},
                timeout=45,
            )
            response.raise_for_status()
            answer = response.json().get("response", "").strip()
            if answer:
                return {"answer": answer, "sources": sources, "provider": "ollama"}
        except requests.RequestException:
            pass
        fallback = "I found these profile notes: " + ", ".join(item["title"] for item in sources)
        if not sources:
            fallback = "I do not have a matching note in this profile yet. Add a note or ask a more specific question."
        return {"answer": fallback, "sources": sources, "provider": "local-fallback"}

    def infrastructure_status(self) -> Dict[str, Any]:
        ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
        try:
            response = requests.get(f"{ollama_url}/api/tags", timeout=2)
            ollama = response.ok
        except requests.RequestException:
            ollama = False
        return {
            "ollama": {"available": ollama, "model": os.getenv("OLLAMA_MODEL", "qwen3:0.6b")},
            "milvus": {"available": self._tcp_available("localhost", 19530), "mode": "profile-filtered when configured"},
        }

    @staticmethod
    def _tcp_available(host: str, port: int) -> bool:
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.5)
            return sock.connect_ex((host, port)) == 0
