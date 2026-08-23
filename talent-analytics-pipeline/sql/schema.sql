-- ============================================================
-- schema.sql
-- Star schema for Talent Acquisition Analytics Warehouse
-- Target: PostgreSQL
-- ============================================================

DROP TABLE IF EXISTS fact_applications CASCADE;
DROP TABLE IF EXISTS dim_candidate CASCADE;
DROP TABLE IF EXISTS dim_job CASCADE;
DROP TABLE IF EXISTS dim_recruiter CASCADE;
DROP TABLE IF EXISTS dim_date CASCADE;

-- ---------------------------------------------------------
-- DIM: Candidate
-- ---------------------------------------------------------
CREATE TABLE dim_candidate (
    candidate_key       SERIAL PRIMARY KEY,
    candidate_id        VARCHAR(20) UNIQUE NOT NULL,
    full_name           VARCHAR(150) NOT NULL,
    email               VARCHAR(150),
    years_experience    NUMERIC(4,1),
    source              VARCHAR(50),         -- normalized: LinkedIn, Referral, Naukri, ...
    location             VARCHAR(50)
);

-- ---------------------------------------------------------
-- DIM: Job requisition
-- ---------------------------------------------------------
CREATE TABLE dim_job (
    job_key             SERIAL PRIMARY KEY,
    job_id              VARCHAR(20) UNIQUE NOT NULL,
    title               VARCHAR(150),
    department          VARCHAR(50),
    location             VARCHAR(50),
    date_opened         DATE,
    headcount           INT,
    status              VARCHAR(20)
);

-- ---------------------------------------------------------
-- DIM: Recruiter
-- ---------------------------------------------------------
CREATE TABLE dim_recruiter (
    recruiter_key       SERIAL PRIMARY KEY,
    recruiter_id        VARCHAR(20) UNIQUE NOT NULL,
    recruiter_name       VARCHAR(150)
);

-- ---------------------------------------------------------
-- DIM: Date (standard date dimension for trend analysis)
-- ---------------------------------------------------------
CREATE TABLE dim_date (
    date_key            INT PRIMARY KEY,      -- YYYYMMDD
    full_date            DATE UNIQUE NOT NULL,
    year                 INT,
    quarter              INT,
    month                INT,
    month_name           VARCHAR(15),
    week                 INT,
    day_of_week          VARCHAR(15)
);

-- ---------------------------------------------------------
-- FACT: Applications (one row per candidate-job application)
-- Grain: one application_id
-- ---------------------------------------------------------
CREATE TABLE fact_applications (
    application_key      SERIAL PRIMARY KEY,
    application_id        VARCHAR(20) UNIQUE NOT NULL,
    candidate_key         INT REFERENCES dim_candidate(candidate_key),
    job_key                INT REFERENCES dim_job(job_key),
    recruiter_key          INT REFERENCES dim_recruiter(recruiter_key),
    applied_date_key       INT REFERENCES dim_date(date_key),
    closed_date_key        INT REFERENCES dim_date(date_key),
    stage                  VARCHAR(20) NOT NULL,   -- Applied/Screening/Interview/Offer/Hired/Rejected/Withdrawn
    is_hired                BOOLEAN DEFAULT FALSE,
    days_to_close           INT                     -- derived: closed_date - applied_date
);

CREATE INDEX idx_fact_app_stage ON fact_applications(stage);
CREATE INDEX idx_fact_app_job ON fact_applications(job_key);
CREATE INDEX idx_fact_app_recruiter ON fact_applications(recruiter_key);
CREATE INDEX idx_fact_app_applied_date ON fact_applications(applied_date_key);

COMMENT ON TABLE fact_applications IS 'Fact table: one row per candidate application; grain = application_id';
COMMENT ON TABLE dim_candidate IS 'Cleaned/deduplicated candidate dimension loaded from raw candidates.csv';
