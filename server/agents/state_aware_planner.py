"""State-Aware Planner - generates plans respecting student progress."""

import json
from typing import Optional
from datetime import date, timedelta

from ..tools import OllamaClient, ProgressExtractor, DateUtils, MilvusRAG
from ..tools.utils.progress_extractor import ProgressValidator
from ..models import ExecutionPlan, Task, StudentState, StudyPlan
from ..exceptions import PlannerException
from ..logger import setup_logger

logger = setup_logger(__name__)


class StateAwarePlanner:
    """Planner that generates study plans respecting student progress."""

    def __init__(self, ollama_client: OllamaClient, rag_system: Optional[MilvusRAG] = None):
        """Initialize the State-Aware Planner.

        Args:
            ollama_client: OllamaClient instance
            rag_system: Optional MilvusRAG for curriculum context
        """
        self.client = ollama_client
        self.rag = rag_system or MilvusRAG()
        self.extractor = ProgressExtractor()
        self.validator = ProgressValidator()

    def plan_with_progress(
        self,
        request: str,
        student_state: Optional[StudentState] = None,
    ) -> ExecutionPlan:
        """Generate execution plan respecting student progress.

        Args:
            request: User request (may mention progress)
            student_state: Current student state (optional, creates default if missing)

        Returns:
            ExecutionPlan that doesn't repeat learned topics

        Raises:
            PlannerException: If planning fails
        """
        logger.info(f"Planning with progress for: {request[:100]}...")

        # Fallback: Create default state if not provided
        if not student_state:
            logger.info("No student state provided. Using default (90-day timeline, 6 hours/day)")
            from datetime import timedelta
            student_state = StudentState(
                student_id="anonymous",
                created_date=date.today(),
                exam_deadline=date.today() + timedelta(days=90),  # Default 90 days
                available_hours_per_day=6.0,
            )

        # Step 1: Extract any progress claims from request
        progress_claims = self.extractor.extract_progress(request)
        if progress_claims:
            logger.info(f"Extracted {len(progress_claims)} progress claims")
            progress_update = self.extractor.update_student_state(student_state, progress_claims)
            student_state = progress_update.updated_state
        else:
            logger.info("No progress mentioned in request. Assuming fresh start.")

        # Step 2: Determine exam date if mentioned (fallback: use state deadline or 90 days)
        exam_date = self._extract_exam_date(request)
        if exam_date:
            student_state.exam_deadline = exam_date
            days_remaining = DateUtils.days_until_exam(exam_date)
            logger.info(f"Exam deadline extracted: {exam_date} ({days_remaining} days remaining)")
        elif not student_state.exam_deadline:
            logger.info("No exam deadline found. Using 90-day default.")
            from datetime import timedelta
            student_state.exam_deadline = date.today() + timedelta(days=90)

        # Step 3: Get curriculum topics, filtering out learned ones
        learned_topics = student_state.get_learned_topic_names()
        available_topics = self._get_available_topics(request, learned_topics)

        logger.info(f"Learned: {len(learned_topics)} topics. Available: {len(available_topics)} topics")

        # Step 4: Generate plan with LLM, considering constraints
        prompt = self._build_state_aware_prompt(
            request,
            student_state,
            available_topics,
        )

        try:
            response = self.client.structured_generate(
                prompt,
                schema={
                    "type": "object",
                    "properties": {
                        "document_type": {"type": "string"},
                        "assumptions": {
                            "type": "object",
                            "additionalProperties": {"type": "string"},
                        },
                        "tasks": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "integer"},
                                    "description": {"type": "string"},
                                    "dependencies": {"type": "array", "items": {"type": "integer"}},
                                },
                            },
                        },
                        "outline": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["document_type", "assumptions", "tasks", "outline"],
                },
            )

            parsed = response.get("parsed_response", {})

            plan = ExecutionPlan(
                document_type=parsed.get("document_type", "Study Plan"),
                assumptions=parsed.get("assumptions", {}),
                tasks=[Task(**t) for t in parsed.get("tasks", [])],
                outline=parsed.get("outline", []),
            )

            # Step 5: Validate plan
            is_feasible, validation_issues = self.validator.validate_plan(
                student_state,
                plan.outline,
            )

            if not is_feasible:
                logger.warning(f"Plan validation issues: {validation_issues}")
                plan.assumptions["validation_issues"] = ", ".join(validation_issues)

            return plan

        except Exception as e:
            raise PlannerException(f"Failed to generate state-aware plan: {str(e)}")

    def _extract_exam_date(self, request: str) -> Optional[date]:
        """Extract exam date from request text."""
        import re

        # Look for patterns like "January 2026", "December exam", etc.
        exam_match = re.search(
            r"(?:exam|test)\s+(?:on\s+)?([A-Za-z]+\s+\d{4}|[A-Za-z]+\s+\d{1,2},?\s+\d{4})",
            request,
            re.IGNORECASE,
        )

        if exam_match:
            date_text = exam_match.group(1)
            return DateUtils.parse_exam_date(date_text)

        # Also check for "deadline" patterns
        deadline_match = re.search(
            r"deadline\s+(?:of\s+)?(?:is\s+)?([A-Za-z]+\s+\d{4}|[A-Za-z]+\s+\d{1,2},?\s+\d{4})",
            request,
            re.IGNORECASE,
        )

        if deadline_match:
            date_text = deadline_match.group(1)
            return DateUtils.parse_exam_date(date_text)

        return None

    def _get_available_topics(self, request: str, exclude_topics: set) -> list:
        """Get curriculum topics, excluding learned ones.

        Args:
            request: User request for context
            exclude_topics: Topics to exclude

        Returns:
            List of available topics
        """
        try:
            # Search curriculum for relevant topics
            results = self.rag.search(request, top_k=10)

            all_topics = []
            for result in results:
                # Extract topics from curriculum content (simple heuristic)
                content = result.get("content", "")
                # Parse chapter/unit names
                import re

                chapters = re.findall(r"(?:Unit|Chapter|Topic|Section)\s+(?:\d+:?)?\s+([^-\n]+)", content)
                for chapter in chapters:
                    chapter = chapter.strip()
                    if chapter and len(chapter) > 2 and chapter.lower() not in {t.lower() for t in exclude_topics}:
                        all_topics.append(chapter)

            return all_topics[:50]  # Return top 50 available topics

        except Exception as e:
            logger.warning(f"Failed to fetch available topics: {e}")
            return []

    def _build_state_aware_prompt(
        self,
        request: str,
        state: StudentState,
        available_topics: list,
    ) -> str:
        """Build prompt for state-aware planning.

        Args:
            request: User request
            state: Student state
            available_topics: Topics not yet learned

        Returns:
            Formatted prompt
        """
        learned_topics = state.get_learned_topic_names()
        days_until_exam = state.get_days_until_exam()

        prompt = f"""You are an expert exam preparation planner. Create a study plan respecting student progress.

STUDENT STATE:
- Learned Topics ({len(learned_topics)}): {', '.join(list(learned_topics)[:5])}{'...' if len(learned_topics) > 5 else ''}
- Available Study Hours/Day: {state.available_hours_per_day}
- Learning Velocity: {state.learning_velocity:.2f} topics/day

EXAM DEADLINE: {state.exam_deadline} ({days_until_exam} days remaining)

REQUEST: {request}

AVAILABLE TOPICS TO LEARN ({len(available_topics)}):
{', '.join(available_topics[:20])}{'...' if len(available_topics) > 20 else ''}

CONSTRAINTS:
1. Do NOT recommend any topics from "Learned Topics" - they are already mastered
2. Only use topics from "Available Topics"
3. Ensure daily load is realistic: ≤ {state.available_hours_per_day} hours/day
4. Cover as many unlearned topics as possible given time constraint
5. Organize topics in progressive difficulty order

Generate a realistic, personalized study plan that:
- Respects what they've already learned (no repetition)
- Fits their time constraints
- Covers important topics first
- Includes specific topics (not generic "study math")

Return the plan as JSON with:
- document_type: "Personalized Study Plan"
- assumptions: Key constraints and decisions
- tasks: List of study tasks with dependencies
- outline: Daily/weekly breakdown of topics"""

        return prompt
