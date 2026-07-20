"""Tests for the FastAPI endpoints.

The app initializes its shared resources (DB-backed service, orchestrators) in a
lifespan handler and stores them on ``app.state``. Tests therefore run the client
as a context manager and override ``app.state`` for generation scenarios. A
database must be reachable (DATABASE_URL / POSTGRES_* env vars).
"""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from server.api import app
from server.base.models import (
    DocumentResponse,
    ExecutionPlan,
    Task,
    QualityScore,
    PipelineMetrics,
)
from server.base.exceptions import DocumentGenerationException


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_api_imports():
    """The app object exists and is importable."""
    assert app is not None


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    # DB is required, so a passing lifespan means healthy.
    assert data["status"] == "healthy"
    assert data["database"] == "up"


def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "endpoints" in response.json()


def test_metrics_endpoint(client):
    response = client.get("/metrics")
    assert response.status_code == 200


def _sample_response() -> DocumentResponse:
    return DocumentResponse(
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
            relevance=5, completeness=4, coherence=5, structure=5, overall=4
        ),
        message="Success",
    )


def test_generate_document_success(client):
    mock = MagicMock()
    mock.generate_document.return_value = _sample_response()
    original = client.app.state.orchestrator
    client.app.state.orchestrator = mock
    try:
        response = client.post("/agent", json={"request": "Create a technical document about AI"})
    finally:
        client.app.state.orchestrator = original

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["document_filename"] == "test_doc.docx"


def test_generate_document_empty_request(client):
    response = client.post("/agent", json={"request": ""})
    assert response.status_code == 400


def test_generate_document_invalid_request(client):
    response = client.post("/agent", json={"request": "   "})
    assert response.status_code == 400


def test_generate_document_server_error(client):
    mock = MagicMock()
    mock.generate_document.side_effect = DocumentGenerationException("Test error")
    original = client.app.state.orchestrator
    client.app.state.orchestrator = mock
    try:
        response = client.post("/agent", json={"request": "Create a document"})
    finally:
        client.app.state.orchestrator = original
    assert response.status_code == 500


def test_generate_document_unexpected_error(client):
    mock = MagicMock()
    mock.generate_document.side_effect = Exception("Unexpected error")
    original = client.app.state.orchestrator
    client.app.state.orchestrator = mock
    try:
        response = client.post("/agent", json={"request": "Create a document"})
    finally:
        client.app.state.orchestrator = original
    assert response.status_code == 500


def test_request_model_validation(client):
    response = client.post("/agent", json={})
    assert response.status_code == 422
