-- ============================================================
-- analytics_queries.sql
-- Business-facing recruiting analytics queries against the star schema
-- ============================================================

-- 1. RECRUITING FUNNEL: how many applications reach each stage
SELECT
    stage,
    COUNT(*) AS n_applications,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct_of_total
FROM fact_applications
GROUP BY stage
ORDER BY n_applications DESC;


-- 2. TIME-TO-HIRE: average days from application to hire, by department
SELECT
    j.department,
    COUNT(*) AS n_hires,
    ROUND(AVG(f.days_to_close), 1) AS avg_days_to_hire,
    MIN(f.days_to_close) AS fastest_hire_days,
    MAX(f.days_to_close) AS slowest_hire_days
FROM fact_applications f
JOIN dim_job j ON f.job_key = j.job_key
WHERE f.is_hired = TRUE
GROUP BY j.department
ORDER BY avg_days_to_hire;


-- 3. SOURCE EFFECTIVENESS: which candidate sources convert best to hire
SELECT
    c.source,
    COUNT(*) AS n_applications,
    SUM(CASE WHEN f.is_hired THEN 1 ELSE 0 END) AS n_hired,
    ROUND(100.0 * SUM(CASE WHEN f.is_hired THEN 1 ELSE 0 END) / COUNT(*), 2) AS hire_rate_pct
FROM fact_applications f
JOIN dim_candidate c ON f.candidate_key = c.candidate_key
GROUP BY c.source
ORDER BY hire_rate_pct DESC;


-- 4. RECRUITER PERFORMANCE: applications handled, hires made, avg time-to-close
SELECT
    r.recruiter_name,
    COUNT(*) AS n_applications_handled,
    SUM(CASE WHEN f.is_hired THEN 1 ELSE 0 END) AS n_hires,
    ROUND(AVG(f.days_to_close), 1) AS avg_days_to_close
FROM fact_applications f
JOIN dim_recruiter r ON f.recruiter_key = r.recruiter_key
GROUP BY r.recruiter_name
ORDER BY n_hires DESC;


-- 5. MONTHLY APPLICATION TREND (uses dim_date for proper time-series rollup)
SELECT
    d.year,
    d.month,
    d.month_name,
    COUNT(*) AS n_applications
FROM fact_applications f
JOIN dim_date d ON f.applied_date_key = d.date_key
GROUP BY d.year, d.month, d.month_name
ORDER BY d.year, d.month;


-- 6. JOB FILL RATE: open headcount vs hires made per job
SELECT
    j.job_id,
    j.title,
    j.department,
    j.headcount,
    COUNT(CASE WHEN f.is_hired THEN 1 END) AS hires_made,
    j.headcount - COUNT(CASE WHEN f.is_hired THEN 1 END) AS headcount_remaining
FROM dim_job j
LEFT JOIN fact_applications f ON j.job_key = f.job_key
GROUP BY j.job_id, j.title, j.department, j.headcount
ORDER BY headcount_remaining DESC;


-- 7. DROP-OFF ANALYSIS: where in the funnel do candidates get rejected most
SELECT
    j.department,
    COUNT(CASE WHEN f.stage = 'Rejected' THEN 1 END) AS n_rejected,
    COUNT(CASE WHEN f.stage = 'Withdrawn' THEN 1 END) AS n_withdrawn,
    COUNT(*) AS n_total,
    ROUND(100.0 * COUNT(CASE WHEN f.stage = 'Rejected' THEN 1 END) / COUNT(*), 1) AS rejection_rate_pct
FROM fact_applications f
JOIN dim_job j ON f.job_key = j.job_key
GROUP BY j.department
ORDER BY rejection_rate_pct DESC;
