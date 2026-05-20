from __future__ import annotations

import logging
import threading
import time as _time
from typing import Any

from prometheus_client import Counter, Gauge, Histogram, REGISTRY, generate_latest

from shared.config import get_settings


def _configure_azure_monitor() -> bool:
    settings = get_settings()
    if not settings.applicationinsights_connection_string:
        return False
    try:
        from azure.monitor.opentelemetry import configure_azure_monitor

        configure_azure_monitor(
            connection_string=settings.applicationinsights_connection_string,
            logger_name="llm-observatory",
        )
        return True
    except Exception as exc:
        logging.getLogger("telemetry").warning("Azure Monitor setup failed: %s", exc)
        return False


_azure_configured = False
_azure_lock = threading.Lock()


def _ensure_azure_configured() -> bool:
    global _azure_configured
    if _azure_configured:
        return True
    with _azure_lock:
        if not _azure_configured:
            _azure_configured = _configure_azure_monitor()
    return _azure_configured


_NS = "llm_observatory"

http_requests_total = Counter(f"{_NS}_http_requests_total", "Total HTTP requests", ["status_code"])
http_request_latency = Histogram(
    f"{_NS}_http_request_latency_seconds",
    "HTTP request latency",
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)
llm_calls_total = Counter(f"{_NS}_llm_calls_total", "Total LLM calls", ["status"])
llm_latency = Histogram(
    f"{_NS}_llm_latency_ms",
    "LLM call latency ms",
    buckets=[100, 250, 500, 1000, 2000, 5000, 10000],
)
llm_cost_usd = Counter(f"{_NS}_llm_cost_usd_total", "Total LLM cost in USD")
process_start_time = Gauge(f"{_NS}_process_start_time_seconds", "Process start time")
process_start_time.set(_time.time())


class PrometheusMetrics:
    """Thin wrapper keeping the existing call interface in gateway.py unchanged."""

    def observe_request(self, *, latency_seconds: float, status_code: int) -> None:
        http_requests_total.labels(status_code=str(status_code)).inc()
        http_request_latency.observe(latency_seconds)

    def observe_llm_call(self, *, latency_ms: float, cost_usd: float, status: str) -> None:
        llm_calls_total.labels(status=status).inc()
        llm_latency.observe(latency_ms)
        llm_cost_usd.inc(cost_usd)

    def render(self) -> str:
        return generate_latest(REGISTRY).decode("utf-8")


metrics = PrometheusMetrics()


def setup_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger


def track_event(name: str, properties: dict[str, Any] | None = None) -> None:
    logger = setup_logger("llm-observatory.telemetry")
    properties = properties or {}

    if _ensure_azure_configured():
        logger.info(
            "event=%s properties=%s",
            name,
            properties,
            extra={"custom_dimensions": {**properties, "event_name": name}},
        )
    else:
        logger.info("local_event=%s properties=%s", name, properties)
