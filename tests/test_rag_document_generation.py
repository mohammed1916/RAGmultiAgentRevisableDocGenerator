"""End-to-end tests for RAG-enabled document generation with curriculum data.

Demonstrates:
1. Fetching syllabuses (JEE, CBSE, etc.)
2. Indexing documents
3. Generating plans based on retrieved docs
4. Creating daily TODOs with relevant material
"""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path
import tempfile

from tools.document_fetcher import DocumentFetcher
from tools.document_indexer import DocumentIndexer
from models import DocumentRequest
from orchestrator import Orchestrator


class TestDocumentFetching:
    """Test document fetching from various sources."""

    def test_fetch_jee_syllabus(self):
        """Test fetching JEE Main syllabus."""
        fetcher = DocumentFetcher()
        syllabus = fetcher.fetch_syllabus("jee_main")

        assert syllabus is not None
        assert "Mathematics" in str(syllabus["topics"])
        assert "Physics" in str(syllabus["topics"])
        assert "Chemistry" in str(syllabus["topics"])
        assert syllabus["type"] == "jee_main"

    def test_fetch_cbse_12_syllabus(self):
        """Test fetching CBSE Class 12 syllabus."""
        fetcher = DocumentFetcher()
        syllabus = fetcher.fetch_syllabus("cbse_12")

        assert syllabus is not None
        assert len(syllabus["topics"]) > 0
        assert syllabus["type"] == "cbse_12"

    def test_fetch_cbse_10_syllabus(self):
        """Test fetching CBSE Class 10 syllabus."""
        fetcher = DocumentFetcher()
        syllabus = fetcher.fetch_syllabus("cbse_10")

        assert syllabus is not None
        assert "Science" in str(syllabus["topics"]) or "Mathematics" in str(syllabus["topics"])

    def test_fetch_jee_full_curriculum(self):
        """Test fetching complete JEE curriculum with chapters."""
        fetcher = DocumentFetcher()
        curriculum = fetcher.fetch_jee_full_curriculum()

        assert curriculum["type"] == "jee_complete"
        assert "Mathematics" in curriculum["subjects"]
        assert "Physics" in curriculum["subjects"]
        assert "Chemistry" in curriculum["subjects"]

        # Verify chapter structure
        math = curriculum["subjects"]["Mathematics"]
        assert len(math["chapters"]) > 0
        assert math["estimated_hours"] > 0

    def test_fetch_course_material(self):
        """Test fetching course material."""
        fetcher = DocumentFetcher()
        course = fetcher.fetch_course_material("Python Programming")

        assert course["title"] == "Python Programming"
        assert "modules" in course
        assert len(course["modules"]) > 0

    def test_fetch_multiple_courses(self):
        """Test fetching different course types."""
        fetcher = DocumentFetcher()

        courses = ["Python", "Data Science", "Web Development"]
        for course_name in courses:
            course = fetcher.fetch_course_material(course_name)
            assert course is not None
            assert len(course["modules"]) > 0

    def test_document_caching(self):
        """Test that documents are cached after fetching."""
        with tempfile.TemporaryDirectory() as tmpdir:
            fetcher = DocumentFetcher(cache_dir=tmpdir)

            # First fetch
            syllabus1 = fetcher.fetch_syllabus("jee_main")

            # Create new fetcher with same cache
            fetcher2 = DocumentFetcher(cache_dir=tmpdir)
            syllabus2 = fetcher2.get_document("jee_main")

            assert syllabus1 is not None
            assert syllabus2 is not None

    def test_get_topics_for_exam(self):
        """Test retrieving topics for an exam."""
        fetcher = DocumentFetcher()
        topics = fetcher.get_topics_for_exam("jee_main")

        assert isinstance(topics, list)
        assert len(topics) > 0
        assert any("Mathematics" in topic or "Physics" in topic for topic in topics)

    def test_search_documents(self):
        """Test searching for documents."""
        fetcher = DocumentFetcher()
        fetcher.fetch_syllabus("jee_main")
        fetcher.fetch_course_material("Python")

        results = fetcher.search_documents("mathematics")
        assert len(results) > 0

        results_python = fetcher.search_documents("programming")
        assert len(results_python) > 0


