from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx

sys.path.append(str(Path(__file__).resolve().parents[1]))

from shared.config import get_settings
from storage.db import init_db, summary


def build_alerts() -> list[str]:
    settings = get_settings()
    metrics = summary()
    alerts: list[str] = []

    if metrics["evaluated_calls"] and metrics["hallucination_rate"] > settings.hallucination_rate_threshold:
        alerts.append(
            f"Hallucination rate {metrics['hallucination_rate']:.1%} exceeds "
            f"threshold {settings.hallucination_rate_threshold:.1%}."
        )

    if metrics["avg_latency_ms"] > settings.avg_latency_ms_threshold:
        alerts.append(
            f"Average latency {metrics['avg_latency_ms']}ms exceeds "
            f"threshold {settings.avg_latency_ms_threshold}ms."
        )

    if metrics["failed_calls"]:
        alerts.append(f"{metrics['failed_calls']} LLM calls have failed.")

    return alerts


def send_alerts() -> list[str]:
    init_db()
    settings = get_settings()
    alerts = build_alerts()
    if not alerts:
        print("No alert thresholds exceeded.")
        return []

    payload = {"text": "LLM Observatory Alert\n" + "\n".join(f"- {alert}" for alert in alerts)}
    if not settings.slack_webhook_url:
        print("SLACK_WEBHOOK_URL is not configured. Alert payload:")
        print(json.dumps(payload, indent=2))
        return alerts

    response = httpx.post(settings.slack_webhook_url, json=payload, timeout=10)
    response.raise_for_status()
    print(f"Sent {len(alerts)} alert(s) to Slack.")
    return alerts


if __name__ == "__main__":
    send_alerts()
