"""Study-content generation agents.

Turn a profile's goal and its real material (chapters from documents + ingested
corpus chunks) into the study scaffolding that used to be hardcoded demo data:

- PlannerAgent      -> a hierarchical task tree (subject -> chapter -> tasks)
- FlashcardAgent    -> Q/A cards seeded into the FSRS-style review scheduler
- SubjectsBuilder   -> subject list + coverage derived from actual documents

The two LLM agents raise on failure (no fabricated content); SubjectsBuilder is
deterministic (pure aggregation over documents).
"""

import json
from datetime import date
from typing import Any, Dict, List, Optional

from ..base.exceptions import AgentException
from ..base.logger import setup_logger
from ..tools.utils import date_tool

logger = setup_logger(__name__)


class StudyContentException(AgentException):
    """Raised when study content cannot be generated."""


def _extract_json(text: str) -> Dict[str, Any]:
    start, end = text.find("{"), text.rfind("}") + 1
    if start == -1 or end <= 0:
        raise StudyContentException("No JSON object in LLM response")
    return json.loads(text[start:end])


def _slug(text: str) -> str:
    return "-".join(str(text).lower().split())[:48]


class PlannerAgent:
    """Generate a hierarchical study plan (task tree) from goal + chapters."""

    SYSTEM_PROMPT = (
        "You are a study planner. Given an exam goal, a list of chapters, and the "
        "learner's instruction, produce a hierarchical task tree: for each relevant "
        "chapter, 1-3 concrete, actionable study tasks (revise, practice, mock-test, etc.). "
        "Follow the learner's instruction closely — it defines the plan's focus, horizon, "
        "and intensity. "
        'Return ONLY JSON: {"tasks": [{"title": "<task>", "parent": "<chapter or subject>", '
        '"estimate": "<e.g. 45 min>", "priority": "high|medium|low"}]}. '
        "Keep it realistic (at most ~12 tasks) and ordered from foundational to advanced."
    )

    def __init__(self, llm):
        self.llm = llm

    def run(
        self,
        goal: str,
        chapters: List[str],
        instruction: str = "",
        deadline: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        if self.llm is None:
            raise StudyContentException("No LLM client configured for planner")
        chapter_text = ", ".join(chapters) if chapters else "general syllabus"
        instruction_text = instruction.strip() or "Balanced plan covering all chapters evenly."
        # Ground the model in the real current date (and days-to-deadline if given)
        # so any date/horizon reasoning is anchored, not guessed.
        date_block = date_tool.date_context(deadline)
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": f"{date_block}\n\nGoal: {goal}\nChapters: {chapter_text}\nInstruction: {instruction_text}\n\nReturn the task tree JSON now."},
        ]
        result = self.llm.chat(messages)
        parsed = _extract_json(result.get("message", {}).get("content", ""))
        tasks, seen = [], set()
        for index, item in enumerate(parsed.get("tasks", [])):
            title = (item.get("title") or "").strip()
            if not title:
                continue
            task_id = f"{_slug(title)}-{index}"
            if task_id in seen:
                continue
            seen.add(task_id)
            priority = item.get("priority", "medium")
            tasks.append({
                "id": task_id,
                "title": title,
                "parent": (item.get("parent") or goal),
                "status": "planned",
                "estimate": item.get("estimate", "30 min"),
                "priority": priority if priority in ("high", "medium", "low") else "medium",
            })
        logger.info("PlannerAgent: %d tasks", len(tasks))
        return tasks


class FlashcardAgent:
    """Generate Q/A flashcards from the profile's material."""

    SYSTEM_PROMPT = (
        "You are a flashcard author for spaced-repetition study. From the study material, "
        "write clear question/answer cards that test understanding (not trivia). "
        'Return ONLY JSON: {"cards": [{"front": "<question>", "back": "<concise answer>"}]}. '
        "Write at most 10 cards; keep answers 1-3 sentences."
    )

    def __init__(self, llm):
        self.llm = llm

    def run(self, material: str, instruction: str = "") -> List[Dict[str, Any]]:
        if self.llm is None:
            raise StudyContentException("No LLM client configured for flashcards")
        if not material.strip():
            return []
        focus = f"\nFocus: {instruction.strip()}" if instruction.strip() else ""
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": f"Study material:\n{material[:6000]}{focus}\n\nReturn the cards JSON now."},
        ]
        result = self.llm.chat(messages)
        parsed = _extract_json(result.get("message", {}).get("content", ""))
        today = date.today().isoformat()
        cards = []
        for index, item in enumerate(parsed.get("cards", [])):
            front = (item.get("front") or "").strip()
            back = (item.get("back") or "").strip()
            if not front or not back:
                continue
            # FSRS-style starting state; all due today for a first pass.
            cards.append({
                "id": f"card-{_slug(front)[:24]}-{index}",
                "front": front,
                "back": back,
                "due": today,
                "stability": 1.0,
                "difficulty": 5.0,
                "reps": 0,
            })
        logger.info("FlashcardAgent: %d cards", len(cards))
        return cards


class SubjectsBuilder:
    """Derive subjects + coverage from real documents (deterministic)."""

    _PALETTE = ["#06b6d4", "#f97316", "#8b5cf6", "#22c55e", "#e11d48", "#eab308"]

    def run(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        by_subject: Dict[str, set] = {}
        for doc in documents:
            subject = (doc.get("subject") or "").strip()
            if not subject:
                continue
            chapter = (doc.get("chapter") or doc.get("title") or "").strip()
            by_subject.setdefault(subject, set())
            if chapter:
                by_subject[subject].add(chapter)

        subjects = []
        for index, (name, chapters) in enumerate(sorted(by_subject.items())):
            # Coverage is a light proxy: more distinct chapters => more covered.
            count = len(chapters)
            progress = min(100, 20 + count * 15)
            subjects.append({
                "name": name,
                "progress": progress,
                "mastery": round(min(1.0, 0.2 + count * 0.15), 2),
                "color": self._PALETTE[index % len(self._PALETTE)],
                "chapters": sorted(chapters),
            })
        logger.info("SubjectsBuilder: %d subjects", len(subjects))
        return subjects
