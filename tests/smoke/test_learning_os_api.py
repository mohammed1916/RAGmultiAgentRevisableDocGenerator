"""Smoke tests for the AI Learning Operating System foundation API."""

from fastapi.testclient import TestClient

from server.api import app


client = TestClient(app)


def test_learning_specification_endpoint():
    response = client.get("/learning/spec")

    assert response.status_code == 200
    assert response.json()["phase"] == "foundation"


def test_profile_workspace_document_flow_is_isolated():
    profile_response = client.post(
        "/learning/profiles",
        json={
            "user_id": "learner-1",
            "name": "Physics Boards",
            "exam": "CBSE",
            "daily_study_hours": 3,
            "timezone": "Asia/Kolkata",
        },
    )
    assert profile_response.status_code == 201
    profile = profile_response.json()

    preferences_response = client.patch(
        f"/learning/profiles/{profile['profile_id']}/preferences?user_id=learner-1",
        json={"preferences": {"revision_strategy": "spaced"}},
    )
    assert preferences_response.status_code == 200
    assert preferences_response.json()["preferences"]["revision_strategy"] == "spaced"

    workspace_response = client.post(
        "/learning/workspaces",
        json={
            "user_id": "learner-1",
            "profile_id": profile["profile_id"],
            "name": "Physics Notes",
        },
    )
    assert workspace_response.status_code == 201
    workspace = workspace_response.json()

    document_response = client.post(
        "/learning/documents",
        json={
            "user_id": "learner-1",
            "profile_id": profile["profile_id"],
            "workspace_id": workspace["workspace_id"],
            "title": "Ohm's Law",
            "subject": "Physics",
            "chapter": "Current Electricity",
            "tags": ["formula", "revision"],
            "content": "V = IR",
        },
    )
    assert document_response.status_code == 201
    document = document_response.json()
    assert document["version"] == 1

    documents_response = client.get(
        f"/learning/profiles/{profile['profile_id']}/documents?user_id=learner-1"
    )
    assert documents_response.status_code == 200
    assert [item["document_id"] for item in documents_response.json()] == [
        document["document_id"]
    ]

    unauthorized_response = client.get(
        f"/learning/documents/{document['document_id']}?user_id=another-user"
    )
    assert unauthorized_response.status_code == 404


def test_document_rejects_workspace_from_another_profile():
    first_profile = client.post(
        "/learning/profiles",
        json={"user_id": "learner-2", "name": "Mathematics"},
    ).json()
    second_profile = client.post(
        "/learning/profiles",
        json={"user_id": "learner-2", "name": "Chemistry"},
    ).json()
    workspace = client.post(
        "/learning/workspaces",
        json={
            "user_id": "learner-2",
            "profile_id": first_profile["profile_id"],
            "name": "Math Workspace",
        },
    ).json()

    response = client.post(
        "/learning/documents",
        json={
            "user_id": "learner-2",
            "profile_id": second_profile["profile_id"],
            "workspace_id": workspace["workspace_id"],
            "title": "Invalid document",
        },
    )

    assert response.status_code == 409
