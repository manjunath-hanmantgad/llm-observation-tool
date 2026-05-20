# Three Design Decisions in LLM Observatory and Why I Made Them

*LLM Observatory — A practitioner's build log | Post 3 of 6*

---

Every non-trivial system has a few decisions that feel like they could go either way until you work through the constraints. This post documents three of those in LLM Observatory: the authentication model, the evaluation sequencing, and the storage default. Each one had a reason, and each one came with an accepted cost.

---

## Decision 1: JWT plus service API keys — not a single auth model

The platform has two types of callers with fundamentally different requirements.

**Human operators** — engineers and analysts — need browser-accessible authentication that supports role-based access and session expiry. They log in through a credentials flow and receive a JWT access token. Their role (owner, admin, engineer, analyst) determines what they can read and modify.

**Service integrations** — the applications that ingest LLM call records — need machine-to-machine authentication that works in automated pipelines without human login flows. They need a credential that can be scoped to a specific project and revoked independently without affecting other integrations.

A single auth model cannot satisfy both requirements cleanly. JWTs for service-to-service traffic create operational problems: token expiry in long-running pipelines, no per-integration revocation scope, and credential management that requires a human login to rotate. API keys for human operators create different problems: no role model, no session concept, no audit of who is authenticated.

The design uses JWTs for human operator sessions (registered through `POST /api/v1/auth/register`, authenticated through `POST /api/v1/auth/login`) and service API keys for ingestion integrations (created through `POST /api/v1/api-keys`, used with `X-API-Key` on ingestion requests).

The accepted cost is complexity — two credential types means two auth paths to test, two sets of middleware to maintain, and two mental models for operators to understand. The benefit is that each credential type is actually fit for its purpose.

---

## Decision 2: Heuristic evaluation before LLM-as-judge

The production case for LLM-as-judge evaluation is compelling: use a capable model to score faithfulness, relevancy, and hallucination risk with nuanced reasoning that heuristics cannot replicate. The engineering case for starting with heuristic evaluation is also compelling: it runs without a provider API key, produces deterministic outputs, and does not add per-evaluation cost to a platform that is itself tracking cost.

I built heuristic evaluation first (`platform-heuristic-v1`) for three concrete reasons:

**Demonstrability without dependency.** A platform that requires an OpenAI API key to demonstrate its own evaluation feature creates a circular dependency for anyone evaluating the platform. The mock provider mode (`LLM_PROVIDER=mock`) needs to work end-to-end — ingestion, evaluation, alerting, dashboard — without any external service. Heuristic evaluation makes that possible.

**Evaluation version tracking as a first-class concern.** The evaluation data model stores evaluator version, prompt template, and judge model alongside every score. This schema was designed to support future evaluator comparisons — not just running LLM-as-judge, but comparing `platform-heuristic-v1` against a subsequent LLM-as-judge run on the same calls. Getting the schema right before adding the complexity of LLM-as-judge was the safer sequence.

**Cost control as a platform principle.** The observatory tracks LLM cost as a first-class metric. Running LLM-as-judge evaluation on every ingested call would add a significant per-call cost that the platform itself would then need to track and explain. Batch evaluation (`python workers/evaluation_worker.py --limit 10`) gives operators explicit control over evaluation volume and cost.

The accepted cost is evaluation precision. Heuristic scoring can identify clear failures and obvious patterns, but it misses subtleties that an LLM judge would catch. The roadmap adds LLM-as-judge templates as a later phase, with fallback to heuristic scoring if the judge call fails.

---

## Decision 3: SQLite-first, PostgreSQL-forward

The storage default is SQLite with a local file path (`DATABASE_URL=sqlite:///storage/observatory.db`). PostgreSQL is the forward deployment target.

This is not a compromise. It is a deliberate sequencing choice.

**Local development velocity.** A platform that requires a running PostgreSQL instance to start has a higher setup cost for anyone reviewing the codebase, running demos, or extending the platform. SQLite removes that cost entirely. The quick start is three shell commands and no Docker dependency.

**Schema correctness validated before deployment complexity.** SQLAlchemy with Alembic migrations (`alembic upgrade head`) runs against both SQLite and PostgreSQL without code changes. Writing and validating migrations against SQLite first means the schema is correct before the PostgreSQL deployment path is introduced.

**Clear deployment path without committed secrets.** The Azure deployment path — Azure PostgreSQL, Azure OpenAI, Azure Container Apps, Azure Key Vault — is documented in `docs/deployment.md` and represented in the architecture diagrams. But none of those credentials are committed. The environment placeholder files (`.env.example`) contain safe values only. Operators replace them when they deploy to a real environment.

The accepted cost is a local–production gap: SQLite behaves differently from PostgreSQL under concurrent writes, and some query patterns that perform well on SQLite will need optimization for PostgreSQL at scale. That gap is documented rather than papered over.

---

## One decision I deliberately did not make yet

The current alert notification implementation delivers to console only. The schema supports Slack, email, and webhook channels — the configuration model is in place — but the delivery implementations are roadmap items.

I made this choice because the operational value of alert rules and incident lifecycle (open → acknowledged → resolved, with suppression windows) is testable and demonstrable without delivery integrations. Adding a Slack webhook that requires an external service to test would have complicated every demo and CI run. The delivery path comes after the detection and lifecycle logic is solid.

---

## Current limits

- Entra ID / OIDC integration for enterprise SSO is a roadmap item. Current auth is JWT and API key only.
- Heuristic evaluation precision is limited. LLM-as-judge templates are a later phase.
- Alert delivery is console-only. Slack, email, and webhook channels require additional implementation work.
- The SQLite–PostgreSQL migration path is documented but not automated. Operators manage the environment switch manually.

---

## Next engineering step

Run the evaluation worker against a set of ingested calls with `--limit 50` and compare the faithfulness and hallucination risk distribution across two different endpoints. The per-evaluator version field makes it straightforward to filter results by which evaluator produced them.

---

## One question for you

When you design auth for an internal platform that serves both human operators and automated pipelines, do you use a single credential model or two? What drove the choice?

---

*Next post: How evaluation works as an operational signal — not just a one-time pre-deploy check, but a continuous quality measurement layer on live traffic.*
