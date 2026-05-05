from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from observatory.alerting_service import evaluate_alert_rules
from observatory.database import SessionLocal, init_platform_db


def main(organization_id: str | None) -> int:
    init_platform_db()
    with SessionLocal() as session:
        created = evaluate_alert_rules(session, organization_id=organization_id)
    print(f"Created {created} incident(s).")
    return created


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate alert rules and create incidents.")
    parser.add_argument("--organization-id", default=None)
    args = parser.parse_args()
    main(args.organization_id)
