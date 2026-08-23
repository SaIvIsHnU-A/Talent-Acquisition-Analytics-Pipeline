# Talent Acquisition Analytics Pipeline

An end-to-end data analytics project simulating a recruiting/talent-acquisition
data platform: raw messy source data → Hive/HDFS raw & curated zones →
Python ETL → PostgreSQL star-schema warehouse → SQL analytics → visual trend reports.

Built as a portfolio project targeting a Data Analytics Intern role at a
talent-experience company — the domain (recruiting funnel, time-to-hire,
source effectiveness) mirrors real product analytics that company runs on.

## Architecture

```
data/raw/ (messy CSV/JSON)
        │
        ▼
[HDFS landing zone]  ──hive_raw_tables.hql──▶  Hive raw_* external tables
        │                                              │
        │                                    hive_transform.hql (heavy
        │                                    aggregation done close to
        │                                    the data, before export)
        │                                              │
        ▼                                              ▼
etl/extract.py → etl/transform.py → etl/load.py   curated_* / agg_* ORC tables
        │
        ▼
PostgreSQL star schema (sql/schema.sql)
   dim_candidate, dim_job, dim_recruiter, dim_date, fact_applications
        │
        ├──▶ sql/analytics_queries.sql   (funnel, time-to-hire, source ROI...)
        └──▶ analysis/trend_analysis.py  (matplotlib/seaborn charts)

Serving layer (operational, not analytical):
   hive/hbase_serving_layer.txt — HBase table for O(1) candidate lookups
   in a recruiter-facing UI (separate from the batch/analytics path above)
```

## Why this design

- **Raw zone stays raw.** Hive external tables read files in place (`STORED AS TEXTFILE`)
  so re-running the pipeline never risks deleting source data — a real production habit,
  not just a script that overwrites things.
- **Heavy aggregation happens close to the data.** `hive_transform.hql` pre-aggregates
  funnel counts and event volumes in Hive before anything moves to Postgres — Postgres
  should hold what BI tools query, not raw event-level volume at scale.
- **Star schema, not one flat table.** `fact_applications` is grain = one row per
  application; dimensions are reusable across every query. This is what actual
  reporting infra looks like at a company processing recruiting data.
- **HBase is deliberately separate from Hive/Postgres.** Hive/Postgres = analytical
  plane (batch, scans, trends). HBase = operational plane (single-key lookups for
  a live UI). Naming *why* you'd use each is more valuable in an interview than
  just knowing the commands.
- **Every cleaning decision is logged, not silent.** `transform.py` prints exactly
  how many duplicate rows, missing dates, or bad values it handled and how — this
  is the difference between "I ran pandas" and "I did data quality engineering."

## How each JD requirement maps to this project

| JD requirement | Where it lives |
|---|---|
| ETL pipelines, extract/transform/load | `etl/extract.py`, `transform.py`, `load.py`, `pipeline.py` |
| Data cleansing, aggregation, normalization | `transform.py` (date parsing, source normalization, dedup) + `hive_transform.hql` |
| Data modeling | `sql/schema.sql` (star schema) |
| Trend analysis and visualization | `analysis/trend_analysis.py` |
| Python scripting for automation | Entire `etl/` package, runnable as one command |
| Big Data concepts (Hadoop/Spark/Hive) | `hive/hive_raw_tables.hql`, `hive_transform.hql` |
| SQL / relational databases | `sql/schema.sql`, `sql/analytics_queries.sql`, Postgres target |
| SQL queries for reports (nice-to-have) | `sql/analytics_queries.sql` (7 business queries) |
| Cloud/Big Data bonus | HBase serving-layer design note, `hive/hbase_serving_layer.txt` |

## How to run it

### 1. Generate raw data + run the Python ETL (SQLite, zero setup)
```bash
cd etl
python3 generate_raw_data.py   # creates messy raw CSV/JSON
python3 pipeline.py            # extract -> transform -> load into SQLite
```

### 2. Run against your real PostgreSQL instead
```bash
pip install psycopg2-binary sqlalchemy
psql -U postgres -c "CREATE DATABASE talent_analytics;"
psql -U postgres -d talent_analytics -f sql/schema.sql

export DB_BACKEND=postgres
export PG_USER=postgres PG_PASSWORD=yourpassword PG_DATABASE=talent_analytics
cd etl && python3 pipeline.py
```

### 3. Run the analytics queries
```bash
psql -U postgres -d talent_analytics -f sql/analytics_queries.sql
```

### 4. Generate charts
```bash
cd analysis
python3 trend_analysis.py   # outputs PNGs to analysis/charts/
```

### 5. (Optional) Hive layer, if you have a Hadoop/Hive environment
```bash
hdfs dfs -mkdir -p /data/raw/talent/{jobs,candidates,applications,recruiter_activity}
hdfs dfs -put data/raw/jobs.csv /data/raw/talent/jobs/
hdfs dfs -put data/raw/candidates.csv /data/raw/talent/candidates/
hdfs dfs -put data/raw/applications.csv /data/raw/talent/applications/
hdfs dfs -put data/raw/recruiter_activity.json /data/raw/talent/recruiter_activity/

hive -f hive/hive_raw_tables.hql
hive -f hive/hive_transform.hql
```

## Sample insights this pipeline surfaces
- Recruiting funnel drop-off by stage (where candidates are lost)
- Time-to-hire by department, with outlier detection via box plots
- Which candidate source (LinkedIn, Referral, Career Site, etc.) actually
  converts to hires best — not just which brings the most volume
- Recruiter workload and hire-close performance
- Monthly application volume trend

## Data quality notes (worth mentioning in an interview)
The raw data deliberately includes: 4 different date formats, missing values,
inconsistent casing (`linkedin` vs `LinkedIn`), leading/trailing whitespace,
exact duplicate rows, and logically invalid rows (closed date before applied
date). Every one of these is caught and handled explicitly in `transform.py`,
with counts logged — nothing is silently dropped.
