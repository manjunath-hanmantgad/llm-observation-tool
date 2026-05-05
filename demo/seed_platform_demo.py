from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from observatory.database import SessionLocal, init_platform_db
from observatory.demo_data import seed_demo_workspace


if __name__ == "__main__":
    init_platform_db()
    with SessionLocal() as session:
        result = seed_demo_workspace(session)
    print("Demo workspace ready.")
    print(f"email={result['email']}")
    print(f"password={result['password']}")
    if result["api_key"]:
        print(f"api_key={result['api_key']}")
