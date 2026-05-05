# Metrics and Evaluation

The observatory tracks operational and quality metrics for every LLM call that passes through the gateway.

## Operational Metrics

| Metric | Meaning |
| --- | --- |
| Total calls | Count of LLM requests handled by the gateway |
| Average latency | Mean response time in milliseconds |
| Prompt tokens | Input token count reported or estimated by provider |
| Completion tokens | Output token count reported or estimated by provider |
| Total cost | Estimated USD cost using model-specific token rates |
| Cost by endpoint | Aggregated spend by product feature or API endpoint |

## Evaluation Metrics

| Metric | Meaning |
| --- | --- |
| Faithfulness score | Whether the response appears factually grounded |
| Relevancy score | Whether the response answers the user question |
| Hallucination flag | Boolean indicator for likely fabricated or unsupported content |
| Judge reasoning | Short explanation for the evaluation result |

## Evaluation Modes

- `mock`: deterministic local scoring for demo data and no-key operation.
- `openai`: LLM-as-judge using OpenAI.
- `azure`: LLM-as-judge using Azure OpenAI deployments.

The evaluator stores structured JSON results in DuckDB. If an LLM judge call fails, the evaluator falls back to conservative heuristic scoring so batch jobs do not fail silently.
