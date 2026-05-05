# Evaluation Pipeline

The platform now supports evaluation jobs against persisted LLM calls in the application database.

## Flow

1. External service ingests an LLM call through `POST /api/v1/ingest/llm-calls`.
2. An engineer queues an evaluation job with `POST /api/v1/evaluations/jobs`.
3. The job can run immediately through `POST /api/v1/evaluations/jobs/{job_id}/run`.
4. The worker entrypoint can process queued jobs:

```bash
python workers/evaluation_worker.py --limit 10
```

5. Results are available from `GET /api/v1/evaluations/results`.

## Current Evaluator

Current evaluator:

- type: heuristic
- version: `platform-heuristic-v1`
- stores evaluator version, prompt template, judge model, scores, flags, and reasoning

Scores and flags:

- faithfulness
- relevancy
- hallucination risk
- toxicity flag
- PII exposure flag
- refusal quality
- groundedness

## Roadmap

Later phases can add LLM-as-judge templates, per-project evaluator configuration, async queue backends, evaluator version comparisons, and regression reports.
