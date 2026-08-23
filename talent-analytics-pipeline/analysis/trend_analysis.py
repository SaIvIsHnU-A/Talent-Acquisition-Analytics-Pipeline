"""
trend_analysis.py - Generates recruiting analytics visualizations from
the star schema warehouse. Run after etl/pipeline.py has loaded data.
"""

import os
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

sns.set_theme(style="whitegrid")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "processed", "talent_analytics.db")
OUT_DIR = os.path.join(BASE_DIR, "analysis", "charts")
os.makedirs(OUT_DIR, exist_ok=True)

conn = sqlite3.connect(DB_PATH)

STAGE_ORDER = ["Applied", "Screening", "Interview", "Offer", "Hired"]

# ------------------------------------------------------------
# 1. Recruiting funnel
# ------------------------------------------------------------
funnel = pd.read_sql("""
    SELECT stage, COUNT(*) as n
    FROM fact_applications
    WHERE stage IN ('Applied','Screening','Interview','Offer','Hired')
    GROUP BY stage
""", conn)
funnel["stage"] = pd.Categorical(funnel["stage"], categories=STAGE_ORDER, ordered=True)
funnel = funnel.sort_values("stage")

fig, ax = plt.subplots(figsize=(8, 5))
bars = ax.barh(funnel["stage"].astype(str), funnel["n"], color=sns.color_palette("Blues_r", len(funnel)))
ax.invert_yaxis()
ax.set_xlabel("Number of Applications")
ax.set_title("Recruiting Funnel: Applications by Stage")
for bar, val in zip(bars, funnel["n"]):
    ax.text(val + 3, bar.get_y() + bar.get_height()/2, str(val), va="center")
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "01_recruiting_funnel.png"), dpi=150)
plt.close()

# ------------------------------------------------------------
# 2. Monthly application trend
# ------------------------------------------------------------
trend = pd.read_sql("""
    SELECT d.year, d.month, d.month_name, COUNT(*) as n
    FROM fact_applications f
    JOIN dim_date d ON f.applied_date_key = d.date_key
    GROUP BY d.year, d.month, d.month_name
    ORDER BY d.year, d.month
""", conn)
trend["label"] = trend["month_name"].str[:3] + " " + trend["year"].astype(str)

fig, ax = plt.subplots(figsize=(11, 5))
ax.plot(trend["label"], trend["n"], marker="o", color="#2b6cb0")
ax.set_title("Monthly Application Volume Trend")
ax.set_ylabel("Applications")
plt.xticks(rotation=45, ha="right")
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "02_monthly_trend.png"), dpi=150)
plt.close()

# ------------------------------------------------------------
# 3. Source effectiveness (hire rate by source)
# ------------------------------------------------------------
source_perf = pd.read_sql("""
    SELECT c.source,
           COUNT(*) as n_applications,
           ROUND(100.0*SUM(CASE WHEN f.is_hired=1 THEN 1 ELSE 0 END)/COUNT(*), 2) as hire_rate_pct
    FROM fact_applications f
    JOIN dim_candidate c ON f.candidate_key = c.candidate_key
    GROUP BY c.source
    ORDER BY hire_rate_pct DESC
""", conn)

fig, ax = plt.subplots(figsize=(8, 5))
sns.barplot(data=source_perf, x="hire_rate_pct", y="source", hue="source",
            palette="crest", ax=ax, legend=False)
ax.set_xlabel("Hire Rate (%)")
ax.set_ylabel("Source")
ax.set_title("Candidate Source Effectiveness (Application -> Hire Rate)")
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "03_source_effectiveness.png"), dpi=150)
plt.close()

# ------------------------------------------------------------
# 4. Time-to-hire by department
# ------------------------------------------------------------
tth = pd.read_sql("""
    SELECT j.department, f.days_to_close
    FROM fact_applications f
    JOIN dim_job j ON f.job_key = j.job_key
    WHERE f.is_hired = 1 AND f.days_to_close IS NOT NULL
""", conn)

fig, ax = plt.subplots(figsize=(9, 5))
sns.boxplot(data=tth, x="department", y="days_to_close", hue="department",
            palette="Set2", ax=ax, legend=False)
ax.set_title("Time-to-Hire Distribution by Department")
ax.set_ylabel("Days to Hire")
plt.xticks(rotation=30, ha="right")
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "04_time_to_hire_by_dept.png"), dpi=150)
plt.close()

print(f"Saved 4 charts to {OUT_DIR}")
for f in sorted(os.listdir(OUT_DIR)):
    print(f"  - {f}")
