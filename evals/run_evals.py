#!/usr/bin/env python3
"""Eval runner for LLM Observatory."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from alerts import slack_alerts
from eval_engine.evaluator import heuristic_evaluate
from gateway.cost import calculate_cost


def run_cost(case: dict) -> tuple[bool, str]:
    payload = case["input"]
    actual = calculate_cost(payload["model"], payload["prompt_tokens"], payload["completion_tokens"])
    expected = float(case["expected"]["cost_usd"])
    tolerance_pct = float(case.get("tolerance_pct", 1.0))
    tolerance = abs(expected) * (tolerance_pct / 100.0)
    passed = abs(actual - expected) <= tolerance
    return passed, f"actual={actual:.8f} expected={expected:.8f} tolerance={tolerance:.8f}"


def run_alert(case: dict) -> tuple[bool, str]:
    payload = case["input"]
    expected = case["expected"]

    original_summary = slack_alerts.summary
    original_get_settings = slack_alerts.get_settings

    try:
        slack_alerts.summary = lambda: payload["metrics"]
        slack_alerts.get_settings = lambda: SimpleNamespace(
            hallucination_rate_threshold=payload["thresholds"]["hallucination_rate_threshold"],
            avg_latency_ms_threshold=payload["thresholds"]["avg_latency_ms_threshold"],
        )
        alerts = slack_alerts.build_alerts()
    finally:
        slack_alerts.summary = original_summary
        slack_alerts.get_settings = original_get_settings

    contains = expected.get("contains", [])
    expected_count = int(expected.get("count", len(contains)))
    all_present = all(any(fragment in alert for alert in alerts) for fragment in contains)
    passed = all_present and len(alerts) == expected_count
    return passed, f"alerts={alerts}"


def run_eval_scoring(case: dict) -> tuple[bool, str]:
    payload = case["input"]
    expected = case["expected"]
    result = heuristic_evaluate(payload["question"], payload["response"], payload.get("judge_model", "mock-judge"))

    checks = [
        result.hallucination_flag == bool(expected["hallucination_flag"]),
        abs(result.faithfulness_score - float(expected["faithfulness_score"])) <= 1e-9,
        result.relevancy_score >= float(expected.get("relevancy_min", 0.0)),
    ]
    if "relevancy_max" in expected:
        checks.append(result.relevancy_score <= float(expected["relevancy_max"]))

    passed = all(checks)
    detail = (
        f"faithfulness={result.faithfulness_score} relevancy={result.relevancy_score} "
        f"hallucination={result.hallucination_flag}"
    )
    return passed, detail


def main() -> int:
    dataset_path = Path(__file__).with_name("golden_dataset.json")
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))

    runners = {
        "cost_calculation": run_cost,
        "alert_trigger": run_alert,
        "eval_scoring": run_eval_scoring,
    }

    executed = 0
    passed = 0
    skipped = 0
    failed_cases: list[tuple[str, str]] = []

    for case in dataset["cases"]:
        case_id = case["id"]
        if case.get("requires_live_llm", False):
            skipped += 1
            print(f"[SKIP] {case_id} requires live LLM")
            continue

        runner = runners.get(case["category"])
        if runner is None:
            failed_cases.append((case_id, f"unsupported category: {case['category']}"))
            print(f"[FAIL] {case_id} unsupported category")
            executed += 1
            continue

        ok, detail = runner(case)
        executed += 1
        if ok:
            passed += 1
            print(f"[PASS] {case_id} {detail}")
        else:
            failed_cases.append((case_id, detail))
            print(f"[FAIL] {case_id} {detail}")

    print("\nSummary")
    print(f"Executed: {executed}")
    print(f"Passed:   {passed}")
    print(f"Skipped:  {skipped}")
    print(f"Failed:   {len(failed_cases)}")

    if failed_cases:
        print("\nFailed cases:")
        for case_id, detail in failed_cases:
            print(f"- {case_id}: {detail}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
