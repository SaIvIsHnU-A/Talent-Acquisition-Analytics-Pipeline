"""
pipeline.py - Orchestrates the full ETL run: extract -> transform -> load.

Usage:
    python3 pipeline.py                 # uses DB_BACKEND from config (default sqlite)
    DB_BACKEND=postgres python3 pipeline.py   # loads into your real Postgres instance
                                                # (run `psql -f ../sql/schema.sql` first)
"""

import time
from extract import extract_all
from transform import transform_all
from load import load_all
from config import DB_BACKEND

RECRUITERS = [("R001", "Anita Rao"), ("R002", "Suresh Menon"), ("R003", "Kavita Joshi"),
              ("R004", "Deepak Nair"), ("R005", "Farah Khan")]


def run():
    t0 = time.time()
    print(f"=== Talent Analytics ETL Pipeline (backend: {DB_BACKEND}) ===\n")

    print("[1/3] EXTRACT")
    raw = extract_all()
    for name, df in raw.items():
        print(f"   {name}: {len(df)} raw rows")

    print("\n[2/3] TRANSFORM")
    clean = transform_all(raw)

    print("\n[3/3] LOAD")
    load_all(clean, RECRUITERS)

    print(f"\nPipeline completed in {time.time() - t0:.2f}s")


if __name__ == "__main__":
    run()
