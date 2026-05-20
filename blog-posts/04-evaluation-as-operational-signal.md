# Evaluation Is Not a Pre-Deploy Step. It Is a Production Signal.

*LLM Observatory — A practitioner's build log | Post 4 of 6*

---

Most LLM evaluation workflows I have seen are structured as a pre-deploy gate: run an eval suite before pushing, check pass rate, merge if acceptable. That model treats evaluation as a quality check at the boundary between development and production.

It misses the harder problem: production behavior changes after deployment, independent of anything the team does. Model providers update weights. Retrieval systems shift. User query distributions evolve. Prompt performance that was valid on the eval set at deploy time degrades on real traffic over the following weeks.

LLM Observatory implements evaluation as a continuous background process on live ingested data — not a one-time check that clears deployment.

---

## What the evaluation pipeline does

The evaluation pipeline runs as a worker process against persisted call data:

```
POST /api/v1/ingest/llm-calls  →  platform database
                                        ↓
POST /api/v1/evaluations/jobs  →  evaluation job queue
                                        ↓
workers/evaluation_worker.py   →  score storage + evaluator metadata
                                        ↓
GET /api/v1/evaluations/results →  results API
```

Each evaluation job processes a batch of calls that have not yet been scored. The worker stores the results alongside the evaluator version (`platform-heuristic-v1`), the prompt template used, and the judge model if applicable. This metadata is not an afterthought — it is what makes evaluator comparison possible later.

---

## What gets scored

The current evaluator (`platform-heuristic-v1`) produces seven signals per call:

| Signal | What it measures |
|---|---|
| Faithfulness | Whether the response is grounded in the provided context |
| Relevancy | Whether the response addresses the user's question |
| Hallucination risk | Whether the response contains ungrounded factual claims |
| Toxicity | Whether the response contains harmful content |
| PII exposure | Whether the response leaks personally identifiable information |
| Refusal quality | Whether appropriate refusals are well-formed |
| Groundedness | Whether claims in the response can be traced to source material |

These seven signals cover the three failure categories that matter most in production LLM systems: factual reliability (faithfulness, hallucination risk, groundedness), relevance (relevancy), and safety (toxicity, PII exposure, refusal quality).

A single evaluation run that shows hallucination risk trending upward on a support assistant endpoint — even by a small margin — is a signal worth investigating before it compounds.

---

## How evaluation connects to alerting

Evaluation scores feed directly into the alert rule system. Alert rules can be configured on:

- `hallucination_rate` — percentage of calls flagged with elevated hallucination risk
- `latency_p95_ms` — 95th percentile latency for an endpoint
- `error_rate` — rate of failed calls
- `cost_spike` — significant increase in per-endpoint token cost

When a rule threshold is crossed, the alert worker creates an incident with status `open`. An engineer acknowledges it (`POST /api/v1/incidents/{incident_id}/acknowledge`), which records operator ownership without closing the event. When the underlying issue is resolved, the incident is closed (`POST /api/v1/incidents/{incident_id}/resolve`) with a `resolved_at` timestamp.

The suppression mechanism matters here: if an open or acknowledged incident already exists for a rule within the configured `suppression_minutes` window, no duplicate incident is created. Resolved incidents no longer suppress, which means a recurring issue can be detected again after an operator closes the previous event.

![LLM Observatory incidents panel — suppression window prevents duplicate firing; resolved incidents re-enable detection](llm-observatory-incidents.png)

This is the difference between evaluation as a static report and evaluation as an operational loop.

---

## The evaluator version field is load-bearing

Every evaluation result stores the evaluator version that produced it. This design choice is easy to overlook and hard to recover from if omitted.

Without version tracking, comparing evaluation results across time or across evaluator configurations is unreliable. A score of 0.72 faithfulness from a heuristic evaluator and a score of 0.72 from an LLM-as-judge run are not comparable — but the field values look identical if version is not recorded.

With version tracking, it becomes possible to run both evaluators against the same call set and compare distributions. This is the foundation for the planned LLM-as-judge phase: the schema already supports it without migration changes.

---

## What the dashboard shows

The Streamlit dashboard (`http://localhost:8510`) renders evaluation results alongside operational metrics — latency, cost, token usage — in the same view.

![LLM Observatory dashboard — evaluation scores rendered alongside latency and cost in a single view](llm-observatory-dashboard.png)

This colocation is deliberate. Treating quality signals as a separate reporting layer — disconnected from the operational telemetry — makes it harder to correlate a quality regression with an operational event. Rendering them in the same view makes it natural to ask: "Hallucination rate climbed on Thursday — did latency or cost also change that day?"

---

## Current limits

- The current evaluator is heuristic. It detects patterns but does not reason about content the way an LLM judge would. Precision is limited, particularly for subtle factual errors.
- Evaluation runs in batch via worker scripts. A queue-backed async pipeline (Redis/Celery, Azure Service Bus, or Azure Container Apps Jobs) is a near-term hardening item.
- LLM-as-judge evaluation requires a live provider API key and adds per-evaluation cost. It is designed as a later phase with explicit operator control over which calls get judge evaluation.
- There is currently no regression report format — no automated summary comparing evaluation distributions across time windows or deployments. That is a planned roadmap capability.

---

## Next engineering step

Ingest 50 LLM calls across two endpoints and run `python workers/evaluation_worker.py --limit 50`. Compare the faithfulness and hallucination risk score distributions between the two endpoints. If they diverge, that divergence is a starting point for a prompt or retrieval investigation.

---

## One question for you

Do you run LLM evaluations on live production traffic today, or only on pre-deploy test sets? If production evaluation is not in place, what is blocking it?

---

*Next post: Security decisions — how tenant isolation, key management, and prompt storage modes work in the current implementation.*
