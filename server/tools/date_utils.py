"""Date and scheduling utilities for exam prep."""

from datetime import datetime, date, timedelta
from typing import Dict, List, Tuple, Optional


class DateUtils:
    """Utilities for date calculations and scheduling."""

    @staticmethod
    def today() -> date:
        """Return today's date."""
        return date.today()

    @staticmethod
    def days_between(start: date, end: date) -> int:
        """Calculate days between two dates."""
        return (end - start).days

    @staticmethod
    def days_until_exam(exam_date: date) -> int:
        """Days until exam (from today)."""
        return DateUtils.days_between(date.today(), exam_date)

    @staticmethod
    def weeks_until_exam(exam_date: date) -> float:
        """Weeks until exam."""
        days = DateUtils.days_until_exam(exam_date)
        return days / 7.0

    @staticmethod
    def is_exam_soon(exam_date: date, days_threshold: int = 30) -> bool:
        """Check if exam is within threshold days."""
        return DateUtils.days_until_exam(exam_date) <= days_threshold

    @staticmethod
    def parse_exam_date(text: str) -> Optional[date]:
        """Parse exam date from text like 'January 2026', 'Dec 15', etc."""
        import re

        text = text.strip()

        # Try "Month Year" format: "January 2026", "Dec 2025"
        month_year_match = re.search(
            r"(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{4})",
            text,
            re.IGNORECASE,
        )
        if month_year_match:
            month_str, year_str = month_year_match.groups()
            month_map = {
                "january": 1, "february": 2, "march": 3, "april": 4,
                "may": 5, "june": 6, "july": 7, "august": 8,
                "september": 9, "october": 10, "november": 11, "december": 12,
                "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
                "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
            }
            month = month_map.get(month_str.lower())
            year = int(year_str)
            # Default to first day of month (or specific day if mentioned)
            day = 1
            day_match = re.search(r"(\d{1,2})\s+(?:of\s+)?(?:" + month_str + ")", text, re.IGNORECASE)
            if day_match:
                day = int(day_match.group(1))
            return date(year, month, min(day, 28))  # Cap at 28 to avoid month-end issues

        # Try "Month Day Year" format: "January 15, 2026"
        full_match = re.search(
            r"(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{1,2}),?\s+(\d{4})",
            text,
            re.IGNORECASE,
        )
        if full_match:
            month_str, day_str, year_str = full_match.groups()
            month_map = {
                "january": 1, "february": 2, "march": 3, "april": 4,
                "may": 5, "june": 6, "july": 7, "august": 8,
                "september": 9, "october": 10, "november": 11, "december": 12,
                "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
                "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
            }
            month = month_map.get(month_str.lower())
            day = int(day_str)
            year = int(year_str)
            return date(year, month, day)

        return None

    @staticmethod
    def create_daily_schedule(
        topics: List[str],
        exam_date: date,
        hours_per_day: float = 6.0,
        hours_per_topic: float = 2.0,
    ) -> Dict[date, List[str]]:
        """Create a day-by-day study schedule.

        Args:
            topics: Topics to schedule
            exam_date: When exam happens
            hours_per_day: Available study hours per day
            hours_per_topic: Estimated hours per topic

        Returns:
            Dict mapping date -> topics to study that day
        """
        today = date.today()
        days_available = DateUtils.days_between(today, exam_date)

        if days_available <= 0:
            return {today: topics}

        # Calculate topics per day
        topics_per_day = max(1, int(hours_per_day / hours_per_topic))
        schedule = {}

        topic_idx = 0
        current_date = today

        while current_date < exam_date and topic_idx < len(topics):
            daily_topics = []
            for _ in range(topics_per_day):
                if topic_idx < len(topics):
                    daily_topics.append(topics[topic_idx])
                    topic_idx += 1

            if daily_topics:
                schedule[current_date] = daily_topics

            current_date += timedelta(days=1)

        # Add remaining topics to last day
        if topic_idx < len(topics):
            last_date = max(schedule.keys()) if schedule else today
            if last_date not in schedule:
                schedule[last_date] = []
            schedule[last_date].extend(topics[topic_idx:])

        return schedule

    @staticmethod
    def get_preparation_phases(exam_date: date) -> Dict[str, Tuple[date, date]]:
        """Get preparation phases based on time until exam.

        Returns dict of phase_name -> (start_date, end_date)
        """
        today = date.today()
        days_until = DateUtils.days_until_exam(exam_date)

        phases = {}

        if days_until > 180:
            # Foundation phase (6 months before)
            foundation_start = today
            foundation_end = exam_date - timedelta(days=120)
            phases["foundation"] = (foundation_start, foundation_end)

            # Intermediate phase (4 months)
            phases["intermediate"] = (foundation_end + timedelta(days=1), exam_date - timedelta(days=30))

        elif days_until > 60:
            # Main prep (2 months)
            phases["main_prep"] = (today, exam_date - timedelta(days=7))

        # Final revision (always last week)
        if days_until > 7:
            phases["final_revision"] = (exam_date - timedelta(days=7), exam_date - timedelta(days=1))

        return phases

    @staticmethod
    def days_in_phase(phase_dates: Tuple[date, date]) -> int:
        """Days available in a preparation phase."""
        start, end = phase_dates
        return DateUtils.days_between(start, end)
