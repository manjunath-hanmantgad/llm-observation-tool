# Your LLM Feature Is Degrading Right Now and You Probably Don't Know It

*LLM Observatory  A practitioner's build log | Post 1 of 6*



There is a failure mode in LLM-powered products that conventional monitoring does not catch.

Your service is up. Response times are within acceptable range. Error rates are nominal. But one of your product features  a support assistant, a research workflow, a sales summarization endpoint  has started producing responses that are less grounded than they were three weeks ago. A prompt was adjusted, a retrieval pipeline was modified, a model was swapped from one version to another. None of those changes triggered a deployment alert. Your uptime dashboard is green.

This is the silent degradation problem. I built LLM Observatory specifically to address it



## Why uptime is not enough

When I mapped out what could go wrong in an LLM-powered feature, I listed the failure modes that a standard health check would miss entirely:

- A prompt change that subtly shifts tone or reduces factual grounding
- A model version update that changes response length distribution and breaks downstream parsing
- A retrieval issue that reduces context quality without increasing error rates
- A token cost increase caused by a new request pattern routing to the wrong endpoint
- Hallucination frequency drifting upward across a specific endpoint over two weeks

None of these produce 500 errors. None of them trip latency thresholds in the first hour. The application health endpoint (`GET /health/ready`) returns 200 throughout. But quality is degrading, and the signal is sitting in the content of the responses  not in the infrastructure telemetry.

The implication is straightforward: LLM observability requires a different data model than service observability. You need trace-level quality data, not just request-level status data.



## What the conventional stack misses

A standard observability stack  metrics, logs, uptime checks  captures operational state. It tells you the service is responding. It does not tell you:

- Whether the response was faithful to the source material
- Whether the response answered the user's actual question
- Whether hallucination frequency is increasing on a specific endpoint
- Which endpoint is responsible for 60% of your token spend this week
- Whether a prompt change two days ago shifted quality in either direction

These questions require a different instrumentation layer. They require capturing and evaluating the content of completions, not just the status of requests.



## The three degradation patterns I kept seeing

As I worked through the design, three concrete failure patterns kept recurring in how teams describe LLM production issues:

**Silent quality drift.** A model update or prompt adjustment gradually changes response quality. No alert fires. The first signal is a support ticket or user complaint  days or weeks after the shift happened. At that point, the team has no telemetry to identify which change caused it.

**Cost spike from endpoint routing.** A specific feature endpoint starts receiving a new request pattern. Token counts per call increase. Costs climb. The team has aggregate billing data from the provider but no per-endpoint breakdown that would let them trace the increase to the responsible feature.

**Evaluation blind spots.** The team runs offline evaluations before deployment but has no mechanism to continue evaluation on live traffic. Production behavior diverges from the pre-deploy test set without any systematic detection.

All three patterns share the same root cause: the team is operating LLM features without a telemetry layer that captures quality, cost, and evaluation data at the call level.



## What I built to address this

LLM Observatory is a local-first observability platform that treats LLM calls as the unit of telemetry  not requests in the abstract, but the specific combination of endpoint, model, prompt, completion, latency, tokens, cost, and quality scores.

The platform captures:

- **Operational telemetry** per call: latency, token counts, cost, endpoint, session, provider, model, status
- **Quality signals**: faithfulness score, relevancy score, hallucination risk flag, toxicity flag, groundedness score
- **Incident lifecycle**: alert rules on hallucination rate, error rate, latency p95, and cost spikes  with acknowledgement and resolution tracking

The dashboard (`http://localhost:8510`) renders these signals across endpoints and time, making drift visible rather than invisible.

The proof artifact is direct: the incidents panel shows open, acknowledged, and resolved incidents with timestamps, affected endpoints, and the metric that triggered each alert.

![LLM Observatory dashboard  latency, cost, and quality scores across endpoints](llm-observatory-dashboard.png)

![LLM Observatory incidents panel  open, acknowledged, and resolved incidents with trigger metrics](llm-observatory-incidents.png)



## What this changes operationally

The shift this enables is moving from reactive to proactive quality management.

Without this layer, the team learns about a quality regression when users report it. With it, an alert rule fires when hallucination rate on a specific endpoint crosses a configured threshold  before the support queue fills up.

That is not a minor workflow improvement. It is the difference between discovering a problem in 15 minutes and discovering it in four days.



## Current limits

I want to be precise about what this is and is not:

- This is a local-first implementation. It is not running in multi-tenant production today.
- The evaluation engine uses deterministic heuristic scoring (`platform-heuristic-v1`). LLM-as-judge evaluation is a later phase requiring a live provider key.
- Alert notification channels are currently console-only. Slack, email, and webhook delivery are on the roadmap.
- Hallucination scoring flags risk  it does not guarantee detection or elimination.



## Next engineering step

Instrument one production LLM endpoint by routing calls through `POST /chat` and observe whether the per-endpoint cost breakdown reveals anything that aggregate billing does not.



## One question for you

If a prompt change degraded quality on your highest-traffic LLM endpoint today, how many hours would it take your team to detect it? What telemetry would you use?



*Next post in this series: The architecture that separates gateway mode from ingest mode, and why that boundary matters for teams that already have LLM integrations in place.*
