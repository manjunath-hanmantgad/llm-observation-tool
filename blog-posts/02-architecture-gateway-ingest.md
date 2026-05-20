# How I Structured the LLM Observatory: Gateway, Ingest, and Why the Boundary Matters

*LLM Observatory A practitioner's build log | Post 2 of 6*



The first architectural decision in LLM Observatory was not about storage schema or evaluation models. It was about where the platform fits relative to existing LLM integrations.

Teams building new products can route LLM traffic through a centralized gateway from day one. But most teams working on LLM observability already have integrations in place client code calling OpenAI or Azure OpenAI directly, embedded in service logic that was shipped months ago. A platform that requires re-routing all that traffic to observe it is not adoptable without a migration project.

That constraint shaped the first design choice: two distinct ingestion paths.



## Two modes, one platform

LLM Observatory supports two ways for applications to contribute telemetry:

**Gateway mode.** The application sends LLM calls to the Observatory gateway (`POST /chat`). The gateway proxies the call to the configured provider (mock, OpenAI, or Azure OpenAI), captures the trace, and returns the completion to the caller. The application never calls the LLM provider directly.

**Ingest mode.** The application calls the LLM provider directly and, after receiving the response, submits the completed trace to the Observatory ingestion endpoint (`POST /api/v1/ingest/llm-calls`) using a service API key. The platform captures the telemetry without being in the call path.

The boundary between these two modes determines the platform's blast radius. In gateway mode, the Observatory is in the critical path. In ingest mode, it is not a platform outage does not degrade the application's LLM calls.



## Service boundary diagram

```
Product Applications ──proxy mode──▶ FastAPI Gateway ──▶ Provider Layer
                                                              (Mock / OpenAI / Azure)
                     ──ingest mode─▶ Ingestion API

Both paths ──▶ Platform Database ──▶ Evaluation Worker
                                 ──▶ Alert Worker ──▶ Incidents
                                 ──▶ Dashboard
```

The gateway and ingestion API both write to the same persistence layer. Downstream workers evaluation and alerting read from that shared store regardless of which ingestion path was used. The dashboard renders the same telemetry model whether it came from gateway mode or ingest mode.

This means teams can start with ingest mode (no traffic rerouting required) and migrate individual endpoints to gateway mode later when they want the platform to handle provider-level failover or routing logic.



## What each component does

**FastAPI gateway (`gateway/gateway.py`).** Receives authenticated LLM requests, selects the provider based on environment configuration, forwards the call, and persists the trace. Returns the completion to the caller. Exposes health endpoints at `GET /health`, `GET /health/live`, and `GET /health/ready`, where `/health/ready` validates database connectivity.

**Ingestion API (`POST /api/v1/ingest/llm-calls`).** Accepts completed call records from external services. Requires a service API key scoped to a specific project. Validates organization scope at the key level a key scoped to project A cannot ingest into project B.

**Evaluation worker (`workers/evaluation_worker.py`).** Reads persisted calls that have not been evaluated. Runs evaluation jobs using the configured evaluator. Stores faithfulness, relevancy, hallucination risk, toxicity, PII exposure, refusal quality, and groundedness scores alongside the evaluator version and prompt template used.

**Alert worker (`workers/alert_worker.py`).** Evaluates configured alert rules against current metric state. Creates incidents when thresholds are crossed. Respects suppression windows to prevent alert storms if an open or acknowledged incident already exists for a rule within the suppression window, no duplicate incident is created.

**Dashboard (`dashboard/app.py`).** Streamlit application that renders latency, cost, token usage, quality scores, trace logs, and incident state. Connects to the local database for demos and to PostgreSQL in the forward deployment path.

**Prometheus endpoint (`GET /metrics`).** Exposes operational metrics in Prometheus format for teams that already have a scraping infrastructure in place.



## Why workers are separate processes

I deliberately separated the evaluation and alert workers from the API process rather than running evaluations inline with requests.

Inline evaluation would add latency to every LLM call that flows through the gateway even calls where the result is not needed immediately. For gateway mode, where the Observatory is already in the critical path, adding an LLM-as-judge evaluation call inline would roughly double per-call latency.

Separating workers as independent processes means evaluation can run on a schedule, in batch, or triggered by queue depth without affecting the request path. The current implementation uses worker scripts. The forward deployment path maps these to Azure Container Apps Jobs or queue-backed workers (Redis/Celery, Azure Service Bus) for production scheduling.



## Provider abstraction

The provider layer is configured through a single environment variable:

```
LLM_PROVIDER=mock    # deterministic, no API key required
LLM_PROVIDER=openai  # requires OPENAI_API_KEY
LLM_PROVIDER=azure   # requires Azure OpenAI endpoint and key
```

Switching providers does not change the API surface or the data schema. The gateway selects the provider implementation at startup. This makes the platform demonstrable without any API key (mock mode) and deployable against either OpenAI or Azure OpenAI without code changes.

The evaluation worker follows the same pattern: in mock mode it uses deterministic heuristic scoring; in openai or azure mode it attempts LLM-as-judge evaluation and falls back to heuristic scoring if the judge call fails.



## Current limits

- The current worker implementation uses batch scripts. Production scheduling requires a queue backend this is documented as a near-term hardening item.
- Docker Compose configuration is included for reviewers who want container parity with PostgreSQL. The verified local path uses Python, SQLite, and the worker scripts directly.
- The dashboard connects directly to the database layer rather than through an API client. A dashboard API client layer is a documented roadmap item.
- Azure deployment guidance is included but Azure credentials are not required for local operation.



## Next engineering step

Separate one high-volume endpoint into its own project in the Observatory and observe whether per-project cost and quality metrics reveal a pattern that per-organization aggregates were masking.



## One question for you

When you instrument a new LLM feature, do you route traffic through a centralized gateway from day one, or do you wire in observability after the fact? What drove that choice?



*Next post: Three specific design decisions why JWT plus service API keys over a single auth model, why heuristic evaluation before LLM-as-judge, and why SQLite-first before PostgreSQL.*
