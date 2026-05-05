# Operations

LLM Observatory exposes operational endpoints and headers that make the platform ready for production observability integrations.

## Health Checks

| Endpoint | Purpose |
| --- | --- |
| `GET /health` | Basic application health and active provider/storage mode |
| `GET /health/live` | Liveness probe for container orchestration |
| `GET /health/ready` | Readiness probe with database connectivity check |

Use `/health/live` for container liveness and `/health/ready` for rollout readiness.

## Prometheus Metrics

`GET /metrics` returns Prometheus-compatible text exposition format.

Current metrics:

| Metric | Type | Description |
| --- | --- | --- |
| `llm_observatory_uptime_seconds` | gauge | Process uptime |
| `llm_observatory_http_requests_total` | counter | HTTP request count |
| `llm_observatory_http_request_errors_total` | counter | HTTP 5xx response count |
| `llm_observatory_http_request_latency_seconds_sum` | counter | Total HTTP request latency |
| `llm_observatory_llm_calls_total` | counter | Gateway LLM call count |
| `llm_observatory_llm_call_errors_total` | counter | Failed gateway LLM call count |
| `llm_observatory_llm_latency_ms_sum` | counter | Total LLM call latency |
| `llm_observatory_llm_cost_usd_sum` | counter | Total estimated gateway LLM cost |

Example:

```bash
curl http://localhost:8001/metrics
```

## Request Correlation

Every HTTP response includes:

- `X-Request-ID`
- `X-Response-Time-ms`

If a client sends `X-Request-ID`, the gateway preserves it. Otherwise the gateway generates one. This supports log correlation across applications, gateway calls, and incident reviews.

## OpenTelemetry Readiness

The current implementation keeps instrumentation dependency-light for local demos and CI. The request ID, response timing, health checks, and Prometheus endpoint provide the integration surface needed to add OpenTelemetry exporters later.

Production deployment can extend this by adding:

- ASGI OpenTelemetry middleware
- trace propagation using W3C `traceparent`
- Azure Monitor / Application Insights exporter
- span attributes for organization, project, endpoint, provider, model, and status

## Logs

The gateway uses centralized logging through `shared.telemetry.setup_logger`. Cloud telemetry events are emitted through `track_event`; when `APPLICATIONINSIGHTS_CONNECTION_STRING` is configured, this becomes the hook for Azure Application Insights integration.
