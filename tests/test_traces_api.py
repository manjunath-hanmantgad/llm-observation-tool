from __future__ import annotations

from fastapi.testclient import TestClient

from gateway.gateway import app
from tests.test_enterprise_api import register_user


def test_llm_calls_and_trace_detail_endpoints() -> None:
    client = TestClient(app)
    token, suffix = register_user(client)
    auth_headers = {"Authorization": f"Bearer {token}"}

    project = client.post(
        "/api/v1/projects",
        headers=auth_headers,
        json={"name": "Trace Project", "slug": f"trace-{suffix}"},
    )
    project_id = project.json()["id"]
    key = client.post("/api/v1/api-keys", headers=auth_headers, json={"name": "trace-key", "project_id": project_id})
    api_key = key.json()["api_key"]
    trace_id = f"trace-list-{suffix}"

    ingest = client.post(
        "/api/v1/ingest/llm-calls",
        headers={"X-API-Key": api_key},
        json={
            "project_id": project_id,
            "trace_id": trace_id,
            "provider": "mock",
            "model": "mock-observatory-model",
            "prompt": "Trace prompt",
            "response": "Trace response",
            "latency_ms": 333,
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "total_cost_usd": 0.01,
        },
    )
    assert ingest.status_code == 201, ingest.text

    listed = client.get(f"/api/v1/llm-calls?project_id={project_id}&search={trace_id}", headers=auth_headers)
    assert listed.status_code == 200, listed.text
    assert listed.json()["total"] >= 1
    assert listed.json()["items"][0]["trace_id"] == trace_id

    detail = client.get(f"/api/v1/traces/{trace_id}", headers=auth_headers)
    assert detail.status_code == 200, detail.text
    assert detail.json()["call"]["trace_id"] == trace_id
    assert detail.json()["prompt"] == "Trace prompt"
