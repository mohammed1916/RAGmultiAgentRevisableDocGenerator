"""Tests for the FastAPI endpoints."""

from unittest.mock import Mock, patch, MagicMock
import pytest
from fastapi.testclient import TestClient

from server.base.models import (
    DocumentRequest,
    DocumentResponse,
    ExecutionPlan,
    Task,
    QualityScore,
    PipelineMetrics,
)


# Mock the Orchestrator before importing the API
@patch("server.api.Orchestrator")
def test_api_imports(mock_orchestrator):
    """Test that API imports successfully."""
    from server.api import app

    assert app is not None


@pytest.fixture
def client():
    """Provide a test client."""
    with patch("server.api.Orchestrator") as mock_orchestrator:
        # Configure the mock
        mock_instance = MagicMock()
        mock_orchestrator.return_value = mock_instance

        from server.api import app

        return TestClient(app)


def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_root_endpoint(client):
    """Test root endpoint."""
    response = client.get("/")

    assert response.status_code == 200
    data = response.json()
    assert "endpoints" in data


def test_metrics_endpoint(client):
    """Test metrics endpoint."""
    response = client.get("/metrics")

    assert response.status_code == 200


@patch("server.api.Orchestrator")
def test_generate_document_success(mock_orchestrator_class):
    """Test successful document generation."""
    # Setup mock
    mock_orchestrator = MagicMock()

    mock_response = DocumentResponse(
        success=True,
        document_filename="test_doc.docx",
        execution_plan=ExecutionPlan(
            document_type="Report",
            assumptions={},
            tasks=[Task(id=1, description="Task 1", dependencies=[])],
            outline=["Intro"],
        ),
        assumptions={},
        metrics=PipelineMetrics(
            planner_latency_ms=100,
            writer_latency_ms=200,
            reviewer_latency_ms=150,
            docx_generation_latency_ms=50,
            total_execution_time_ms=500,
            num_generated_tasks=1,
            review_iterations=1,
        ),
        quality_scores=QualityScore(
            relevance=5,
            completeness=4,
            coherence=5,
            structure=5,
            overall=4,
        ),
        message="Success",
    )

    mock_orchestrator.generate_document.return_value = mock_response
    mock_orchestrator_class.return_value = mock_orchestrator

    from server.api import app

    client = TestClient(app)

    response = client.post(
        "/agent",
        json={"request": "Create a technical document about AI"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["document_filename"] == "test_doc.docx"


@patch("server.api.Orchestrator")
def test_generate_document_empty_request(mock_orchestrator_class):
    """Test document generation with empty request."""
    mock_orchestrator_class.return_value = MagicMock()

    from server.api import app

    client = TestClient(app)

    response = client.post(
        "/agent",
        json={"request": ""},
    )

    assert response.status_code == 400


@patch("server.api.Orchestrator")
def test_generate_document_invalid_request(mock_orchestrator_class):
    """Test document generation with invalid request."""
    mock_orchestrator_class.return_value = MagicMock()

    from server.api import app

    client = TestClient(app)

    response = client.post(
        "/agent",
        json={"request": "   "},  # Just whitespace
    )

    assert response.status_code == 400


@patch("server.api.Orchestrator")
def test_generate_document_server_error(mock_orchestrator_class):
    """Test document generation with server error."""
    from server.base.exceptions import DocumentGenerationException

    mock_orchestrator = MagicMock()
    mock_orchestrator.generate_document.side_effect = DocumentGenerationException(
        "Test error"
    )
    mock_orchestrator_class.return_value = mock_orchestrator

    from server.api import app

    client = TestClient(app)

    response = client.post(
        "/agent",
        json={"request": "Create a document"},
    )

    assert response.status_code == 500


@patch("server.api.Orchestrator")
def test_generate_document_unexpected_error(mock_orchestrator_class):
    """Test document generation with unexpected error."""
    mock_orchestrator = MagicMock()
    mock_orchestrator.generate_document.side_effect = Exception("Unexpected error")
    mock_orchestrator_class.return_value = mock_orchestrator

    from server.api import app

    client = TestClient(app)

    response = client.post(
        "/agent",
        json={"request": "Create a document"},
    )

    assert response.status_code == 500


def test_request_model_validation(client):
    """Test request model validation."""
    # Missing required field
    response = client.post("/agent", json={})

    assert response.status_code == 422  # Unprocessable Entity
