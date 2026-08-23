"""
generate_raw_data.py
---------------------
Generates synthetic, deliberately-messy raw recruiting data to simulate
what a Talent Acquisition system would dump into a raw/landing zone
(in production this would be the HDFS/Hive raw layer).

Messiness injected on purpose (mirrors real-world data):
- Inconsistent date formats
- Missing values
- Duplicate rows
- Inconsistent casing / whitespace in categorical fields
- Mixed types in numeric-looking columns

Run: python3 generate_raw_data.py
Outputs into ../data/raw/
"""

import random
import csv
import json
import os
from datetime import datetime, timedelta

random.seed(42)

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
os.makedirs(OUT_DIR, exist_ok=True)

FIRST_NAMES = ["Aarav","Priya","Rohan","Sneha","Vikram","Anjali","Karan","Neha",
               "Arjun","Divya","Sanjay","Pooja","Rahul","Isha","Aditya","Meera",
               "Nikhil","Ritu","Varun","Kavya"]
LAST_NAMES = ["Sharma","Verma","Patel","Gupta","Reddy","Kumar","Singh","Mehta",
              "Nair","Iyer","Das","Chopra","Rao","Bose","Kapoor"]

SOURCES = ["LinkedIn", "linkedin", "Referral", "Naukri", "Indeed", "Career Site",
           "career site", "Referral ", "College Fair", None]

DEPARTMENTS = ["Engineering", "Data & Analytics", "Product", "Sales", "HR", "Marketing"]

LOCATIONS = ["Bengaluru", "Hyderabad", "Pune", "Remote", "Noida", "Chennai"]

STAGES = ["Applied", "Screening", "Interview", "Offer", "Hired", "Rejected", "Withdrawn"]

RECRUITERS = [("R001","Anita Rao"), ("R002","Suresh Menon"), ("R003","Kavita Joshi"),
              ("R004","Deepak Nair"), ("R005","Farah Khan")]


def rand_date(start, end):
    delta = end - start
    return start + timedelta(days=random.randint(0, delta.days))


def messy_date(d):
    """Return date in one of several inconsistent formats, sometimes null."""
    fmt_choice = random.random()
    if fmt_choice < 0.05:
        return ""  # missing
    elif fmt_choice < 0.4:
        return d.strftime("%Y-%m-%d")
    elif fmt_choice < 0.7:
        return d.strftime("%d/%m/%Y")
    elif fmt_choice < 0.9:
        return d.strftime("%d-%b-%Y")
    else:
        return d.strftime("%m/%d/%Y")


# ---------------------------------------------------------------
# 1. JOBS (job requisitions)
# ---------------------------------------------------------------
jobs = []
job_open_dates = {}
for i in range(1, 41):
    job_id = f"JOB{i:04d}"
    dept = random.choice(DEPARTMENTS)
    title = random.choice([
        "Data Analyst", "Software Engineer", "Data Scientist", "Product Manager",
        "Sales Executive", "HR Business Partner", "Marketing Analyst",
        "Backend Developer", "ML Engineer", "Business Analyst"
    ])
    opened = rand_date(datetime(2024,1,1), datetime(2025,6,1))
    job_open_dates[job_id] = opened
    jobs.append({
        "job_id": job_id,
        "title": title,
        "department": dept if random.random() > 0.03 else dept.upper(),
        "location": random.choice(LOCATIONS),
        "date_opened": messy_date(opened),
        "headcount": random.choice([1,1,1,2,3]),
        "status": random.choice(["Open","Closed","On Hold"])
    })

with open(os.path.join(OUT_DIR, "jobs.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=jobs[0].keys())
    w.writeheader()
    w.writerows(jobs)

# ---------------------------------------------------------------
# 2. CANDIDATES
# ---------------------------------------------------------------
candidates = []
for i in range(1, 601):
    cand_id = f"CAND{i:05d}"
    fn = random.choice(FIRST_NAMES)
    ln = random.choice(LAST_NAMES)
    exp = round(random.uniform(0, 12), 1)
    candidates.append({
        "candidate_id": cand_id,
        "full_name": f" {fn} {ln} " if random.random() < 0.1 else f"{fn} {ln}",
        "email": f"{fn.lower()}.{ln.lower()}{i}@example.com",
        "years_experience": exp if random.random() > 0.05 else "",
        "source": random.choice(SOURCES),
        "location": random.choice(LOCATIONS),
    })

with open(os.path.join(OUT_DIR, "candidates.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=candidates[0].keys())
    w.writeheader()
    w.writerows(candidates)

# ---------------------------------------------------------------
# 3. APPLICATIONS (the core fact - candidate applies to job, moves through stages)
# ---------------------------------------------------------------
applications = []
app_id_counter = 1
for cand in candidates:
    n_apps = random.choice([1,1,1,2,2,3])
    for _ in range(n_apps):
        job = random.choice(jobs)
        applied_date = rand_date(job_open_dates[job["job_id"]], job_open_dates[job["job_id"]] + timedelta(days=90))
        stage = random.choices(STAGES, weights=[10,25,25,15,10,20,5])[0]

        # time in stage - hired/rejected have a "closed" date
        closed_date = None
        if stage in ("Hired", "Rejected", "Withdrawn"):
            closed_date = applied_date + timedelta(days=random.randint(3, 60))

        applications.append({
            "application_id": f"APP{app_id_counter:06d}",
            "candidate_id": cand["candidate_id"],
            "job_id": job["job_id"],
            "recruiter_id": random.choice(RECRUITERS)[0],
            "applied_date": messy_date(applied_date),
            "stage": stage if random.random() > 0.02 else stage.lower(),
            "closed_date": messy_date(closed_date) if closed_date else "",
        })
        app_id_counter += 1

# inject some exact duplicate rows (common real-world ETL issue)
applications += random.sample(applications, 25)

with open(os.path.join(OUT_DIR, "applications.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=applications[0].keys())
    w.writeheader()
    w.writerows(applications)

# ---------------------------------------------------------------
# 4. RECRUITER ACTIVITY (JSON - simulates a semi-structured log/event source)
# ---------------------------------------------------------------
activity_log = []
for rid, rname in RECRUITERS:
    for _ in range(random.randint(80,150)):
        activity_log.append({
            "recruiter_id": rid,
            "recruiter_name": rname,
            "event_type": random.choice(["resume_review","phone_screen","interview_scheduled","offer_sent"]),
            "timestamp": rand_date(datetime(2024,1,1), datetime(2025,6,1)).isoformat(),
            "application_id": random.choice(applications)["application_id"]
        })

with open(os.path.join(OUT_DIR, "recruiter_activity.json"), "w") as f:
    json.dump(activity_log, f, indent=2)

print(f"Generated: {len(jobs)} jobs, {len(candidates)} candidates, "
      f"{len(applications)} applications, {len(activity_log)} activity events")
print(f"Files written to: {os.path.abspath(OUT_DIR)}")
