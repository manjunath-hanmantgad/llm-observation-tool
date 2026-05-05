from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from gateway.gateway import app


def _workspace(client: TestClient) -> tuple[dict[str, str], dict[str, str], str]:
    suffix = uuid.uuid4().hex[:8]
    register = client.post(
        "/api/v1/auth/register",
        json={
            "organization_name": f"EvalCo {suffix}",
            "organization_slug": f"evalco-{suffix}",
            "email": f"owner-{suffix}@example.com",
            "password": "correct-horse-battery-staple",
        },
    )
    assert register.status_code == 201, register.text
    headers = {"Authorization": f"Bearer {register.json()['access_token']}"}
    project = client.post(
        "/api/v1/projects",
        headers=headers,
        json={"name": "Evaluation Project", "slug": f"eval-{suffix}"},
    )
    assert project.status_code == 201, project.text
    project_id = project.json()["id"]
    key = client.post("/api/v1/api-keys", headers=headers, json={"name": "eval-key", "project_id": project_id})
    assert key.status_code == 201, key.text
    return headers, {"X-API-Key": key.json()["api_key"]}, project_id


def test_evaluation_job_scores_ingested_calls() -> None:
    client = TestClient(app)
    auth_headers, api_headers, project_id = _workspace(client)

    ingest = client.post(
        "/api/v1/ingest/llm-calls",
        headers=api_headers,
        json={
            "project_id": project_id,
            "trace_id": f"trace-{uuid.uuid4().hex}",
            "provider": "mock",
            "model": "mock-observatory-model",
            "prompt": "Research request",
            "response": "Unsupported glass city claim.",
            "latency_ms": 450,
            "prompt_tokens": 20,
            "completion_tokens": 10,
        },
    )
    assert ingest.status_code == 201, ingest.text

    job = client.post("/api/v1/evaluations/jobs", headers=auth_headers, json={"project_id": project_id})
    assert job.status_code == 201, job.text
    run = client.post(f"/api/v1/evaluations/jobs/{job.json()['id']}/run", headers=auth_headers)
    assert run.status_code == 200, run.text
    assert run.json()["status"] == "succeeded"

    results = client.get(f"/api/v1/evaluations/results?project_id={project_id}", headers=auth_headers)
    assert results.status_code == 200, results.text
    assert len(results.json()) >= 1
    assert results.json()[0]["hallucination_flag"] is True


def test_alert_rule_creates_incident_and_suppresses_duplicate() -> None:
    client = TestClient(app)
    auth_headers, api_headers, project_id = _workspace(client)

    client.post(
        "/api/v1/ingest/llm-calls",
        headers=api_headers,
        json={
            "project_id": project_id,
            "trace_id": f"trace-{uuid.uuid4().hex}",
            "provider": "mock",
            "model": "mock-observatory-model",
            "prompt": "Research request",
            "response": "Unsupported glass city claim.",
        },
    )
    job = client.post("/api/v1/evaluations/jobs", headers=auth_headers, json={"project_id": project_id})
    client.post(f"/api/v1/evaluations/jobs/{job.json()['id']}/run", headers=auth_headers)

    rule = client.post(
        "/api/v1/alert-rules",
        headers=auth_headers,
        json={
            "project_id": project_id,
            "name": "Any hallucination",
            "metric": "hallucination_rate",
            "threshold": 0.0,
            "severity": "critical",
            "suppression_minutes": 60,
        },
    )
    assert rule.status_code == 201, rule.text

    first = client.post("/api/v1/alert-rules/evaluate", headers=auth_headers)
    assert first.status_code == 200, first.text
    assert first.json()["incidents_created"] == 1

    second = client.post("/api/v1/alert-rules/evaluate", headers=auth_headers)
    assert second.status_code == 200, second.text
    assert second.json()["incidents_created"] == 0

    incidents = client.get("/api/v1/incidents", headers=auth_headers)
    assert incidents.status_code == 200, incidents.text
    assert len(incidents.json()) >= 1


def test_incident_acknowledge_resolve_and_suppression_lifecycle() -> None:
    client = TestClient(app)
    auth_headers, api_headers, project_id = _workspace(client)

    client.post(
        "/api/v1/ingest/llm-calls",
        headers=api_headers,
        json={
            "project_id": project_id,
            "trace_id": f"trace-{uuid.uuid4().hex}",
            "provider": "mock",
            "model": "mock-observatory-model",
            "prompt": "Research request",
            "response": "Unsupported glass city claim.",
        },
    )
    job = client.post("/api/v1/evaluations/jobs", headers=auth_headers, json={"project_id": project_id})
    client.post(f"/api/v1/evaluations/jobs/{job.json()['id']}/run", headers=auth_headers)
    client.post(
        "/api/v1/alert-rules",
        headers=auth_headers,
        json={
            "project_id": project_id,
            "name": "Hallucination lifecycle",
            "metric": "hallucination_rate",
            "threshold": 0.0,
            "severity": "critical",
            "suppression_minutes": 60,
        },
    )

    first = client.post("/api/v1/alert-rules/evaluate", headers=auth_headers)
    assert first.status_code == 200, first.text
    assert first.json()["incidents_created"] == 1
    incident = client.get("/api/v1/incidents", headers=auth_headers).json()[0]

    acknowledged = client.post(f"/api/v1/incidents/{incident['id']}/acknowledge", headers=auth_headers)
    assert acknowledged.status_code == 200, acknowledged.text
    assert acknowledged.json()["status"] == "acknowledged"

    suppressed = client.post("/api/v1/alert-rules/evaluate", headers=auth_headers)
    assert suppressed.status_code == 200, suppressed.text
    assert suppressed.json()["incidents_created"] == 0

    resolved = client.post(f"/api/v1/incidents/{incident['id']}/resolve", headers=auth_headers)
    assert resolved.status_code == 200, resolved.text
    assert resolved.json()["status"] == "resolved"
    assert resolved.json()["resolved_at"] is not None

    recreated = client.post("/api/v1/alert-rules/evaluate", headers=auth_headers)
    assert recreated.status_code == 200, recreated.text
    assert recreated.json()["incidents_created"] == 1
