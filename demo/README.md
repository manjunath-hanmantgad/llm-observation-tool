# Demo Plan: LLM Observatory

Demo flow:

1. Start the dashboard locally.
2. Load or seed the demo workspace.
3. Show overview metrics for calls, error rate, latency, cost, and hallucination rate.
4. Open request logs and trace detail to inspect captured LLM calls.
5. Open evaluation results to show faithfulness, relevancy, groundedness, and hallucination flags.
6. Open incidents and demonstrate acknowledgement/resolution controls.
7. Open API keys and show create/revoke workflows.
8. Run the worker commands to process evaluations and alerts.

Screenshots:

- [Overview](llm-observatory-dashboard.png)
- [Incidents](llm-observatory-incidents.png)
- [API keys](llm-observatory-api-keys.png)

Repeatable local setup:

```bash
python demo/reset_demo.py
python demo/seed_platform_demo.py
streamlit run dashboard/app.py --server.port 8510
```
