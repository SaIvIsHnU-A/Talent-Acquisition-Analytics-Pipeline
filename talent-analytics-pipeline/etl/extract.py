"""
extract.py - Extract stage of the ETL pipeline.

Reads raw source files (the "raw / landing zone" - in production this
would be files sitting in HDFS, queried here via Hive external tables;
see /hive/hive_raw_tables.hql for that mapping).
"""

import os
import json
import pandas as pd
from config import RAW_DIR


def extract_jobs() -> pd.DataFrame:
    return pd.read_csv(os.path.join(RAW_DIR, "jobs.csv"))


def extract_candidates() -> pd.DataFrame:
    return pd.read_csv(os.path.join(RAW_DIR, "candidates.csv"))


def extract_applications() -> pd.DataFrame:
    return pd.read_csv(os.path.join(RAW_DIR, "applications.csv"))


def extract_recruiter_activity() -> pd.DataFrame:
    with open(os.path.join(RAW_DIR, "recruiter_activity.json")) as f:
        data = json.load(f)
    return pd.DataFrame(data)


def extract_all() -> dict:
    """Returns a dict of raw dataframes, one per source."""
    return {
        "jobs": extract_jobs(),
        "candidates": extract_candidates(),
        "applications": extract_applications(),
        "recruiter_activity": extract_recruiter_activity(),
    }


if __name__ == "__main__":
    dfs = extract_all()
    for name, df in dfs.items():
        print(f"{name}: {df.shape[0]} rows, {df.shape[1]} cols")
