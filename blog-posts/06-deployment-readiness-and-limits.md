# What LLM Observatory Is Today and What It Would Take to Run It in Production

*LLM Observatory — A practitioner's build log | Post 6 of 6*

---

The last post in this series is the most important one to get right, because this is where a lot of technical writing goes wrong: the author describes what they built without being precise about where the boundary is between what works today and what requires additional engineering to be production-ready.

I will be direct. LLM Observatory is a production-shaped local-first platform. That phrase has specific meaning, and I want to unpack it.

---

## What "production-shaped" means

Production-shaped means the architecture, the API surface, the data model, and the security controls are all designed for production deployment. The patterns are correct. The service boundaries are where they belong. The schema supports what a multi-tenant production platform needs.

What production-shaped does not mean: that the platform is currently running in a multi-tenant production environment handling real user traffic.

The distinction matters because a platform built with production patterns can be extended to real deployment with hardening work. A prototype that was not designed for production requires rebuilding, not hardening.

---

## What is fully operational today

Every item in this list is verified and runnable locally without external dependencies:

**Core platform:**
- FastAPI gateway with mock LLM provider (no API key required)
- Ingestion API accepting external LLM call records
- SQLAlchemy persistence with Alembic migrations on SQLite
- Organization, project, endpoint, and API key management
- JWT authentication and service API key auth with HMAC-SHA256 storage

**Observability:**
- Per-call telemetry: latency, token counts, cost, endpoint, session, status
- Streamlit dashboard (`http://localhost:8510`) rendering latency, cost, token usage, trace logs, quality scores
- Prometheus-compatible metrics endpoint (`GET /metrics`)
- Request correlation headers

**Evaluation and alerting:**
- Batch evaluation worker with heuristic scoring (seven quality signals per call)
- Evaluator version, prompt template, and judge model metadata stored per result
- Alert rules on hallucination rate, latency p95, error rate, and cost spikes
- Incident lifecycle: open → acknowledged → resolved with suppression windows
- Audit log entry on incident resolution

**CI and operations:**
- GitHub Actions CI for automated test validation
- Docker Compose configuration for API, dashboard, PostgreSQL, and workers
- Deterministic demo seed and reset scripts for repeatable demonstrations

---

## The forward Azure deployment path

The architecture is explicitly designed with a production Azure deployment target:

```
Product Services  →  Azure Container Apps: Gateway
Internal Tools    →  Azure Container Apps: Dashboard
                      ↓
                  Azure OpenAI (provider)
                  Azure PostgreSQL (persistence)
                      ↓
Container Apps Jobs: Evaluation Worker
Container Apps Jobs: Alert Worker
                      ↓
                  Azure Key Vault (secrets)
                  Application Insights (telemetry)
                  Slack / Email / Webhook (alert delivery)
```

The environment configuration maps directly to this topology. Switching from local SQLite to Azure PostgreSQL requires changing `DATABASE_URL`. Switching from mock LLM to Azure OpenAI requires setting the Azure provider variables. The code does not change.

What this deployment path does not yet have: Terraform or Bicep infrastructure modules, automated deployment pipelines, and verified end-to-end testing in an actual Azure environment. The guidance is in `docs/deployment.md`. The automation is a roadmap item.

---

## What hardening is required before multi-tenant production use

I am listing these specifically rather than summarizing them, because the specific items are what a production security or architecture review would ask about:

**Queue-backed workers.** The evaluation and alert workers are currently batch scripts. Production scheduling requires a queue backend — Redis with Celery or RQ, Azure Service Bus, or Azure Container Apps Jobs. Without this, worker execution is manual or cron-scheduled rather than event-driven.

**Dashboard API client layer.** The Streamlit dashboard connects directly to the database layer. A production dashboard should connect through an authenticated API client, not with direct database access. This decouples the dashboard from the storage implementation and allows proper access control on dashboard queries.

**Federated identity.** Current auth is JWT with local credential storage. Microsoft Entra ID / OIDC integration is required for enterprise teams with existing identity providers.

**Row-level security.** Tenant isolation is enforced at the application middleware layer. A database-level RLS policy would provide defense in depth against application-layer bypass.

**PII redaction.** The `redacted` storage mode uses a conservative redaction hook that is explicitly documented as needing extension. Production use with sensitive content requires a dedicated PII detector.

**Alert delivery channels.** Current implementation delivers to console only. Slack, email, and webhook delivery require additional implementation.

**Rate limiting.** No per-key rate limiting on ingestion. High-volume or misconfigured ingestion is not bounded.

---

## An honest assessment of where this sits

LLM Observatory demonstrates end-to-end observability for LLM features: centralized access, trace-level telemetry, quality evaluation, alert rules, incident lifecycle, and a dashboard that surfaces operational state. The architecture is correct and the patterns are production-appropriate.

The gap between this and a multi-tenant production deployment is real and specific: worker scheduling, dashboard API layer, federated auth, database RLS, PII redaction, and alert delivery. These are well-understood engineering problems with clear solutions documented in the roadmap. None of them require rethinking the architecture.

For a team evaluating this as a foundation for an internal LLM observability platform: the foundation is solid. The hardening list above is the production engineering backlog.

---

## What I would implement next

The single highest-impact hardening item is queue-backed workers. Everything else on the list can wait; manual batch evaluation can cover the gap. But until workers are queue-backed, the platform cannot respond to quality or cost events in near-real-time — which is the core operational promise.

The concrete next step: integrate Azure Service Bus or Redis with Celery into the evaluation worker, trigger evaluation runs when new call records are ingested, and measure how quickly alert rules fire after a quality threshold is crossed.

---

## One question for you

If you were evaluating an internal LLM observability platform for your engineering team, which item on the hardening list above would be the hard requirement before you could put it in front of a production workload?

---

*This concludes the LLM Observatory build log series.*

---

## Full series index

1. Your LLM Feature Is Degrading Right Now and You Probably Don't Know It
2. How I Structured the LLM Observatory: Gateway, Ingest, and Why the Boundary Matters
3. Three Design Decisions in LLM Observatory and Why I Made Them
4. Evaluation Is Not a Pre-Deploy Step. It Is a Production Signal.
5. Security in an LLM Observability Platform: Controls, Tradeoffs, and What Is Still Open
6. What LLM Observatory Is Today and What It Would Take to Run It in Production *(this post)*

*Add Medium post URLs to each title above after publishing.*
