"""Extract student progress claims from natural language input."""

import re
from datetime import datetime, date, timedelta
from typing import List, Tuple, Optional
from ..models import ProgressClaim, ProgressUpdate, StudentState, TopicProgress
from ..logger import setup_logger

logger = setup_logger(__name__)


class ProgressExtractor:
    """Extract progress updates from user messages."""

    # Patterns for different progress types
    COMPLETION_PATTERNS = [
        r"(?:completed|finished|learned|mastered|covered)\s+(?:the\s+)?(?:chapter|topic|section)?\s*:?\s*([a-zA-Z\s]+?)(?:\s+(?:today|yesterday|on\s+\d{1,2}\/\d{1,2})|$)",
        r"(?:did|studied|worked on|solved)\s+([a-zA-Z\s]+?)\s+(?:problems|exercises|questions)",
        r"finished\s+(?:chapter|topic)?\s*:?\s*([a-zA-Z\s]+)",
    ]

    HOURS_PATTERNS = [
        r"(?:spent|studied for|worked for)\s+(\d+(?:\.\d+)?)\s+(?:hours?|hrs?)",
        r"(\d+(?:\.\d+)?)\s+(?:hours?|hrs?)\s+(?:on|of|studying|learning)",
        r"(?:studied|learned)\s+(?:for\s+)?(\d+(?:\.\d+)?)\s+(?:hours?|hrs?)",
    ]

    DATE_PATTERNS = [
        (r"today", 0),
        (r"yesterday", -1),
        (r"on\s+(\d{1,2})[\/\-](\d{1,2})", None),  # Date parsing needed
    ]

    CONFIDENCE_PATTERNS = [
        (r"(?:fully\s+)?mastered", 0.95),
        (r"(?:completely\s+)?(?:learned|understood)", 0.85),
        (r"(?:covered|studied|learned about)", 0.70),
        (r"(?:partially\s+)?(?:understand|learned)", 0.50),
    ]

    def extract_progress(self, user_input: str) -> List[ProgressClaim]:
        """Extract all progress claims from user input.

        Args:
            user_input: User message text

        Returns:
            List of ProgressClaim objects
        """
        claims = []
        text_lower = user_input.lower()

        # Extract completion claims
        for pattern in self.COMPLETION_PATTERNS:
            matches = re.finditer(pattern, user_input, re.IGNORECASE)
            for match in matches:
                topic = match.group(1).strip() if match.groups() else None
                if topic and len(topic) > 2:  # Ignore very short matches
                    claim = ProgressClaim(
                        claim_type="completed_topic",
                        topic_name=topic,
                        completion_date=self._extract_date(match.group(0)),
                        extracted_text=match.group(0),
                    )
                    claims.append(claim)

        # Extract hours spent
        for pattern in self.HOURS_PATTERNS:
            matches = re.finditer(pattern, user_input, re.IGNORECASE)
            for match in matches:
                hours = float(match.group(1))
                claim = ProgressClaim(
                    claim_type="spent_hours",
                    hours=hours,
                    extracted_text=match.group(0),
                )
                claims.append(claim)

        # Extract confidence levels from completion claims
        for claim in claims:
            if claim.claim_type == "completed_topic":
                confidence = self._extract_confidence(claim.extracted_text)
                claim.confidence = confidence

        logger.info(f"Extracted {len(claims)} progress claims from input")
        return claims

    def update_student_state(
        self, state: StudentState, claims: List[ProgressClaim]
    ) -> ProgressUpdate:
        """Apply progress claims to student state.

        Args:
            state: Current StudentState
            claims: Progress claims to apply

        Returns:
            ProgressUpdate with updated state
        """
        updated_state = state.copy(deep=True)
        updated_state.last_updated = datetime.now()

        for claim in claims:
            if claim.claim_type == "completed_topic" and claim.topic_name:
                self._apply_completion_claim(updated_state, claim)
            elif claim.claim_type == "spent_hours" and claim.hours:
                self._apply_hours_claim(updated_state, claim)

        logger.info(f"Applied {len(claims)} progress claims to student state")
        return ProgressUpdate(
            student_id=state.student_id,
            claims=claims,
            updated_state=updated_state,
            extraction_confidence=0.85,
        )

    def _apply_completion_claim(self, state: StudentState, claim: ProgressClaim):
        """Apply topic completion claim to state."""
        topic_name = claim.topic_name.strip()

        # Find existing topic or create new
        existing = next((t for t in state.learned_topics if t.topic_name.lower() == topic_name.lower()), None)

        if existing:
            existing.confidence = claim.confidence or 0.85
            existing.completed_date = claim.completion_date or date.today()
            existing.revision_count += 1
            existing.last_revised_date = date.today()
        else:
            state.learned_topics.append(
                TopicProgress(
                    topic_name=topic_name,
                    completed_date=claim.completion_date or date.today(),
                    confidence=claim.confidence or 0.85,
                    revision_count=1,
                )
            )

    def _apply_hours_claim(self, state: StudentState, claim: ProgressClaim):
        """Apply hours spent claim (update velocity estimate)."""
        if claim.hours and claim.hours > 0:
            # Simple moving average for learning velocity
            total_hours = sum(t.hours_spent for t in state.learned_topics)
            total_topics = len(state.learned_topics)

            if total_topics > 0:
                avg_hours = (total_hours + claim.hours) / (total_topics + 1)
                # Learning velocity: if avg 2 hours per topic, and study 6 hours/day
                state.learning_velocity = state.available_hours_per_day / max(avg_hours, 1.0)

    def _extract_date(self, text: str) -> Optional[date]:
        """Extract date from text."""
        today = date.today()

        if "today" in text.lower():
            return today
        if "yesterday" in text.lower():
            return today - timedelta(days=1)

        # Try to parse M/D or MM/DD format
        date_match = re.search(r"(\d{1,2})[\/\-](\d{1,2})", text)
        if date_match:
            try:
                month, day = int(date_match.group(1)), int(date_match.group(2))
                return date(today.year, month, day)
            except ValueError:
                pass

        return None

    def _extract_confidence(self, text: str) -> float:
        """Extract confidence level from text."""
        text_lower = text.lower()

        for pattern, confidence in self.CONFIDENCE_PATTERNS:
            if re.search(pattern, text_lower):
                return confidence

        return 0.70  # Default confidence


class ProgressValidator:
    """Validate study plans against student state."""

    @staticmethod
    def validate_plan(state: StudentState, plan_topics: List[str]) -> Tuple[bool, List[str]]:
        """Validate that plan doesn't repeat learned topics and is feasible.

        Args:
            state: StudentState
            plan_topics: Topics in the proposed plan

        Returns:
            (is_feasible, list of validation issues)
        """
        issues = []
        learned = state.get_learned_topic_names()

        # Check for repetition
        repetitions = [t for t in plan_topics if t.lower() in {l.lower() for l in learned}]
        if repetitions:
            issues.append(f"Already learned: {', '.join(repetitions)}")

        # Check time feasibility
        days_until_exam = state.get_days_until_exam()
        if days_until_exam and days_until_exam > 0:
            required_daily = len(plan_topics) / days_until_exam
            capacity = state.available_hours_per_day / max(1.0, state.learning_velocity)

            if required_daily > capacity * 1.2:  # 20% buffer
                issues.append(
                    f"Unrealistic daily load: {required_daily:.2f} topics/day "
                    f"(capacity: {capacity:.2f})"
                )

        return len(issues) == 0, issues
