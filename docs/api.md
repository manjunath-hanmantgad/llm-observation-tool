# API Reference

The backend exposes local mock gateway APIs and enterprise management APIs.

## Health

- `GET /health`
- `GET /health/live`
- `GET /health/ready`

`/health/ready` validates application database connectivity.

## Authentication

### Register Organization Owner

`POST /api/v1/auth/register`

```json
{
  "organization_name": "Acme AI",
  "organization_slug": "acme-ai",
  "email": "owner@example.com",
  "password": "correct-horse-battery-staple"
}
```

### Login

`POST /api/v1/auth/login`

Authenticated API requests use:

```http
Authorization: Bearer <access_token>
```

## Projects And Endpoints

- `POST /api/v1/projects`
- `GET /api/v1/projects`
- `POST /api/v1/endpoints`

## API Keys

- `POST /api/v1/api-keys`
- `GET /api/v1/api-keys`
- `DELETE /api/v1/api-keys/{api_key_id}`

Raw API keys are returned only once at creation. Only the hash is persisted.

## Ingestion

`POST /api/v1/ingest/llm-calls`

```http
X-API-Key: <service_api_key>
```

## Metrics

`GET /api/v1/metrics/summary`

Optional query:

- `project_id`

## Logs And Traces

`GET /api/v1/llm-calls`

Query parameters:

- `project_id`
- `endpoint_id`
- `provider`
- `model`
- `status`
- `search`
- `limit`
- `offset`

`GET /api/v1/traces/{trace_id}`

Returns the call, prompt, response, metadata, evaluation results, and related incidents for the trace.

## Evaluations

- `POST /api/v1/evaluations/jobs`
- `POST /api/v1/evaluations/jobs/{job_id}/run`
- `GET /api/v1/evaluations/jobs`
- `GET /api/v1/evaluations/results`

Evaluation jobs are tenant scoped. The current worker supports heuristic scoring and stores evaluator version, model, reasoning, and quality flags.

## Alerts And Incidents

- `POST /api/v1/alert-rules`
- `GET /api/v1/alert-rules`
- `POST /api/v1/alert-rules/evaluate`
- `GET /api/v1/incidents`
- `POST /api/v1/incidents/{incident_id}/acknowledge`
- `POST /api/v1/incidents/{incident_id}/resolve`

Supported metrics:

- `hallucination_rate`
- `latency_p95_ms`
- `error_rate`
- `cost_spike`

Alert evaluation creates incidents and respects each rule's suppression window. Acknowledged incidents continue to suppress duplicate incidents until they are resolved or the suppression window expires. Resolved incidents retain their `resolved_at` timestamp for operational review.
