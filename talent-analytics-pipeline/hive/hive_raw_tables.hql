-- ============================================================
-- hive_raw_tables.hql
-- Defines the RAW ZONE in Hive, on top of files sitting in HDFS.
-- Mirrors a real batch architecture:
--    Source systems -> land as CSV/JSON in HDFS -> Hive external tables
--    -> curated + aggregated with HiveQL -> exported to Postgres warehouse
--
-- Run: hive -f hive_raw_tables.hql
-- Assumes raw files have already been copied to HDFS, e.g.:
--   hdfs dfs -mkdir -p /data/raw/talent
--   hdfs dfs -put data/raw/*.csv /data/raw/talent/
--   hdfs dfs -put data/raw/*.json /data/raw/talent/
-- ============================================================

CREATE DATABASE IF NOT EXISTS talent_raw;
USE talent_raw;

-- Raw jobs (external table = Hive does NOT own the data, just reads it,
-- so re-running ETL never risks deleting source files)
CREATE EXTERNAL TABLE IF NOT EXISTS raw_jobs (
    job_id          STRING,
    title           STRING,
    department      STRING,
    location        STRING,
    date_opened     STRING,   -- kept as STRING: raw zone should never assume clean types
    headcount       STRING,
    status          STRING
)
ROW FORMAT DELIMITED
FIELDS TERMINATED BY ','
STORED AS TEXTFILE
LOCATION '/data/raw/talent/jobs/'
TBLPROPERTIES ("skip.header.line.count"="1");

CREATE EXTERNAL TABLE IF NOT EXISTS raw_candidates (
    candidate_id      STRING,
    full_name         STRING,
    email             STRING,
    years_experience  STRING,
    source            STRING,
    location          STRING
)
ROW FORMAT DELIMITED
FIELDS TERMINATED BY ','
STORED AS TEXTFILE
LOCATION '/data/raw/talent/candidates/'
TBLPROPERTIES ("skip.header.line.count"="1");

CREATE EXTERNAL TABLE IF NOT EXISTS raw_applications (
    application_id  STRING,
    candidate_id    STRING,
    job_id          STRING,
    recruiter_id    STRING,
    applied_date    STRING,
    stage           STRING,
    closed_date     STRING
)
ROW FORMAT DELIMITED
FIELDS TERMINATED BY ','
STORED AS TEXTFILE
LOCATION '/data/raw/talent/applications/'
TBLPROPERTIES ("skip.header.line.count"="1");

-- Recruiter activity is semi-structured JSON - use JsonSerDe
-- (org.apache.hive.hcatalog.data.JsonSerDe ships with most Hive distros)
CREATE EXTERNAL TABLE IF NOT EXISTS raw_recruiter_activity (
    recruiter_id    STRING,
    recruiter_name  STRING,
    event_type      STRING,
    `timestamp`     STRING,
    application_id  STRING
)
ROW FORMAT SERDE 'org.apache.hive.hcatalog.data.JsonSerDe'
STORED AS TEXTFILE
LOCATION '/data/raw/talent/recruiter_activity/';
