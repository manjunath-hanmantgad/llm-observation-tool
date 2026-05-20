# Demo Script — LLM Observatory

**Duration:** 15–20 minutes  
**Audience:** Engineering managers, platform leads, technical decision-makers  
**What you need open:** terminal, `http://localhost:8501`, `http://localhost:8001/docs`

## Pre-demo setup (do this 10 minutes before)
- [ ] Run: `make up`
- [ ] Seed/reset demo data:
  - `python demo/reset_demo.py`
  - `python demo/seed_platform_demo.py`
- [ ] Verify API: `curl http://localhost:8001/health`
- [ ] Verify dashboard: open `http://localhost:8501`

## The problem you're solving (2 minutes)
> Say: "Most teams can’t explain LLM quality, spend, or failures with evidence. Observatory centralizes traces, evaluation quality, latency, and incident signals in one operational surface."

## The solution overview (3 minutes)
> Show `docs/architecture.md` (or the dashboard top-level sections).  
> Say: "A FastAPI gateway logs every call, workers run evaluation and alerting, and the dashboard gives incident-ready visibility by tenant/project/endpoint."

## Live demo walkthrough (10 minutes)

### Step 1 — Load the workspace
Use the dashboard **Load demo workspace** action.

Expected output: Overview KPIs populate (calls, latency, cost, hallucination, incidents).

### Step 2 — Inspect live traces
Open **Request Logs** and filter by endpoint/provider.

Expected output: trace rows with latency, token, and cost metadata.

### Step 3 — Trace drilldown
Open **Trace Detail** and inspect `trace-demo-004`.

Expected output: prompt/response payload, evaluation details, and related incidents.

### Step 4 — Show quality scoring
Open **Evaluations**.

Expected output: faithfulness/relevancy/hallucination metrics and judge reasoning entries.

### Step 5 — Show alerting and incident lifecycle
Open **Alert Rules** then **Incidents**.

Expected output: threshold rule, open incident, and acknowledgement/resolution controls.

### Step 6 — Show API key governance
Open **API Keys**.

Expected output: key metadata, revocation controls, and security narrative.

## Business value close (2 minutes)
> Say: "This gives teams measurable confidence: traceability for every LLM call, measurable quality regression detection, and faster incident response with clear ownership."

## Fallback plan
If gateway or DB is unstable:
- Show `demo/llm-observatory-dashboard.png`.
- Walk through `docs/api.md` and `docs/evaluation.md` artifacts.
- Run `python workers/evaluation_worker.py --limit 5` as a CLI-only proof.

## Common demo gotchas
- Dashboard on wrong port (`8501` in Docker Compose, `8510` in some local walkthrough commands).
- `.env` left in non-mock mode without valid provider credentials.
- Demo data not reseeded after prior runs.
