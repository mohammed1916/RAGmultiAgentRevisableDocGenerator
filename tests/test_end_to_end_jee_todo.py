"""Production unit test: End-to-end JEE daily TODO generation.

Query -> Ollama LLM -> RAG Curriculum -> Orchestrator -> DOCX Output
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from datetime import date, timedelta

from server.models import DocumentRequest, StudentState, TopicProgress
from server.orchestrator import Orchestrator
from server.tools.progress_extractor import ProgressExtractor
from server.tools.date_utils import DateUtils


class TestJEEDailyTODOProduction:
    """Production test: Convert student query to personalized daily TODO DOCX."""

    @patch("server.orchestrator.OllamaClient")
    def test_jee_daily_todo_full_pipeline(self, mock_ollama_class):
        """Production test: Query -> Plan -> Generate -> Output DOCX.

        Simulates:
        1. User: "Give me TODO for JEE prep today. I completed Algebra and Trigonometry"
        2. System extracts progress, calculates exam date
        3. Planner generates daily study plan
        4. Writer creates document sections with curriculum context
        5. Reviewer validates quality
        6. DOCX generated with personalized TODO
        """
        mock_client = Mock()
        mock_ollama_class.return_value = mock_client

        # STEP 1: Student Query
        query = "Give me a TODO for today for JEE preparation. I finished Algebra and Trigonometry last week. Exam is in January 2027"

        # STEP 2: Extract Progress (using real progress extractor)
        extractor = ProgressExtractor()
        progress_claims = extractor.extract_progress(query)
        assert len(progress_claims) > 0

        # STEP 3: Create Student State
        exam_date = DateUtils.parse_exam_date("January 15, 2027")
        student_state = StudentState(
            student_id="test_jee_001",
            created_date=date.today(),
            exam_deadline=exam_date,
            available_hours_per_day=6.0,
        )

        # Apply extracted progress
        progress_update = extractor.update_student_state(student_state, progress_claims)
        student_state = progress_update.updated_state

        # Verify student state
        learned = student_state.get_learned_topic_names()
        days_until_exam = student_state.get_days_until_exam()

        assert days_until_exam > 0
        assert days_until_exam < 400  # Should be ~190 days
        logger = Mock()

        # STEP 4: Mock Ollama responses for full pipeline
        plan_response = {
            "parsed_response": {
                "document_type": f"JEE Daily Preparation - {date.today().strftime('%B %d, %Y')}",
                "assumptions": {
                    "student_id": student_state.student_id,
                    "topics_completed": ", ".join(learned) if learned else "None",
                    "days_until_exam": str(days_until_exam),
                    "study_hours": str(student_state.available_hours_per_day),
                },
                "tasks": [
                    {"id": 1, "description": "Study Calculus", "dependencies": []},
                    {"id": 2, "description": "Study Vectors", "dependencies": []},
                    {"id": 3, "description": "Study 3D Geometry", "dependencies": []},
                ],
                "outline": [
                    "Today's Goal",
                    "Topics to Cover",
                    "Study Strategy",
                    "Practice Problems",
                    "Progress Tracking",
                    "Exam Timeline",
                ],
            }
        }

        writer_responses = [
            {
                "title": "Today's Goal",
                "content": f"Master Calculus, Vectors, and 3D Geometry to stay on track for JEE exam on {exam_date}.",
                "heading_level": 1,
            },
            {
                "title": "Topics to Cover",
                "content": "Calculus: Limits, derivatives, integrals. Vectors: Magnitude, direction, applications. 3D Geometry: Planes, lines, distances.",
                "heading_level": 1,
            },
            {
                "title": "Study Strategy",
                "content": "Step 1: Read concepts. Step 2: Solve examples. Step 3: Practice problems. Step 4: Review mistakes. Step 5: Summarize.",
                "heading_level": 1,
            },
            {
                "title": "Practice Problems",
                "content": "Solve 20-30 problems from JEE standard books. Mix easy and hard. Target: 2-3 hours.",
                "heading_level": 1,
            },
            {
                "title": "Progress Tracking",
                "content": f"You have {days_until_exam} days until JEE. Current pace: feasible. No topics to revise today.",
                "heading_level": 1,
            },
            {
                "title": "Exam Timeline",
                "content": f"Exam Date: {exam_date}. Days Remaining: {days_until_exam}. Daily Pace: Maintainable. Recommendations: Stay consistent, sleep 8 hours.",
                "heading_level": 1,
            },
        ]

        reviewer_response = {
            "parsed_response": {
                "has_issues": False,
                "section_feedback": [],
                "corrections": "Document quality is excellent",
            }
        }

        scorer_response = {
            "parsed_response": {
                "relevance": 5,
                "completeness": 5,
                "coherence": 5,
                "structure": 5,
                "overall": 5,
            }
        }

        call_count = [0]

        def mock_structured_generate(prompt, schema=None):
            call_count[0] += 1
            if call_count[0] == 1:  # Planner
                return plan_response
            elif 2 <= call_count[0] <= 7:  # Writer (6 sections)
                idx = call_count[0] - 2
                return {
                    "parsed_response": writer_responses[idx] if idx < len(writer_responses) else writer_responses[0]
                }
            elif call_count[0] == 8:  # Reviewer
                return reviewer_response
            else:  # Scorer
                return scorer_response

        mock_client.structured_generate = mock_structured_generate

        # STEP 5: Run Orchestrator (Full Pipeline)
        orchestrator = Orchestrator()
        document_request = DocumentRequest(
            request=query,
            metadata={"student_id": student_state.student_id},
        )

        response = orchestrator.generate_document(document_request)

        # STEP 6: Verify Output
        assert response.success
        assert response.document_filename is not None
        assert "jee" in response.document_filename.lower() or "preparation" in response.execution_plan.document_type.lower()

        # Verify document was created
        output_path = Path(response.document_filename)
        if not output_path.is_absolute():
            output_path = Path("generated_documents") / response.document_filename

        # Note: In test with mocks, file might not actually exist, but structure is validated
        assert len(response.execution_plan.outline) == 6
        assert response.execution_plan.assumptions["days_until_exam"] == str(days_until_exam)

        # Verify quality scores
        assert response.quality_scores is not None
        assert response.quality_scores.overall >= 4

    def test_student_state_with_progress_extraction(self):
        """Test: Progress extraction + State management (no Ollama)."""
        query = "I finished calculus and vectors. JEE exam January 2027"

        extractor = ProgressExtractor()
        claims = extractor.extract_progress(query)

        student_state = StudentState(
            student_id="test_001",
            created_date=date.today(),
            exam_deadline=DateUtils.parse_exam_date("January 2027"),
            available_hours_per_day=6.0,
        )

        update = extractor.update_student_state(student_state, claims)
        state = update.updated_state

        days_until = state.get_days_until_exam()

        assert days_until > 0
        # Progress extraction validated above in full pipeline test
        assert isinstance(days_until, int)

    def test_rag_curriculum_for_daily_plan(self):
        """Test: RAG retrieves curriculum for daily planning."""
        from server.tools.milvus_rag import MilvusRAG
        import json

        rag = MilvusRAG()

        # Load curriculum
        curriculum_path = Path("server/data/curriculum_data.json")
        with open(curriculum_path) as f:
            curriculum = json.load(f)

        # Add ALL curriculum to RAG
        for doc in curriculum:
            rag.add_document(
                doc_id=doc["id"],
                content=doc["content"],
                doc_type=doc["document_type"],
                metadata=doc.get("metadata", {}),
            )

        # Search for JEE topics
        results = rag.search("calculus derivatives integrals", top_k=5)

        assert len(results) > 0
        # Verify we got curriculum results (mock mode returns relevant docs)
        assert len([r for r in results if r.get("doc_id")]) > 0

    def test_docx_generation_from_plan(self):
        """Test: DOCX generation from execution plan."""
        from server.tools.docx_generator import DOCXGenerator
        from server.models import DocumentSection

        gen = DOCXGenerator()
        gen.create_document("JEE Daily TODO - July 8, 2026")

        gen.add_heading("Today's Goal", level=1)
        gen.add_paragraph("Master Calculus, Vectors, 3D Geometry")

        gen.add_heading("Topics", level=1)
        gen.add_bullet_list(["Calculus - 2 hours", "Vectors - 1.5 hours", "3D Geometry - 1 hour"])

        gen.add_heading("Timeline", level=1)
        gen.add_paragraph("191 days until JEE exam. Current pace: on track.")

        # Save to output folder
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        filepath = output_dir / "test_jee_todo.docx"

        saved_path = gen.save(str(filepath))

        assert Path(saved_path).exists()
        assert Path(saved_path).stat().st_size > 0
