"""Pytest configuration and shared fixtures for all tests."""

import pytest
import sys
from pathlib import Path

# Add parent directory to path so tests can import server modules
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def sample_document_request():
    """Sample document request for testing."""
    return {
        "request": "Create a 2-day study plan for JEE Mathematics",
        "metadata": {
            "subject": "Mathematics",
            "level": "JEE",
            "scope": "Relations and Functions"
        }
    }


@pytest.fixture
def sample_execution_plan():
    """Sample execution plan for testing."""
    from server.base.models import ExecutionPlan, Task

    return ExecutionPlan(
        document_type="JEE Mathematics Study Plan",
        assumptions={
            "exam_date": "12 months from now",
            "daily_study_hours": "6 hours",
            "current_level": "Intermediate",
        },
        tasks=[
            Task(id=1, description="Study Relations and Functions", dependencies=[]),
            Task(id=2, description="Practice 50 problems", dependencies=[1]),
            Task(id=3, description="Complete Mock Test", dependencies=[2]),
        ],
        outline=[
            "Executive Summary",
            "Topics to Cover",
            "Study Schedule",
        ],
    )


@pytest.fixture
def mock_milvus_rag():
    """Mock MilvusRAG instance for testing."""
    from server.tools import MilvusRAG

    # Creates a mock instance (in mock mode since no real Milvus running in tests)
    return MilvusRAG()


@pytest.fixture
def sample_chunks():
    """Sample curriculum chunks for testing."""
    return [
        {
            "chunk_id": "test_001",
            "document_id": "test_doc",
            "chunk_text": "This is a test chunk about Relations and Functions",
            "embedding": None,
            "metadata": {
                "topic": "Relations and Functions",
                "difficulty": "Basic",
                "chapter": 1,
            },
        },
        {
            "chunk_id": "test_002",
            "document_id": "test_doc",
            "chunk_text": "This is a test chunk about Matrices and Determinants",
            "embedding": None,
            "metadata": {
                "topic": "Matrices",
                "difficulty": "Intermediate",
                "chapter": 2,
            },
        },
    ]


@pytest.fixture
def mock_ollama_client():
    """Mock OllamaClient for testing."""
    from server.tools import OllamaClient

    try:
        return OllamaClient()
    except Exception:
        # If Ollama not available, return None (tests should handle this)
        return None
