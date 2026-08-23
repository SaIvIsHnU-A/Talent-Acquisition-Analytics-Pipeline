-- ============================================================
-- hive_transform.hql
-- CURATED ZONE: cleans + aggregates raw Hive tables using HiveQL,
-- writing results as ORC (columnar, efficient for downstream BI/export)
-- Run: hive -f hive_transform.hql
-- ============================================================

CREATE DATABASE IF NOT EXISTS talent_curated;
USE talent_curated;

-- ------------------------------------------------------------
-- Curated applications: type-cast + basic normalization done here,
-- deep cleaning (fuzzy dedup, source mapping) stays in the Python
-- transform step for finer control - Hive handles the *heavy lift*
-- of filtering/casting at scale before data leaves the cluster.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS curated_applications
STORED AS ORC
AS
SELECT
    application_id,
    candidate_id,
    job_id,
    recruiter_id,
    -- normalize stage casing at the Hive layer too (defense in depth)
    INITCAP(TRIM(stage)) AS stage,
    applied_date,
    closed_date
FROM talent_raw.raw_applications
WHERE application_id IS NOT NULL
  AND candidate_id IS NOT NULL
  AND job_id IS NOT NULL;

-- ------------------------------------------------------------
-- Pre-aggregated funnel counts per job x stage.
-- This is the kind of rollup you'd compute in Hive BEFORE moving
-- data to Postgres, so Postgres only stores what BI tools query,
-- not the full raw volume (this is the "Big Data -> Data Warehouse"
-- pattern: heavy aggregation happens close to the data in HDFS/Hive).
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS agg_funnel_by_job
STORED AS ORC
AS
SELECT
    job_id,
    stage,
    COUNT(*) AS n_applications
FROM curated_applications
GROUP BY job_id, stage;

-- ------------------------------------------------------------
-- Recruiter activity volume by event type per day - typical
-- high-volume event table that benefits from Hive's partitioning.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS agg_recruiter_activity_daily
STORED AS ORC
AS
SELECT
    recruiter_id,
    TO_DATE(`timestamp`) AS activity_date,
    event_type,
    COUNT(*) AS n_events
FROM talent_raw.raw_recruiter_activity
GROUP BY recruiter_id, TO_DATE(`timestamp`), event_type;

-- Export pattern (run separately, e.g. via Sqoop or a beeline query
-- piped to CSV, then COPY'd into Postgres):
--   beeline -e "SELECT * FROM talent_curated.agg_funnel_by_job" \
--     --outputformat=csv2 > agg_funnel_by_job.csv
