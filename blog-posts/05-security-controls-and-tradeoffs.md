# Security in an LLM Observability Platform: Controls, Tradeoffs, and What Is Still Open

*LLM Observatory — A practitioner's build log | Post 5 of 6*

---

An observability platform for LLM calls occupies an unusual security position. It is not just infrastructure — it is infrastructure that stores the prompts and completions your applications send to language models. Depending on what those applications handle, that data can include customer queries, internal documents, financial requests, or clinical text.

The security controls in LLM Observatory are not a separate concern from the telemetry design. They are built into the data model, the auth layer, and the storage configuration. This post documents what is implemented, what the specific tradeoffs are, and what is explicitly not yet done.

---

## Tenant isolation at the data boundary

The platform uses organization-scoped data isolation. Every API call that modifies or reads data derives the organization scope from the credential used:

- JWT-authenticated requests derive scope from the token's organization claim. An engineer authenticated to organization A cannot access organization B's traces, evaluations, or incidents.
- Service API keys derive scope from the key's organization and project assignment. A key scoped to project A cannot ingest into project B — the ingestion endpoint rejects requests that would violate project scope at the key level.

This means the isolation boundary is enforced at the application layer on every authenticated request. It is not a row-level security policy in the database, which is an important distinction — the control is in the API middleware, not the storage engine. A direct database access would bypass it.

For the local SQLite deployment, this is acceptable. For a multi-tenant production deployment on PostgreSQL, row-level security policies at the database layer would be an additional hardening step.

---

## Credential storage

**Passwords** are stored as salted PBKDF2-HMAC-SHA256 hashes. No plaintext passwords are persisted.

**Service API keys** use HMAC-SHA256 with an environment-provided pepper (`API_KEY_PEPPER`). The raw key is returned once at creation (`POST /api/v1/api-keys`) and never again. Only the hash is stored. This matches the operational model of GitHub personal access tokens and similar credential systems — the key cannot be recovered from storage if the database is compromised.

**JWT secrets** are environment-provided (`JWT_SECRET_KEY`). The `.env` file is excluded from source control. The `.env.example` file contains safe placeholder values only.

![LLM Observatory API key management — keys are hashed at creation; raw value is never stored or retrievable](llm-observatory-api-keys.png)

The API key revocation flow (`DELETE /api/v1/api-keys/{api_key_id}`) removes the stored hash. A revoked key cannot be re-authenticated even if an operator knows the original raw value.

---

## Prompt and response storage modes

Storing LLM call telemetry means storing what users sent and what the model returned. This is where observability and data governance intersect.

The ingestion API supports three storage modes, selected per call at ingestion time:

- **`full`** — stores the complete prompt and response text.
- **`redacted`** — applies a redaction hook before storage. The current redaction implementation is explicitly conservative and is documented as needing extension with a dedicated PII detector.
- **`metadata-only`** — stores operational fields (latency, tokens, cost, endpoint, status) without prompt or response content.

The metadata-only mode is the right default for applications that handle sensitive content and do not need the observatory to store what was said — only the operational characteristics of the call. Hallucination risk and quality scores can still be evaluated using content that is passed at evaluation time but not stored at ingestion time.

This is a design tradeoff: metadata-only mode gives stronger data minimization guarantees but reduces the observatory's ability to surface the specific response that triggered an alert.

---

## Security headers and CORS

The API sets three security headers on all responses:

- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: strict-origin-when-cross-origin`

CORS origins are explicitly configured rather than using a wildcard default:

```env
CORS_ALLOWED_ORIGINS=http://localhost:8501,http://localhost:8510
```

Production deployments should enumerate the specific origins that need API access. A wildcard CORS configuration on an API that stores LLM call telemetry is not acceptable.

---

## What is not yet implemented

I want to be specific about the open items, because observability platforms are often evaluated for enterprise use and the gaps matter:

**No SSO or federated identity.** The current authentication is JWT with local credential storage. Microsoft Entra ID and OIDC provider integration are roadmap items. Enterprise teams with existing identity providers cannot federate with the current implementation.

**No row-level security in the database.** Tenant isolation is enforced at the application middleware layer. A database-level RLS policy would provide defense in depth.

**PII redaction is conservative.** The redaction hook in `redacted` storage mode is documented as requiring extension. It should not be treated as a production-grade PII detector without additional work.

**No audit log for administrative actions.** Incident resolution writes an audit log entry with `resolved_at`. Broader administrative actions — creating projects, rotating API keys, changing RBAC roles — do not yet have a full audit trail.

**No rate limiting on ingestion.** High-volume ingestion from a misconfigured or compromised service API key could fill the database. Request-level rate limiting is a near-term hardening item.

---

## The security posture in one sentence

The platform is appropriate for internal engineering use, local development, and demonstration — with a clear and documented hardening path toward multi-tenant production deployment.

That sentence is more useful than a vague "enterprise-ready" claim. It tells an engineering team exactly what the current controls cover and what work remains before a production security review.

---

## Next engineering step

Review which endpoints in your LLM feature set handle the most sensitive content and configure those to use `metadata-only` storage mode. Reserve `full` mode for endpoints where prompt-level debugging is worth the storage tradeoff.

---

## One question for you

For LLM-powered features that handle sensitive content — support queries, financial requests, internal documents — have you defined a prompt storage policy, or is everything stored by default?

---

*Final post in this series: Deployment readiness, the local-to-Azure path, and an honest accounting of what this platform is today versus what it would need to become for production multi-tenant use.*
