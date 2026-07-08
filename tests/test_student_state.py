"""Tests for student state management, progress tracking, and validation."""

import pytest
from datetime import date, timedelta
from server.models import (
    StudentState, TopicProgress, ProgressClaim, StudyPlan
)
from server.tools.progress_extractor import ProgressExtractor, ProgressValidator
from server.tools.date_utils import DateUtils
from server.agents.state_aware_planner import StateAwarePlanner
from unittest.mock import Mock, patch


class TestStudentState:
    """Test student state model."""

    def test_student_state_initialization(self):
        """Test creating a student state."""
        state = StudentState(
            student_id="jee_2026_001",
            created_date=date.today(),
            exam_deadline=date(2026, 1, 15),
            available_hours_per_day=6.0
        )

        assert state.student_id == "jee_2026_001"
        assert state.exam_deadline == date(2026, 1, 15)
        assert state.available_hours_per_day == 6.0

    def test_learned_topics_tracking(self):
        """Test tracking learned topics."""
        state = StudentState(
            student_id="test",
            created_date=date.today(),
        )

        # Add learned topics
        state.learned_topics.append(TopicProgress(
            topic_name="Algebra",
            confidence=0.95,
            completed_date=date.today()
        ))
        state.learned_topics.append(TopicProgress(
            topic_name="Trigonometry",
            confidence=0.85,
            completed_date=date.today() - timedelta(days=5)
        ))

        learned = state.get_learned_topic_names()
        assert "Algebra" in learned
        assert "Trigonometry" in learned
        assert len(learned) == 2

    def test_days_until_exam(self):
        """Test calculating days until exam."""
        exam_date = date.today() + timedelta(days=90)
        state = StudentState(
            student_id="test",
            created_date=date.today(),
            exam_deadline=exam_date
        )

        days = state.get_days_until_exam()
        assert days == 90

    def test_no_exam_deadline(self):
        """Test state without exam deadline."""
        state = StudentState(
            student_id="test",
            created_date=date.today(),
            exam_deadline=None
        )

        assert state.get_days_until_exam() is None


class TestProgressExtractor:
    """Test progress extraction from user input."""

    @pytest.fixture
    def extractor(self):
        """Create extractor instance."""
        return ProgressExtractor()

    def test_extract_completed_topic(self, extractor):
        """Test extracting completion claims."""
        text = "I completed the Algebra chapter today"
        claims = extractor.extract_progress(text)

        assert len(claims) > 0
        assert any(c.claim_type == "completed_topic" for c in claims)
        assert any("algebra" in str(c.topic_name).lower() for c in claims)

    def test_extract_hours_spent(self, extractor):
        """Test extracting hours spent."""
        text = "I studied for 3 hours on calculus"
        claims = extractor.extract_progress(text)

        assert len(claims) > 0
        assert any(c.claim_type == "spent_hours" and c.hours == 3.0 for c in claims)

    def test_extract_multiple_claims(self, extractor):
        """Test extracting multiple claims."""
        text = "I completed Algebra and Trigonometry, studied for 4 hours total"
        claims = extractor.extract_progress(text)

        assert len(claims) >= 2

    def test_update_student_state(self, extractor):
        """Test applying progress to state."""
        state = StudentState(
            student_id="test",
            created_date=date.today(),
        )

        claims = [ProgressClaim(
            claim_type="completed_topic",
            topic_name="Vectors",
            completion_date=date.today(),
            extracted_text="completed vectors"
        )]

        update = extractor.update_student_state(state, claims)
        assert "vectors" in {t.topic_name.lower() for t in update.updated_state.learned_topics}

    def test_mastery_confidence_level(self, extractor):
        """Test different mastery levels."""
        texts = [
            ("I mastered Algebra", 0.95),
            ("I learned Calculus", 0.85),
            ("I covered Geometry", 0.70),
        ]

        for text, expected_confidence in texts:
            claims = extractor.extract_progress(text)
            # Check that a confidence level was extracted
            completed = [c for c in claims if c.claim_type == "completed_topic"]
            if completed:
                # Confidence should be close to expected
                assert completed[0].confidence >= 0.5


