from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from observatory.database import SessionLocal, init_platform_db
from observatory.demo_data import reset_demo_workspace


if __name__ == "__main__":
    init_platform_db()
    with SessionLocal() as session:
        deleted = reset_demo_workspace(session)
    print(f"Deleted {deleted} demo record(s).")