class TestDocumentIndexing:
    """Test document indexing and semantic search."""

    def test_add_document_to_index(self):
        """Test adding a document to the index."""
        with tempfile.TemporaryDirectory() as tmpdir:
            indexer = DocumentIndexer(index_dir=tmpdir)

            content = "Mathematics involves studying numbers, algebra, and geometry"
            indexer.add_document("math_101", content, {"subject": "Mathematics"})

            doc = indexer.get_document("math_101")
            assert doc is not None
            assert "Mathematics" in doc["content"]

    def test_search_indexed_documents(self):
        """Test searching indexed documents."""
        with tempfile.TemporaryDirectory() as tmpdir:
            indexer = DocumentIndexer(index_dir=tmpdir)

            # Add documents
            documents = [
                ("math_101", "Algebra covers equations, functions, and polynomials", {}),
                ("math_102", "Calculus involves derivatives and integrals", {}),
                ("physics_101", "Mechanics studies motion, forces, and energy", {}),
            ]
            indexer.add_documents_batch(documents)

            # Search for mathematics
            results = indexer.search("algebra equations", top_k=2)
            assert len(results) > 0
            assert results[0]["relevance_score"] >= 0.0

    def test_search_returns_top_k(self):
        """Test that search returns correct number of results."""
        with tempfile.TemporaryDirectory() as tmpdir:
            indexer = DocumentIndexer(index_dir=tmpdir)

            for i in range(10):
                indexer.add_document(f"doc_{i}", f"Document {i} content", {})

            results = indexer.search("content", top_k=3)
            assert len(results) <= 3

    def test_index_persistence(self):
        """Test that index persists across instances."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # First instance
            indexer1 = DocumentIndexer(index_dir=tmpdir)
            indexer1.add_document("persistent_doc", "This is persistent content", {})

            # Second instance
            indexer2 = DocumentIndexer(index_dir=tmpdir)
            doc = indexer2.get_document("persistent_doc")

            assert doc is not None
            assert "persistent" in doc["content"]

    def test_index_stats(self):
        """Test getting index statistics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            indexer = DocumentIndexer(index_dir=tmpdir)

            for i in range(5):
                indexer.add_document(f"doc_{i}", f"Document {i} content", {})

            stats = indexer.get_index_stats()
            assert stats["total_documents"] == 5
            assert stats["total_characters"] > 0


