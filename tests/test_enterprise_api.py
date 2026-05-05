from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from gateway.gateway import app


def register_user(client: TestClient) -> tuple[str, str]:
    suffix = uuid.uuid4().hex[:8]
    response = client.post(
        "/api/v1/auth/register",
        json={
            "organization_name": f"Acme {suffix}",
            "organization_slug": f"acme-{suffix}",
            "email": f"owner-{suffix}@example.com",
            "password": "correct-horse-battery-staple",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["access_token"], suffix


def test_register_create_project_api_key_ingest_and_metrics() -> None:
    client = TestClient(app)
    token, suffix = register_user(client)
    headers = {"Authorization": f"Bearer {token}"}

    project_response = client.post(
        "/api/v1/projects",
        headers=headers,
        json={"name": "Support Assistant", "slug": f"support-{suffix}", "description": "Support LLM calls"},
    )
    assert project_response.status_code == 201, project_response.text
    project_id = project_response.json()["id"]

    endpoint_response = client.post(
        "/api/v1/endpoints",
        headers=headers,
        json={"project_id": project_id, "name": "Refund Flow", "slug": f"refund-{suffix}"},
    )
    assert endpoint_response.status_code == 201, endpoint_response.text
    endpoint_id = endpoint_response.json()["id"]

    key_response = client.post(
        "/api/v1/api-keys",
        headers=headers,
        json={"name": "ingestion-key", "project_id": project_id},
    )
    assert key_response.status_code == 201, key_response.text
    api_key = key_response.json()["api_key"]
    assert api_key.startswith("lo_")

    ingest_response = client.post(
        "/api/v1/ingest/llm-calls",
        headers={"X-API-Key": api_key},
        json={
            "project_id": project_id,
            "endpoint_id": endpoint_id,
            "trace_id": f"trace-{suffix}",
            "provider": "mock",
            "model": "mock-observatory-model",
            "prompt": "Customer asks for a refund",
            "response": "Route to support.",
            "latency_ms": 123,
            "prompt_tokens": 12,
            "completion_tokens": 5,
            "total_cost_usd": 0,
        },
    )
    assert ingest_response.status_code == 201, ingest_response.text

    metrics_response = client.get(f"/api/v1/metrics/summary?project_id={project_id}", headers=headers)
    assert metrics_response.status_code == 200, metrics_response.text
    metrics = metrics_response.json()
    assert metrics["total_calls"] >= 1
    assert metrics["avg_latency_ms"] >= 123


def test_metrics_requires_bearer_token() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/metrics/summary")
    assert response.status_code == 401


def test_ingest_rejects_missing_api_key() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/v1/ingest/llm-calls",
        json={
            "project_id": str(uuid.uuid4()),
            "trace_id": "trace-missing-key",
            "provider": "mock",
            "model": "mock",
        },
    )
    assert response.status_code == 401
