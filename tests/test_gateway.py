from fastapi.testclient import TestClient

from gateway.gateway import app


def test_health() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.headers["X-Request-ID"]
    assert response.headers["X-Response-Time-ms"]


def test_chat_logs_mock_response() -> None:
    client = TestClient(app)
    response = client.post(
        "/chat",
        json={
            "messages": [{"role": "user", "content": "What is 2+2?"}],
            "endpoint": "test-suite",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["provider"] == "mock"
    assert data["tokens"]["prompt"] > 0
    assert data["response"]


def test_prometheus_metrics_endpoint() -> None:
    client = TestClient(app)
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    body = response.text
    assert "llm_observatory_http_requests_total" in body
    assert "llm_observatory_llm_calls_total" in body