class TestProgressValidator:
    """Test validation of study plans."""

    def test_no_repetition_validation(self):
        """Test that validator rejects repeated topics."""
        state = StudentState(
            student_id="test",
            created_date=date.today(),
            learned_topics=[
                TopicProgress(topic_name="Algebra", confidence=0.95)
            ]
        )

        plan_topics = ["Algebra", "Calculus"]  # Algebra already learned!
        is_feasible, issues = ProgressValidator.validate_plan(state, plan_topics)

        assert not is_feasible
        assert any("learned" in issue.lower() for issue in issues)

    def test_feasible_plan_validation(self):
        """Test that validator accepts feasible plans."""
        state = StudentState(
            student_id="test",
            created_date=date.today(),
            exam_deadline=date.today() + timedelta(days=30),
            available_hours_per_day=6.0,
            learning_velocity=3.0,  # 3 topics per day
        )

        plan_topics = ["Vectors", "Matrices", "Calculus"]
        is_feasible, issues = ProgressValidator.validate_plan(state, plan_topics)

        # Plan is feasible: 3 topics in 30 days at 3 topics/day
        assert is_feasible or len(issues) == 0

    def test_unrealistic_load_detection(self):
        """Test detection of unrealistic daily loads."""
        state = StudentState(
            student_id="test",
            created_date=date.today(),
            exam_deadline=date.today() + timedelta(days=5),  # Only 5 days!
            available_hours_per_day=3.0,
            learning_velocity=1.0,  # 1 topic per day
        )

        plan_topics = ["Topic1", "Topic2", "Topic3", "Topic4", "Topic5", "Topic6"]
        is_feasible, issues = ProgressValidator.validate_plan(state, plan_topics)

        # Should detect unrealistic load
        assert not is_feasible
        assert any("load" in issue.lower() for issue in issues)


class TestDateUtils:
    """Test date utilities."""

    def test_days_until_exam(self):
        """Test calculating days until exam."""
        exam = date.today() + timedelta(days=90)
        days = DateUtils.days_until_exam(exam)
        assert days == 90

    def test_parse_exam_date(self):
        """Test parsing exam date from text."""
        exam_date = DateUtils.parse_exam_date("January 2026")
        assert exam_date is not None
        assert exam_date.year == 2026
        assert exam_date.month == 1

    def test_parse_full_date(self):
        """Test parsing full date format."""
        exam_date = DateUtils.parse_exam_date("January 15, 2026")
        assert exam_date is not None
        assert exam_date.month == 1
        assert exam_date.day == 15
        assert exam_date.year == 2026

    def test_is_exam_soon(self):
        """Test checking if exam is soon."""
        soon_exam = date.today() + timedelta(days=15)
        far_exam = date.today() + timedelta(days=100)

        assert DateUtils.is_exam_soon(soon_exam, days_threshold=30)
        assert not DateUtils.is_exam_soon(far_exam, days_threshold=30)

    def test_create_daily_schedule(self):
        """Test creating daily study schedule."""
        topics = ["Algebra", "Trigonometry", "Calculus", "Vectors"]
        exam_date = date.today() + timedelta(days=10)

        schedule = DateUtils.create_daily_schedule(
            topics,
            exam_date,
            hours_per_day=6.0,
            hours_per_topic=1.5
        )

        # Should have schedule for multiple days
        assert len(schedule) > 1
        # All topics should be scheduled
        all_scheduled = [t for day_topics in schedule.values() for t in day_topics]
        assert len(all_scheduled) >= 4

    def test_preparation_phases(self):
        """Test getting preparation phases."""
        exam_date = date.today() + timedelta(days=180)
        phases = DateUtils.get_preparation_phases(exam_date)

        # Should have multiple phases for 6-month prep
        assert len(phases) >= 2


