"""Seed (or reseed) the work order service's SQLite database. Run from the repo root:

    python scripts/seed_work_order_db.py [--reset]
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "work-order-service"))

from sqlmodel import Session  # noqa: E402

from app.db import engine, init_db  # noqa: E402
from app.seed import seed  # noqa: E402

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()

    init_db()
    with Session(engine) as session:
        inserted = seed(session, force=args.reset)
        print(f"inserted {inserted} work orders" if inserted else "database already seeded, use --reset to regenerate")
