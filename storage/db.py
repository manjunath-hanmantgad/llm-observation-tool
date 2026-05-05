from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import duckdb


DEFAULT_DB_PATH = Path("storage/metrics.db")


def db_path() -> Path:
    return Path(os.getenv("LLM_OBSERVATORY_DB_PATH", str(DEFAULT_DB_PATH)))


def get_connection(read_only: bool = False) -> duckdb.DuckDBPyConnection:
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(path), read_only=read_only)


def init_db() -> None:
    db_path().parent.mkdir(parents=True, exist_ok=True)
    con = get_connection()

    con.execute(
        """
        CREATE TABLE IF NOT EXISTS llm_logs (
            id VARCHAR PRIMARY KEY,
            timestamp TIMESTAMP,
            prompt TEXT,
            response TEXT,
            model VARCHAR,
            provider VARCHAR,
            latency_ms DOUBLE,
            prompt_tokens INTEGER,
            completion_tokens INTEGER,
            total_cost_usd DOUBLE,
            endpoint VARCHAR,
            session_id VARCHAR,
            status VARCHAR,
            error TEXT
        )
        """
    )

    con.execute(
        """
        CREATE TABLE IF NOT EXISTS eval_results (
            id VARCHAR PRIMARY KEY,
            log_id VARCHAR,
            timestamp TIMESTAMP,
            faithfulness_score DOUBLE,
            relevancy_score DOUBLE,
            hallucination_flag BOOLEAN,
            judge_reasoning TEXT,
            judge_model VARCHAR
        )
        """
    )
    con.close()


def insert_llm_log(record: dict[str, Any]) -> None:
    con = get_connection()
    con.execute(
        """
        INSERT INTO llm_logs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            record["id"],
            record["timestamp"],
            record["prompt"],
            record["response"],
            record["model"],
            record["provider"],
            record["latency_ms"],
            record["prompt_tokens"],
            record["completion_tokens"],
            record["total_cost_usd"],
            record["endpoint"],
            record["session_id"],
            record["status"],
            record["error"],
        ],
    )
    con.close()


def insert_eval_result(record: dict[str, Any]) -> None:
    con = get_connection()
    con.execute(
        """
        INSERT INTO eval_results VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            record["id"],
            record["log_id"],
            record["timestamp"],
            record["faithfulness_score"],
            record["relevancy_score"],
            record["hallucination_flag"],
            record["judge_reasoning"],
            record["judge_model"],
        ],
    )
    con.close()


def fetch_pending_eval_logs(limit: int = 50) -> list[dict[str, Any]]:
    con = get_connection(read_only=True)
    rows = con.execute(
        """
        SELECT l.id, l.timestamp, l.prompt, l.response, l.model, l.endpoint
        FROM llm_logs l
        LEFT JOIN eval_results e ON l.id = e.log_id
        WHERE e.log_id IS NULL AND l.status = 'success'
        ORDER BY l.timestamp DESC
        LIMIT ?
        """,
        [limit],
    ).fetchdf()
    con.close()
    return rows.to_dict("records")


def summary() -> dict[str, Any]:
    con = get_connection(read_only=True)
    row = con.execute(
        """
        SELECT
            COUNT(*) AS total_calls,
            COALESCE(ROUND(SUM(total_cost_usd), 6), 0) AS total_cost_usd,
            COALESCE(ROUND(AVG(latency_ms), 1), 0) AS avg_latency_ms,
            SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) AS failed_calls
        FROM llm_logs
        """
    ).fetchone()
    eval_row = con.execute(
        """
        SELECT
            COUNT(*) AS evaluated_calls,
            COALESCE(ROUND(AVG(faithfulness_score), 3), 0) AS avg_faithfulness,
            COALESCE(ROUND(AVG(relevancy_score), 3), 0) AS avg_relevancy,
            COALESCE(ROUND(AVG(CASE WHEN hallucination_flag THEN 1.0 ELSE 0.0 END), 3), 0) AS hallucination_rate
        FROM eval_results
        """
    ).fetchone()
    con.close()

    return {
        "total_calls": row[0],
        "total_cost_usd": row[1],
        "avg_latency_ms": row[2],
        "failed_calls": row[3] or 0,
        "evaluated_calls": eval_row[0],
        "avg_faithfulness": eval_row[1],
        "avg_relevancy": eval_row[2],
        "hallucination_rate": eval_row[3],
    }


if __name__ == "__main__":
    init_db()
    print(f"Database initialized at {db_path()}")
