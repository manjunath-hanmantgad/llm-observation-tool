from __future__ import annotations

import ast
import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from shared.llm_client import get_llm_client
from storage.db import insert_eval_result


JUDGE_PROMPT = """
You are evaluating an LLM response for an observability system.

Question:
{question}

Response:
{response}

Return only JSON with these keys:
- faithfulness_score: number from 0.0 to 1.0
- relevancy_score: number from 0.0 to 1.0
- hallucination_flag: boolean
- judge_reasoning: short explanation
"""


@dataclass
class EvaluationResult:
    faithfulness_score: float
    relevancy_score: float
    hallucination_flag: bool
    judge_reasoning: str
    judge_model: str


def evaluate_log(log: dict) -> EvaluationResult:
    question = extract_question(log.get("prompt", ""))
    response = log.get("response", "")

    try:
        client = get_llm_client()
        if client.settings.llm_provider == "mock":
            return heuristic_evaluate(question, response, "mock-judge")

        result = client.chat(
            [{"role": "user", "content": JUDGE_PROMPT.format(question=question, response=response)}],
            purpose="eval",
        )
        parsed = json.loads(result.content)
        return EvaluationResult(
            faithfulness_score=clamp(parsed.get("faithfulness_score", 0.0)),
            relevancy_score=clamp(parsed.get("relevancy_score", 0.0)),
            hallucination_flag=bool(parsed.get("hallucination_flag", False)),
            judge_reasoning=str(parsed.get("judge_reasoning", ""))[:1000],
            judge_model=result.model,
        )
    except Exception as exc:
        fallback = heuristic_evaluate(question, response, "heuristic-fallback")
        fallback.judge_reasoning = f"{fallback.judge_reasoning} Fallback used after judge error: {exc}"
        return fallback


def persist_evaluation(log_id: str, result: EvaluationResult) -> None:
    insert_eval_result(
        {
            "id": str(uuid.uuid4()),
            "log_id": log_id,
            "timestamp": datetime.now(UTC),
            "faithfulness_score": result.faithfulness_score,
            "relevancy_score": result.relevancy_score,
            "hallucination_flag": result.hallucination_flag,
            "judge_reasoning": result.judge_reasoning,
            "judge_model": result.judge_model,
        }
    )


def extract_question(prompt: str) -> str:
    try:
        messages = ast.literal_eval(prompt)
        user_messages = [m.get("content", "") for m in messages if m.get("role") == "user"]
        return user_messages[-1] if user_messages else prompt
    except Exception:
        return prompt


def heuristic_evaluate(question: str, response: str, judge_model: str) -> EvaluationResult:
    lowered = response.lower()
    suspicious_terms = ["glass city", "unsupported", "fabricated", "made up", "hallucinated"]
    hallucination = any(term in lowered for term in suspicious_terms)
    empty = not response.strip()

    faithfulness = 0.2 if hallucination else 0.85
    relevancy = 0.1 if empty else 0.75
    if question and any(token in lowered for token in question.lower().split()[:4]):
        relevancy = max(relevancy, 0.82)

    return EvaluationResult(
        faithfulness_score=faithfulness,
        relevancy_score=relevancy,
        hallucination_flag=hallucination,
        judge_reasoning=(
            "Heuristic evaluation flagged unsupported content."
            if hallucination
            else "Heuristic evaluation found no obvious unsupported claims."
        ),
        judge_model=judge_model,
    )


def clamp(value: float) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.0
