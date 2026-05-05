from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from observatory.database import SessionLocal, init_platform_db
from observatory.evaluation_service import run_queued_jobs


def main(limit: int) -> int:
    init_platform_db()
    with SessionLocal() as session:
        processed = run_queued_jobs(session, limit=limit)
    print(f"Processed {processed} evaluation job(s).")
    return processed


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run queued platform evaluation jobs.")
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()
    main(args.limit)
