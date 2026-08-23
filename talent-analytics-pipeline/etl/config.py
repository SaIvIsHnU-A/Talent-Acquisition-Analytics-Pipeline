"""
config.py - central configuration for the ETL pipeline.

Set DB_BACKEND to "postgres" for production (your real Postgres instance)
or "sqlite" for local testing without any DB server running.
"""

import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE_DIR, "data", "raw")
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")

# --- DB backend switch ---
DB_BACKEND = os.environ.get("DB_BACKEND", "sqlite")  # "sqlite" or "postgres"

SQLITE_PATH = os.path.join(BASE_DIR, "data", "processed", "talent_analytics.db")

POSTGRES_CONFIG = {
    "host": os.environ.get("PG_HOST", "localhost"),
    "port": os.environ.get("PG_PORT", "5432"),
    "database": os.environ.get("PG_DATABASE", "talent_analytics"),
    "user": os.environ.get("PG_USER", "postgres"),
    "password": os.environ.get("PG_PASSWORD", "postgres"),
}


def get_sqlalchemy_url():
    if DB_BACKEND == "postgres":
        c = POSTGRES_CONFIG
        return f"postgresql+psycopg2://{c['user']}:{c['password']}@{c['host']}:{c['port']}/{c['database']}"
    else:
        return f"sqlite:///{SQLITE_PATH}"
