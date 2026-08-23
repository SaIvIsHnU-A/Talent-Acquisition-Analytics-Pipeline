"""
load.py - Load stage of the ETL pipeline.

Loads cleaned dataframes into the star schema defined in /sql/schema.sql.

Two backends supported (set DB_BACKEND env var, see config.py):
  - "sqlite"   -> zero-setup, used for local testing (this file's __main__ uses it)
  - "postgres" -> production target. Requires: pip install psycopg2-binary sqlalchemy
                  and PG_HOST/PG_DATABASE/PG_USER/PG_PASSWORD env vars set,
                  and schema.sql already applied (psql -f sql/schema.sql).
"""

import sqlite3
import pandas as pd
from config import DB_BACKEND, SQLITE_PATH, get_sqlalchemy_url


def get_connection():
    if DB_BACKEND == "postgres":
        from sqlalchemy import create_engine
        engine = create_engine(get_sqlalchemy_url())
        return engine
    else:
        return sqlite3.connect(SQLITE_PATH)


def load_sqlite_schema(conn):
    """SQLite doesn't understand SERIAL/BOOLEAN the same way Postgres does,
    so for local testing we create a lightweight equivalent schema.
    (Production always uses sql/schema.sql against real Postgres.)"""
    conn.executescript("""
    DROP TABLE IF EXISTS fact_applications;
    DROP TABLE IF EXISTS dim_candidate;
    DROP TABLE IF EXISTS dim_job;
    DROP TABLE IF EXISTS dim_recruiter;
    DROP TABLE IF EXISTS dim_date;

    CREATE TABLE dim_candidate (
        candidate_key INTEGER PRIMARY KEY AUTOINCREMENT,
        candidate_id TEXT UNIQUE, full_name TEXT, email TEXT,
        years_experience REAL, source TEXT, location TEXT
    );
    CREATE TABLE dim_job (
        job_key INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id TEXT UNIQUE, title TEXT, department TEXT, location TEXT,
        date_opened TEXT, headcount INTEGER, status TEXT
    );
    CREATE TABLE dim_recruiter (
        recruiter_key INTEGER PRIMARY KEY AUTOINCREMENT,
        recruiter_id TEXT UNIQUE, recruiter_name TEXT
    );
    CREATE TABLE dim_date (
        date_key INTEGER PRIMARY KEY, full_date TEXT, year INTEGER,
        quarter INTEGER, month INTEGER, month_name TEXT, week INTEGER, day_of_week TEXT
    );
    CREATE TABLE fact_applications (
        application_key INTEGER PRIMARY KEY AUTOINCREMENT,
        application_id TEXT UNIQUE, candidate_key INTEGER, job_key INTEGER,
        recruiter_key INTEGER, applied_date_key INTEGER, closed_date_key INTEGER,
        stage TEXT, is_hired INTEGER, days_to_close INTEGER
    );
    """)
    conn.commit()


def load_all(clean: dict, recruiters_lookup: list):
    """
    clean: dict of cleaned dataframes from transform.transform_all()
    recruiters_lookup: list of (recruiter_id, recruiter_name) tuples
    """
    conn = get_connection()
    is_sqlite = DB_BACKEND != "postgres"

    if is_sqlite:
        load_sqlite_schema(conn)

    # --- dim_date ---
    dim_date = clean["dim_date"].copy()
    dim_date["full_date"] = dim_date["full_date"].astype(str)
    dim_date.to_sql("dim_date", conn, if_exists="append", index=False)

    # --- dim_candidate ---
    candidates = clean["candidates"][
        ["candidate_id", "full_name", "email", "years_experience", "source", "location"]
    ]
    candidates.to_sql("dim_candidate", conn, if_exists="append", index=False)

    # --- dim_job ---
    jobs = clean["jobs"].copy()
    jobs["date_opened"] = jobs["date_opened"].astype(str)
    jobs = jobs[["job_id", "title", "department", "location", "date_opened", "headcount", "status"]]
    jobs.to_sql("dim_job", conn, if_exists="append", index=False)

    # --- dim_recruiter ---
    dim_recruiter = pd.DataFrame(recruiters_lookup, columns=["recruiter_id", "recruiter_name"])
    dim_recruiter.to_sql("dim_recruiter", conn, if_exists="append", index=False)

    # --- fact_applications: resolve surrogate keys ---
    apps = clean["applications"].copy()

    cand_map = pd.read_sql("SELECT candidate_key, candidate_id FROM dim_candidate", conn)
    job_map = pd.read_sql("SELECT job_key, job_id FROM dim_job", conn)
    rec_map = pd.read_sql("SELECT recruiter_key, recruiter_id FROM dim_recruiter", conn)

    apps = apps.merge(cand_map, on="candidate_id", how="left")
    apps = apps.merge(job_map, on="job_id", how="left")
    apps = apps.merge(rec_map, on="recruiter_id", how="left")

    apps["applied_date_key"] = apps["applied_date"].dt.strftime("%Y%m%d").astype("Int64")
    apps["closed_date_key"] = apps["closed_date"].dt.strftime("%Y%m%d")
    apps["closed_date_key"] = pd.to_numeric(apps["closed_date_key"], errors="coerce").astype("Int64")

    fact = apps[[
        "application_id", "candidate_key", "job_key", "recruiter_key",
        "applied_date_key", "closed_date_key", "stage", "is_hired", "days_to_close"
    ]].copy()
    fact["is_hired"] = fact["is_hired"].astype(int)

    fact.to_sql("fact_applications", conn, if_exists="append", index=False)

    if is_sqlite:
        conn.commit()

    print(f"Loaded: {len(dim_date)} dates, {len(candidates)} candidates, "
          f"{len(jobs)} jobs, {len(dim_recruiter)} recruiters, {len(fact)} fact rows")
    return conn


if __name__ == "__main__":
    from extract import extract_all
    from transform import transform_all

    RECRUITERS = [("R001","Anita Rao"), ("R002","Suresh Menon"), ("R003","Kavita Joshi"),
                  ("R004","Deepak Nair"), ("R005","Farah Khan")]

    raw = extract_all()
    clean = transform_all(raw)
    conn = load_all(clean, RECRUITERS)

    # quick sanity query
    check = pd.read_sql("""
        SELECT stage, COUNT(*) as n
        FROM fact_applications
        GROUP BY stage
        ORDER BY n DESC
    """, conn)
    print("\nStage distribution after load:")
    print(check.to_string(index=False))
