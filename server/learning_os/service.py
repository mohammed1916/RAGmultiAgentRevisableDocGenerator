"""Profile-isolated application service for the AI Learning OS MVP.

State is persisted through :class:`LearningRepository` (SQLite) so profiles,
documents, tasks, flashcards and memories survive restarts. The public methods
below are the stable contract the API depends on; the storage backend can change
without touching the API layer.
"""

from datetime import date, datetime, timedelta, timezone
import os
from typing import Any, Dict, List, Optional
from uuid import uuid4

import requests

from ..agents.knowledge_graph import KnowledgeGraphAgent
from ..agents.graph_pipeline import GraphPipeline
from ..agents.study_content import (
    PlannerAgent as StudyPlannerAgent,
    FlashcardAgent,
    SubjectsBuilder,
)
from ..base.logger import setup_logger
from ..config import config
from .models import (
    DocumentCreate,
    LearningDocument,
    LearningProfile,
    LearningProfileCreate,
    ProfilePreferencesUpdate,
    ProfileUpdate,
    Workspace,
    WorkspaceCreate,
)
from .repository import LearningRepository

# Rough per-event study-minute weights used to turn discrete learning events
# (flashcard reviews, completed tasks) into an activity signal. These are
# estimates, not tracked wall-clock time.
_REVIEW_MINUTES = 2
_TASK_DONE_MINUTES = 25

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
        ingestion: Optional[Any] = None,
    ) -> None:
        self._repo = repository or LearningRepository()
        # Shared LLM client used by the tutor and (via the agents) generation.
        self._llm = llm_client
        self._graph_agent = KnowledgeGraphAgent(llm_client=llm_client)
        # Multi-agent pipeline that derives the graph from ingested corpus data.
        self._graph_pipeline = GraphPipeline(llm_client=llm_client)
        # Study-content generators (planner tree, flashcards, subjects).
        self._planner_agent = StudyPlannerAgent(llm_client)
        self._flashcard_agent = FlashcardAgent(llm_client)
        self._subjects_builder = SubjectsBuilder()
        # Optional ingestion service; when present, notes are embedded into the
        # vector store on save and the corpus feeds the multi-agent graph build.
        self._ingestion = ingestion

    def set_ingestion(self, ingestion: Any) -> None:
        """Attach the ingestion service after construction (wired at startup)."""
        self._ingestion = ingestion

    def _embed_note(self, document: LearningDocument) -> None:
        """(Re)embed a note's content into the profile's vector store."""
        if self._ingestion is None or not document.content.strip():
            return
        try:
            # Replace any prior chunks for this note, then embed the new content.
            self._ingestion.delete_doc(document.profile_id, document.document_id)
            self._ingestion.ingest_note(
                user_id=document.user_id,
                profile_id=document.profile_id,
                doc_id=document.document_id,
                text=document.content,
                subject=document.subject,
                chapter=document.chapter,
            )
        except Exception as error:
            logger.warning("Note embedding skipped (%s)", error)

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

    def update_profile(self, profile_id: str, user_id: str, request: ProfileUpdate) -> LearningProfile:
        """Update editable profile fields (name, learner_name, exam, goal…)."""
        profile = self.get_profile(profile_id, user_id)
        changes = request.model_dump(exclude_unset=True)
        for key, value in changes.items():
            setattr(profile, key, value)
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
        # Notes are also embedded so they are retrievable and feed the graph.
        self._embed_note(document)
        return document

    def delete_document(self, document_id: str, user_id: str, profile_id: str) -> None:
        """Delete a document from Postgres and its chunks from the vector store."""
        document = self.get_document(document_id, user_id, profile_id)  # raises if not owner
        self._repo.delete_entity("documents", document_id)
        if self._ingestion is not None:
            try:
                self._ingestion.delete_doc(document.profile_id, document_id)
            except Exception as error:
                logger.warning("Vector cleanup for %s skipped: %s", document_id, error)
        # Removing content invalidates the derived graph.
        self._repo.delete_collection("graph", document.profile_id)

    def get_document(self, document_id: str, user_id: str, profile_id: str) -> LearningDocument:
        data = self._repo.get_entity("documents", document_id)
        if (data is None or data.get("user_id") != user_id or data.get("profile_id") != profile_id):
            raise KeyError("Document not found")
        return LearningDocument(**data)

    def update_document(self, document_id: str, user_id: str, profile_id: str, content: str) -> LearningDocument:
        document = self.get_document(document_id, user_id, profile_id)
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
        self._embed_note(document)
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
                learner_name="Abdullah",
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
                learner_name="Abdullah",
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
        # Seed a couple of weeks of backdated activity so the analytics (which are
        # now derived, not hardcoded) show a realistic history for the demo.
        self._seed_demo_events(boards.profile_id, [70, 55, 90, 40, 110, 65, 80, 60, 75, 45, 95, 50, 85, 72])
        self._seed_demo_events(jee.profile_id, [40, 0, 55, 30, 0, 45, 60, 25, 0, 50, 35, 0, 40, 30])
        return [boards, jee]

    def _seed_demo_events(self, profile_id: str, minutes_by_day_desc: List[int]) -> None:
        """Create backdated demo events; index 0 is today, 1 is yesterday, etc."""
        now = datetime.now(timezone.utc)
        events: List[Dict[str, Any]] = []
        for offset, minutes in enumerate(minutes_by_day_desc):
            if minutes <= 0:
                continue
            ts = (now - timedelta(days=offset)).replace(hour=18, minute=0, second=0, microsecond=0)
            events.append({"ts": ts.isoformat(), "kind": "seed", "minutes": minutes})
        # Store oldest-first for consistency with the live append path.
        events.reverse()
        self._repo.set_collection("events", profile_id, events)

    # ------------------------------------------------------------- dashboards

    def dashboard(self, profile_id: str, user_id: str) -> Dict[str, Any]:
        profile = self.get_profile(profile_id, user_id)
        documents = self.list_documents(profile_id, user_id)
        tasks = self._repo.get_collection("tasks", profile_id)
        cards = self._repo.get_collection("flashcards", profile_id)
        subjects = self._repo.get_collection("subjects", profile_id)
        due_cards = [card for card in cards if card.get("due", date.today().isoformat()) <= date.today().isoformat()]
        completed = sum(task["status"] == "done" for task in tasks)
        analytics = self._analytics(profile_id)
        analytics["tasks_completed"] = completed
        analytics["task_total"] = len(tasks)
        analytics["review_due"] = len(due_cards)
        return {
            "profile": profile.model_dump(mode="json"),
            "subjects": subjects,
            "documents": [document.model_dump(mode="json") for document in documents],
            "tasks": tasks,
            "flashcards": due_cards,
            "memories": self._repo.get_collection("memories", profile_id),
            "analytics": analytics,
            "graph": self._graph_payload(profile_id),
        }

    def _analytics(self, profile_id: str) -> Dict[str, Any]:
        """Derive activity metrics from the profile's real event log.

        All figures come from logged learning events (flashcard reviews,
        completed tasks); a profile with no activity yet reports zeros rather
        than fabricated numbers.
        """
        events = self._repo.get_collection("events", profile_id)
        today = date.today()

        # Minutes per calendar day (UTC date of each event).
        minutes_by_day: Dict[str, int] = {}
        for event in events:
            try:
                day = datetime.fromisoformat(event["ts"]).date()
            except (KeyError, ValueError):
                continue
            minutes_by_day[day.isoformat()] = minutes_by_day.get(day.isoformat(), 0) + int(event.get("minutes", 0))

        def minutes_in_range(start: date, end: date) -> int:
            return sum(
                mins for iso, mins in minutes_by_day.items()
                if start <= date.fromisoformat(iso) <= end
            )

        # This week = trailing 7 days including today; last week = the 7 before.
        this_week = minutes_in_range(today - timedelta(days=6), today)
        last_week = minutes_in_range(today - timedelta(days=13), today - timedelta(days=7))
        if last_week > 0:
            trend_percent = round((this_week - last_week) / last_week * 100)
        else:
            trend_percent = 100 if this_week > 0 else 0

        # Current streak: consecutive days up to today with any activity.
        streak = 0
        cursor = today
        while minutes_by_day.get(cursor.isoformat(), 0) > 0:
            streak += 1
            cursor -= timedelta(days=1)

        # Last 7 days as an ordered activity series for the chart.
        activity = []
        for offset in range(6, -1, -1):
            day = today - timedelta(days=offset)
            activity.append({
                "day": day.strftime("%a"),
                "minutes": minutes_by_day.get(day.isoformat(), 0),
            })

        return {
            "study_minutes_this_week": this_week,
            "study_minutes_last_week": last_week,
            "trend_percent": trend_percent,
            "streak": streak,
            "activity": activity,
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

    def save_graph(self, profile_id: str, user_id: str, graph: Dict[str, Any]) -> Dict[str, Any]:
        """Persist a user-edited graph (custom roadmap layout)."""
        self.get_profile(profile_id, user_id)
        clean = {"nodes": graph.get("nodes", []), "edges": graph.get("edges", [])}
        self._repo.set_collection("graph", profile_id, [clean])
        return clean

    # --------------------------------------------------- content generation

    def _profile_chapters(self, profile_id: str) -> List[str]:
        chapters = []
        for data in self._repo.get_documents_by_profile(profile_id):
            chapter = (data.get("chapter") or "").strip()
            if chapter and chapter not in chapters:
                chapters.append(chapter)
        return chapters

    def _profile_material(self, profile_id: str) -> str:
        """Concatenate ingested chunks + document content for card generation."""
        parts: List[str] = []
        if self._ingestion is not None:
            for chunk in self._ingestion.list_corpus(profile_id, limit=60):
                content = (chunk.get("content") or "").strip()
                if content:
                    parts.append(content)
        if not parts:
            for data in self._repo.get_documents_by_profile(profile_id):
                content = (data.get("content") or "").strip()
                if content:
                    parts.append(content)
        return "\n\n".join(parts)

    def generate_plan(self, profile_id: str, user_id: str, instruction: str = "") -> List[Dict[str, Any]]:
        """Generate and persist a hierarchical study plan from goal + chapters.

        ``instruction`` is the learner's free-text guidance (focus, horizon,
        intensity) that shapes the plan.
        """
        profile = self.get_profile(profile_id, user_id)
        goal = profile.exam or profile.name
        tasks = self._planner_agent.run(goal, self._profile_chapters(profile_id), instruction)
        self._repo.set_collection("tasks", profile_id, tasks)
        return tasks

    def generate_flashcards(self, profile_id: str, user_id: str, instruction: str = "") -> List[Dict[str, Any]]:
        """Generate and persist flashcards from the profile's material."""
        self.get_profile(profile_id, user_id)
        cards = self._flashcard_agent.run(self._profile_material(profile_id), instruction)
        self._repo.set_collection("flashcards", profile_id, cards)
        return cards

    def list_ingested_sources(self, profile_id: str, user_id: str) -> List[Dict[str, Any]]:
        """Group a profile's ingested vector chunks by source document.

        Ingested data lives only in the vector store (it is not a workspace
        document); this exposes what has been added and how much, so the
        knowledge base is visible and manageable.
        """
        self.get_profile(profile_id, user_id)
        if self._ingestion is None:
            return []
        chunks = self._ingestion.list_corpus(profile_id, limit=2000)
        grouped: Dict[str, Dict[str, Any]] = {}
        for chunk in chunks:
            doc_id = chunk.get("doc_id") or "unknown"
            entry = grouped.setdefault(doc_id, {
                "doc_id": doc_id,
                "source": chunk.get("source") or "text",
                "subject": chunk.get("subject") or None,
                "chapter": chunk.get("chapter") or None,
                "chunks": 0,
            })
            entry["chunks"] += 1
        return sorted(grouped.values(), key=lambda item: item["source"])

    def delete_ingested_source(self, profile_id: str, user_id: str, doc_id: str) -> None:
        """Remove all chunks of one ingested source from the vector store."""
        self.get_profile(profile_id, user_id)
        if self._ingestion is not None:
            self._ingestion.delete_doc(profile_id, doc_id)
            self._repo.delete_collection("graph", profile_id)

    def generate_subjects(self, profile_id: str, user_id: str) -> List[Dict[str, Any]]:
        """Derive and persist subjects/coverage from the profile's documents."""
        self.get_profile(profile_id, user_id)
        documents = self._repo.get_documents_by_profile(profile_id)
        subjects = self._subjects_builder.run(documents)
        self._repo.set_collection("subjects", profile_id, subjects)
        return subjects

    def _build_and_store_graph(self, profile_id: str) -> Dict[str, Any]:
        """Build the knowledge graph, preferring the multi-agent corpus pipeline.

        If the profile has ingested chunks in the vector store, the 3-agent
        pipeline (extract -> map -> critic) derives the graph from that real
        material. Otherwise it falls back to the single chapter-based agent so a
        profile with only notes/documents still gets a graph.
        """
        graph = {"nodes": [], "edges": []}
        chunks = self._ingestion.list_corpus(profile_id) if self._ingestion is not None else []
        if chunks:
            try:
                graph = self._graph_pipeline.build_from_corpus(chunks)
            except Exception as error:
                logger.warning("Corpus graph pipeline failed, falling back: %s", error)
                graph = {"nodes": [], "edges": []}
        if not graph.get("nodes"):
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
                previous = task.get("status")
                task["status"] = status
                self._repo.set_collection("tasks", profile_id, tasks)
                # Log a study event only on the transition into "done".
                if status == "done" and previous != "done":
                    self._log_event(profile_id, "task_done", _TASK_DONE_MINUTES)
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
                card["reps"] = card.get("reps", 0) + 1
                card["stability"] = round(card.get("stability", 1.0) + interval * 0.35, 2)
                card["difficulty"] = round(max(1.0, card.get("difficulty", 5.0) + (0.3 if rating == "again" else -0.15)), 2)
                self._repo.set_collection("flashcards", profile_id, cards)
                self._log_event(profile_id, "review", _REVIEW_MINUTES)
                return card
        raise KeyError("Flashcard not found")

    # ------------------------------------------------- per-item collection CRUD

    @staticmethod
    def _next_id(prefix: str) -> str:
        return f"{prefix}-{uuid4().hex[:8]}"

    def _add_item(self, kind: str, profile_id: str, user_id: str, item: Dict[str, Any], id_prefix: str) -> Dict[str, Any]:
        self.get_profile(profile_id, user_id)
        items = self._repo.get_collection(kind, profile_id)
        record = dict(item)
        record.setdefault("id", self._next_id(id_prefix))
        items.append(record)
        self._repo.set_collection(kind, profile_id, items)
        return record

    def _update_item(self, kind: str, profile_id: str, user_id: str, item_id: str, changes: Dict[str, Any], match_key: str = "id") -> Dict[str, Any]:
        self.get_profile(profile_id, user_id)
        items = self._repo.get_collection(kind, profile_id)
        for record in items:
            if record.get(match_key) == item_id:
                record.update({k: v for k, v in changes.items() if v is not None})
                self._repo.set_collection(kind, profile_id, items)
                return record
        raise KeyError(f"{kind[:-1].capitalize()} not found")

    def _delete_item(self, kind: str, profile_id: str, user_id: str, item_id: str, match_key: str = "id") -> None:
        self.get_profile(profile_id, user_id)
        items = self._repo.get_collection(kind, profile_id)
        remaining = [r for r in items if r.get(match_key) != item_id]
        if len(remaining) == len(items):
            raise KeyError(f"{kind[:-1].capitalize()} not found")
        self._repo.set_collection(kind, profile_id, remaining)

    # Tasks
    def create_task(self, profile_id: str, user_id: str, item: Dict[str, Any]) -> Dict[str, Any]:
        item.setdefault("status", "planned")
        item.setdefault("priority", "medium")
        return self._add_item("tasks", profile_id, user_id, item, "task")

    def update_task(self, profile_id: str, user_id: str, task_id: str, changes: Dict[str, Any]) -> Dict[str, Any]:
        return self._update_item("tasks", profile_id, user_id, task_id, changes)

    def delete_task(self, profile_id: str, user_id: str, task_id: str) -> None:
        self._delete_item("tasks", profile_id, user_id, task_id)

    # Flashcards
    def create_flashcard(self, profile_id: str, user_id: str, item: Dict[str, Any]) -> Dict[str, Any]:
        item.setdefault("due", date.today().isoformat())
        item.setdefault("stability", 1.0)
        item.setdefault("difficulty", 5.0)
        item.setdefault("reps", 0)
        return self._add_item("flashcards", profile_id, user_id, item, "card")

    def update_flashcard(self, profile_id: str, user_id: str, card_id: str, changes: Dict[str, Any]) -> Dict[str, Any]:
        return self._update_item("flashcards", profile_id, user_id, card_id, changes)

    def delete_flashcard(self, profile_id: str, user_id: str, card_id: str) -> None:
        self._delete_item("flashcards", profile_id, user_id, card_id)

    # Subjects (matched by name, which is their identity)
    def create_subject(self, profile_id: str, user_id: str, item: Dict[str, Any]) -> Dict[str, Any]:
        item.setdefault("progress", 0)
        item.setdefault("mastery", 0.0)
        item.setdefault("color", "#0c8fa2")
        return self._add_item("subjects", profile_id, user_id, item, "subject")

    def update_subject(self, profile_id: str, user_id: str, name: str, changes: Dict[str, Any]) -> Dict[str, Any]:
        return self._update_item("subjects", profile_id, user_id, name, changes, match_key="name")

    def delete_subject(self, profile_id: str, user_id: str, name: str) -> None:
        self._delete_item("subjects", profile_id, user_id, name, match_key="name")

    # ---------------------------------------------------------------- events

    def _log_event(self, profile_id: str, kind: str, minutes: int) -> None:
        """Append a timestamped learning event to the profile's activity log."""
        events = self._repo.get_collection("events", profile_id)
        events.append({
            "ts": datetime.now(timezone.utc).isoformat(),
            "kind": kind,
            "minutes": minutes,
        })
        # Bound the log so it cannot grow without limit (keep recent 2000).
        if len(events) > 2000:
            events = events[-2000:]
        self._repo.set_collection("events", profile_id, events)

    # ---------------------------------------------------------------- tutor

    def tutor(self, profile_id: str, user_id: str, question: str) -> Dict[str, Any]:
        self.get_profile(profile_id, user_id)
        if self._llm is None:
            raise RuntimeError("LLM is not available")
        sources = self.search(profile_id, user_id, question)[:3]
        context_text = "\n\n".join(f"{item['title']}: {item['excerpt']}" for item in sources)
        prompt = (
            "You are a precise, encouraging study tutor. Answer only from the provided profile-scoped notes. "
            "If the notes do not contain enough information, say what is missing. Use short sections and one practice prompt.\n\n"
            f"Notes:\n{context_text or 'No matching notes available.'}\n\nQuestion: {question}"
        )
        # Uses the shared client, so it respects the active model selection.
        result = self._llm.generate(prompt)
        answer = (result.get("response") or "").strip()
        return {"answer": answer, "sources": sources, "provider": self._llm.mode}

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