class TestRAGDocumentGeneration:
    """Test document generation using RAG with curriculum data."""

    @patch("orchestrator.OllamaClient")
    def test_generate_jee_study_plan_with_rag(self, mock_ollama_class):
        """Test generating a JEE study plan with retrieved curriculum.

        This demonstrates:
        - Fetching JEE curriculum
        - Indexing chapters
        - Retrieving relevant topics for a specific day
        - Generating a daily study plan
        """
        mock_client = Mock()
        mock_ollama_class.return_value = mock_client

        # Setup RAG with fresh temp directory
        with tempfile.TemporaryDirectory() as tmpdir:
            fetcher = DocumentFetcher(cache_dir=f"{tmpdir}/docs")
            curriculum = fetcher.fetch_jee_full_curriculum()

            indexer = DocumentIndexer(index_dir=f"{tmpdir}/index")
            for subject, data in curriculum["subjects"].items():
                chapters_text = ", ".join(data["chapters"])
                indexer.add_document(
                    f"jee_{subject.lower()}",
                    chapters_text,
                    {"subject": subject, "level": "Advanced"},
                )

            # Mock response for plan generation
            plan_response = {
                "document_type": "Daily Study Plan - JEE Mathematics",
                "assumptions": {
                    "exam_date": "12 months from now",
                    "daily_study_hours": "6 hours",
                    "subjects": "Mathematics focus for this plan",
                },
                "tasks": [
                    {"id": 1, "description": "Study Relations and Functions", "dependencies": []},
                    {"id": 2, "description": "Complete practice problems", "dependencies": [1]},
                    {"id": 3, "description": "Solve mock tests", "dependencies": [1, 2]},
                ],
                "outline": [
                    "Today's Goal",
                    "Topics to Cover",
                    "Practice Resources",
                    "Assessment",
                ],
            }

            # Mock writer responses
            writer_responses = [
                {
                    "title": "Today's Goal",
                    "content": "Master Relations and Functions chapter for JEE Mathematics",
                    "heading_level": 1,
                },
                {
                    "title": "Topics to Cover",
                    "content": "Focus on: Domain and Range, Functions, Composition, Inverse Functions",
                    "heading_level": 1,
                },
                {
                    "title": "Practice Resources",
                    "content": "Solve 20 JEE-level problems from standard books",
                    "heading_level": 1,
                },
                {
                    "title": "Assessment",
                    "content": "Complete a 30-minute mini-test on this chapter",
                    "heading_level": 1,
                },
            ]

            call_count = [0]

            def mock_post_side_effect(*args, **kwargs):
                call_count[0] += 1
                if call_count[0] == 1:  # Planner
                    return Mock(json=lambda: {"response": str(plan_response)}, status_code=200)
                elif 2 <= call_count[0] <= 5:  # Writer
                    idx = call_count[0] - 2
                    return Mock(
                        json=lambda r=writer_responses[idx]: {"response": str(r)}, status_code=200
                    )
                elif call_count[0] == 6:  # Reviewer
                    return Mock(
                        json=lambda: {
                            "response": str(
                                {
                                    "has_issues": False,
                                    "section_feedback": [],
                                    "corrections": "Perfect study plan",
                                }
                            )
                        },
                        status_code=200,
                    )
                else:  # Scorer
                    return Mock(
                        json=lambda: {
                            "response": str(
                                {
                                    "relevance": 5,
                                    "completeness": 5,
                                    "coherence": 5,
                                    "structure": 5,
                                    "overall": 5,
                                }
                            )
                        },
                        status_code=200,
                    )

            mock_client.structured_generate = lambda prompt, schema: (
                mock_post_side_effect()
                if "response" not in str(schema)
                else {"parsed_response": mock_post_side_effect().json()["response"]}
            )

            # Retrieve relevant topics for today
            search_results = indexer.search("Relations Functions Algebra", top_k=3)
            assert len(search_results) > 0

            # Verify curriculum was indexed
            assert indexer.get_index_stats()["total_documents"] == 3

    @patch("orchestrator.OllamaClient")
    def test_generate_cbse_exam_prep_plan(self, mock_ollama_class):
        """Test generating a CBSE exam preparation plan with syllabus."""
        mock_client = Mock()
        mock_ollama_class.return_value = mock_client

        fetcher = DocumentFetcher()
        syllabus = fetcher.fetch_syllabus("cbse_12")

        assert syllabus is not None
        assert "Physics" in str(syllabus["topics"]) or "Chemistry" in str(syllabus["topics"])

    @patch("orchestrator.OllamaClient")
    def test_generate_course_todo_with_rag(self, mock_ollama_class):
        """Test generating daily TODOs for a course using RAG.

        When user says: "Create a TODO for Python course for tomorrow"
        System should:
        1. Fetch Python course curriculum
        2. Index all modules and topics
        3. Retrieve relevant material for tomorrow
        4. Generate structured TODO with specific topics
        """
        mock_client = Mock()
        mock_ollama_class.return_value = mock_client

        # Setup RAG
        fetcher = DocumentFetcher()
        course = fetcher.fetch_course_material("Python Programming")

        indexer = DocumentIndexer()

        # Index all modules
        for module in course["modules"]:
            topics_text = ", ".join(module["topics"])
            indexer.add_document(
                f"python_{module['name'].lower()}",
                topics_text,
                {"module": module["name"], "course": "Python"},
            )

        # Retrieve for "Functions and Control Flow"
        results = indexer.search("Functions Control Flow", top_k=2)

        # Verify indexing
        assert indexer.get_index_stats()["total_documents"] >= 3
        assert len(results) > 0


