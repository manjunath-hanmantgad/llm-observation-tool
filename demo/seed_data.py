from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.append(str(Path(__file__).resolve().parents[1]))

from eval_engine.run_evals import run
from gateway.gateway import app
from storage.db import init_db


DEMO_REQUESTS = [
    {
        "messages": [{"role": "user", "content": "What is 2+2? Answer in one word."}],
        "endpoint": "support-assistant",
        "session_id": "demo-001",
    },
    {
        "messages": [{"role": "user", "content": "Summarize the refund request from this customer."}],
        "endpoint": "support-assistant",
        "session_id": "demo-002",
    },
    {
        "messages": [{"role": "user", "content": "Please hallucinate a fake historical discovery on the moon."}],
        "endpoint": "research-assistant",
        "session_id": "demo-003",
    },
    {
        "messages": [{"role": "user", "content": "Draft a concise response for an account upgrade question."}],
        "endpoint": "sales-copilot",
        "session_id": "demo-004",
    },
]


def seed() -> None:
    init_db()
    client = TestClient(app)
    for payload in DEMO_REQUESTS:
        response = client.post("/chat", json=payload)
        response.raise_for_status()
        print(f"seeded call id={response.json()['id']} endpoint={payload['endpoint']}")
    run(limit=20)


if __name__ == "__main__":
    seed()
