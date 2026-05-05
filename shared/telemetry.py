import logging
import threading
import time
from typing import Any

from shared.config import get_settings


class PrometheusMetrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.started_at = time.time()
        self.request_count = 0
        self.error_count = 0
        self.request_latency_seconds_sum = 0.0
        self.llm_call_count = 0
        self.llm_call_error_count = 0
        self.llm_latency_ms_sum = 0.0
        self.llm_cost_usd_sum = 0.0

    def observe_request(self, *, latency_seconds: float, status_code: int) -> None:
        with self._lock:
            self.request_count += 1
            self.request_latency_seconds_sum += latency_seconds
            if status_code >= 500:
                self.error_count += 1

    def observe_llm_call(self, *, latency_ms: float, cost_usd: float, status: str) -> None:
        with self._lock:
            self.llm_call_count += 1
            self.llm_latency_ms_sum += latency_ms
            self.llm_cost_usd_sum += cost_usd
            if status != "success":
                self.llm_call_error_count += 1

    def render(self) -> str:
        uptime = max(0.0, time.time() - self.started_at)
        with self._lock:
            lines = [
                "# HELP llm_observatory_uptime_seconds Process uptime in seconds.",
                "# TYPE llm_observatory_uptime_seconds gauge",
                f"llm_observatory_uptime_seconds {uptime:.6f}",
                "# HELP llm_observatory_http_requests_total Total HTTP requests.",
                "# TYPE llm_observatory_http_requests_total counter",
                f"llm_observatory_http_requests_total {self.request_count}",
                "# HELP llm_observatory_http_request_errors_total HTTP requests returning 5xx responses.",
                "# TYPE llm_observatory_http_request_errors_total counter",
                f"llm_observatory_http_request_errors_total {self.error_count}",
                "# HELP llm_observatory_http_request_latency_seconds_sum Total HTTP request latency.",
                "# TYPE llm_observatory_http_request_latency_seconds_sum counter",
                f"llm_observatory_http_request_latency_seconds_sum {self.request_latency_seconds_sum:.6f}",
                "# HELP llm_observatory_llm_calls_total Total LLM calls through the gateway.",
                "# TYPE llm_observatory_llm_calls_total counter",
                f"llm_observatory_llm_calls_total {self.llm_call_count}",
                "# HELP llm_observatory_llm_call_errors_total Failed LLM calls through the gateway.",
                "# TYPE llm_observatory_llm_call_errors_total counter",
                f"llm_observatory_llm_call_errors_total {self.llm_call_error_count}",
                "# HELP llm_observatory_llm_latency_ms_sum Total LLM call latency in milliseconds.",
                "# TYPE llm_observatory_llm_latency_ms_sum counter",
                f"llm_observatory_llm_latency_ms_sum {self.llm_latency_ms_sum:.6f}",
                "# HELP llm_observatory_llm_cost_usd_sum Total estimated LLM cost in USD.",
                "# TYPE llm_observatory_llm_cost_usd_sum counter",
                f"llm_observatory_llm_cost_usd_sum {self.llm_cost_usd_sum:.8f}",
            ]
        return "\n".join(lines) + "\n"


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
    settings = get_settings()
    logger = setup_logger("telemetry")
    properties = properties or {}

    if settings.applicationinsights_connection_string:
        logger.info("cloud_event=%s properties=%s", name, properties)
    else:
        logger.info("local_event=%s properties=%s", name, properties)
