# Runbook — LLM Observatory

## Service overview
LLM Observatory captures gateway LLM traffic and tracks cost, latency, evaluation quality, and incidents. If this service is down, request ingestion, evaluation runs, alert generation, and dashboard observability all stop.

## Health checks
| Endpoint | Expected | What it means |
|---|---|---|
| `GET /health` | `200` with `{"status":"ok",...}` | Gateway is running and config loaded |
| `GET /health/live` | `200` with `{"status":"alive"}` | Process liveness is healthy |
| `GET /health/ready` | `200` with `{"status":"ready","database":"ok"}` | Database connection through SQLAlchemy works |
| `GET /metrics` | `200` Prometheus payload | Metrics scraping path is healthy |

## Common failure scenarios

### PostgreSQL connection failure
**Symptom:** `GET /health/ready` fails or returns 500.
**Action:**
1. `docker compose ps postgres`
2. `docker compose logs postgres`
3. `docker compose restart postgres`
4. Re-run `curl http://localhost:8001/health/ready`

### LLM calls failing on `/chat`
**Symptom:** `POST /chat` returns `502` and gateway logs show `LLM call failed`.
**Action:**
1. Check provider mode: `grep '^LLM_PROVIDER' .env`
2. For demo continuity, switch to `LLM_PROVIDER=mock`.
3. If using OpenAI/Azure, verify corresponding credentials in `.env`.
4. Retry with a minimal `/chat` payload and confirm response.

### Evaluations or alerts not updating
**Symptom:** Dashboard shows stale evaluation/incident data.
**Action:**
1. Run evaluation worker: `python workers/evaluation_worker.py --limit 20`
2. Run alert worker: `python workers/alert_worker.py`
3. Check worker logs in Compose: `docker compose logs evaluation-worker alert-worker`

### High latency alerts
**Symptom:** Alert payload contains `Average latency ... exceeds threshold`.
**Action:**
1. Check recent traces in dashboard **Request Logs** and **Trace Detail**.
2. Inspect gateway logs: `docker compose logs gateway`
3. Verify database responsiveness: `curl http://localhost:8001/health/ready`

## Rollback procedure
```bash
az containerapp revision list \
  --name <GATEWAY_CONTAINER_APP> \
  --resource-group <RESOURCE_GROUP>

az containerapp revision activate \
  --name <GATEWAY_CONTAINER_APP> \
  --resource-group <RESOURCE_GROUP> \
  --revision <PREVIOUS_REVISION_NAME>
```

## Log access
```bash
# Local gateway logs
docker compose logs -f gateway

# Azure Container Apps live logs
az containerapp logs show \
  --name <GATEWAY_CONTAINER_APP> \
  --resource-group <RESOURCE_GROUP> \
  --follow
```

## Contacts / escalation
- Primary owner: [fill in]
- Secondary owner: [fill in]
- Escalation SLA: [fill in]
