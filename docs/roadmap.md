# Roadmap

LLM Observatory is production-shaped today and intentionally local-first for review and demonstration. The roadmap below separates implemented capabilities from planned hardening so public readers can understand the current state clearly.

## Implemented

- FastAPI gateway with mock, OpenAI, and Azure OpenAI provider modes
- organization-scoped auth, JWT access tokens, service API keys, and RBAC
- project and endpoint management APIs
- external LLM call ingestion API
- request, trace, token, cost, latency, and status persistence
- SQLAlchemy models with Alembic migrations
- local SQLite and PostgreSQL-compatible runtime path
- heuristic evaluation jobs with stored evaluator metadata
- alert rules, incident creation, acknowledgement, and resolution
- Streamlit operations console for local demos
- Prometheus-compatible `/metrics`
- request correlation headers
- optional Docker Compose configuration
- GitHub Actions CI
- Azure deployment guidance and safe environment placeholders

## Near-Term Hardening

- verify Docker Compose on a machine with Docker available
- add API-backed dashboard client layer
- add OpenTelemetry ASGI middleware and Azure Monitor exporter
- add queue-backed workers using Redis, Celery/RQ, Azure Service Bus, or Container Apps Jobs
- add incident comments and timeline entries
- add frontend smoke tests

## Enterprise Extensions

- Microsoft Entra ID / OIDC authentication
- organization invite and password reset flows
- configurable evaluator templates and LLM-as-judge comparisons
- configurable retention jobs
- webhook and email alert channels
- provider credential management through Azure Key Vault
- production Terraform or Bicep deployment modules