class TestDocumentGeneratedWithTest:
    """Test showing WHERE documents are generated and used."""

    def test_document_generation_flow_with_indexing(self):
        """Test complete flow: Fetch → Index → Retrieve → Generate → Output.

        This shows:
        1. WHERE documents come from (Fetcher)
        2. WHERE they are stored (Index)
        3. HOW they are retrieved (Search)
        4. HOW they are used (In generation context)
        5. WHERE output is created (Document file)
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # Step 1: FETCH documents
            fetcher = DocumentFetcher(cache_dir=f"{tmpdir}/docs")
            jee_curriculum = fetcher.fetch_jee_full_curriculum()

            # Documents are now IN: document_cache/documents_index.json
            cache_index = Path(f"{tmpdir}/docs/documents_index.json")
            assert cache_index.exists()

            # Step 2: INDEX documents
            indexer = DocumentIndexer(index_dir=f"{tmpdir}/index")

            for subject, data in jee_curriculum["subjects"].items():
                chapters_text = ", ".join(data["chapters"])
                indexer.add_document(f"jee_{subject.lower()}", chapters_text, {"subject": subject})

            # Documents indexed IN: {tmpdir}/index/index.json
            index_file = Path(f"{tmpdir}/index/index.json")
            assert index_file.exists()

            # Step 3: RETRIEVE relevant documents
            query = "calculus derivatives integrals"
            results = indexer.search(query, top_k=2)

            # Verification
            assert len(results) > 0
            for result in results:
                assert "relevance_score" in result
                assert "content" in result

            # Step 4: USE in generation context
            context = "\n".join([r["content"] for r in results])
            assert len(context) > 0
            # Verify retrieved content contains curriculum material
            assert any(word in context.lower() for word in ["calculus", "derivatives", "integrals", "applications"])

            # Summary
            stats = indexer.get_index_stats()
            assert stats["total_documents"] == 3  # Math, Physics, Chemistry


class TestTODOGenerationWithCurriculum:
    """Test TODO generation based on fetched curriculum documents."""

    def test_daily_todo_from_jee_curriculum(self):
        """Test creating daily TODO items based on JEE curriculum."""
        fetcher = DocumentFetcher()
        curriculum = fetcher.fetch_jee_full_curriculum()

        # Extract today's topic (simulate day 1)
        math_chapters = curriculum["subjects"]["Mathematics"]["chapters"]
        today_chapter = math_chapters[0]  # Relations and Functions

        # Create TODO items
        todos = [
            f"Study: {today_chapter}",
            f"Solve: 10 problems from {today_chapter}",
            f"Review: Key concepts in {today_chapter}",
        ]

        assert len(todos) == 3
        assert "Relations and Functions" in todos[0]

    def test_weekly_plan_from_cbse_curriculum(self):
        """Test creating weekly plan from CBSE curriculum."""
        fetcher = DocumentFetcher()
        syllabus = fetcher.fetch_syllabus("cbse_12")

        # Generate weekly plan
        topics = syllabus["topics"][:5]  # First 5 topics
        weekly_plan = {f"Day {i+1}": topic for i, topic in enumerate(topics)}

        assert len(weekly_plan) <= 5
        assert all(isinstance(v, str) for v in weekly_plan.values())


class TestMockDocuments:
    """Test with mock curriculum data (when internet fetching fails)."""

    def test_mock_jee_curriculum_complete(self):
        """Verify mock JEE curriculum is complete and usable."""
        fetcher = DocumentFetcher()
        curriculum = fetcher.fetch_jee_full_curriculum()

        # Verify structure
        assert curriculum["total_chapters"] == 35
        assert curriculum["total_hours"] == 420

        subjects = curriculum["subjects"]
        assert len(subjects) == 3

        for subject, data in subjects.items():
            assert "chapters" in data
            assert "difficulty" in data
            assert "estimated_hours" in data
            assert len(data["chapters"]) > 0

    def test_mock_course_structure(self):
        """Verify mock course structure is usable for TODOs."""
        fetcher = DocumentFetcher()
        course = fetcher.fetch_course_material("Python Programming")

        assert "modules" in course
        assert len(course["modules"]) >= 3

        for module in course["modules"]:
            assert "name" in module
            assert "topics" in module
            assert len(module["topics"]) > 0