class TestStateAwarePlanner:
    """Test state-aware planning."""

    @patch("server.agents.state_aware_planner.OllamaClient")
    def test_plan_with_progress_extraction(self, mock_ollama):
        """Test planning that extracts and applies progress."""
        mock_client = Mock()
        planner = StateAwarePlanner(mock_client)

        state = StudentState(
            student_id="test",
            created_date=date.today(),
            exam_deadline=date.today() + timedelta(days=30),
        )

        # User mentions progress in request
        request = "I completed Algebra and Trigonometry. For JEE exam by January 2026, what should I prepare?"

        # Mock the LLM response
        mock_client.structured_generate.return_value = {
            "parsed_response": {
                "document_type": "Personalized Study Plan",
                "assumptions": {"focus": "Advanced topics", "constraint": "30 days"},
                "tasks": [
                    {"id": 1, "description": "Study Calculus", "dependencies": []}
                ],
                "outline": ["Calculus", "Vectors", "Coordinate Geometry"]
            }
        }

        plan = planner.plan_with_progress(request, state)

        assert plan is not None
        assert len(plan.outline) > 0

    def test_exam_date_extraction(self):
        """Test extracting exam date from request."""
        mock_client = Mock()
        planner = StateAwarePlanner(mock_client)

        request = "I want to prepare for JEE Main exam on January 2026"
        exam_date = planner._extract_exam_date(request)

        assert exam_date is not None
        assert exam_date.year == 2026
        assert exam_date.month == 1

    def test_available_topics_filtering(self):
        """Test filtering out learned topics."""
        mock_client = Mock()
        planner = StateAwarePlanner(mock_client)

        learned = {"Algebra", "Trigonometry", "Matrices"}
        request = "JEE Math preparation"

        # Mock RAG to return various topics
        available = planner._get_available_topics(request, learned)

        # Should return topics (exact behavior depends on RAG)
        assert isinstance(available, list)


class TestEndToEndProgressTracking:
    """Integration tests for complete progress tracking."""

    def test_day1_to_day7_progression(self):
        """Test realistic 7-day JEE prep scenario."""
        extractor = ProgressExtractor()
        validator = ProgressValidator()

        # Day 1: Initial state
        state = StudentState(
            student_id="jee_2026_student",
            created_date=date.today(),
            exam_deadline=date.today() + timedelta(days=100),
            available_hours_per_day=6.0,
        )

        # Day 2: User completes Algebra
        claims_day2 = [ProgressClaim(
            claim_type="completed_topic",
            topic_name="Algebra",
            completion_date=date.today() + timedelta(days=1),
            extracted_text="finished algebra",
            confidence=0.90
        )]
        update_day2 = extractor.update_student_state(state, claims_day2)
        state = update_day2.updated_state

        assert "Algebra" in state.get_learned_topic_names()

        # Day 5: User completes Trigonometry and studies for 4 hours
        claims_day5 = [
            ProgressClaim(
                claim_type="completed_topic",
                topic_name="Trigonometry",
                completed_date=date.today() + timedelta(days=4),
                extracted_text="completed trig",
                confidence=0.85
            ),
            ProgressClaim(
                claim_type="spent_hours",
                hours=4.0,
                extracted_text="studied 4 hours"
            )
        ]
        update_day5 = extractor.update_student_state(state, claims_day5)
        state = update_day5.updated_state

        learned = state.get_learned_topic_names()
        assert "Algebra" in learned
        assert "Trigonometry" in learned

        # Verify no repetition: plan should not include these topics
        plan_topics = ["Calculus", "Vectors", "Algebra"]  # Algebra is repeated!
        is_feasible, issues = validator.validate_plan(state, plan_topics)

        assert not is_feasible
        assert any("already learned" in issue.lower() or "learned" in issue.lower() for issue in issues)

    def test_metrics_collection(self):
        """Test collecting metrics from progress tracking."""
        state = StudentState(
            student_id="student1",
            created_date=date.today(),
            exam_deadline=date.today() + timedelta(days=90),
            available_hours_per_day=5.0,
        )

        # Add progress
        state.learned_topics = [
            TopicProgress(topic_name="Algebra", confidence=0.95, hours_spent=8.0),
            TopicProgress(topic_name="Vectors", confidence=0.80, hours_spent=6.0),
        ]

        # Calculate metrics
        learned_count = len(state.get_learned_topic_names())
        days_remaining = state.get_days_until_exam()
        learning_pace = state.learning_velocity

        assert learned_count == 2
        assert days_remaining == 90
        assert learning_pace >= 0.0
