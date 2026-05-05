from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from eval_engine.evaluator import evaluate_log, persist_evaluation
from storage.db import fetch_pending_eval_logs, init_db


def run(limit: int = 50) -> int:
    init_db()
    logs = fetch_pending_eval_logs(limit=limit)
    for log in logs:
        result = evaluate_log(log)
        persist_evaluation(log["id"], result)
        print(
            f"evaluated log_id={log['id']} faithfulness={result.faithfulness_score} "
            f"relevancy={result.relevancy_score} hallucination={result.hallucination_flag}"
        )
    return len(logs)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run batch evaluations for unevaluated LLM calls.")
    parser.add_argument("--limit", type=int, default=50)
    args = parser.parse_args()
    count = run(limit=args.limit)
    print(f"Completed {count} evaluations.")
