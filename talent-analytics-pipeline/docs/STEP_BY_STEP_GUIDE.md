# Step-by-Step Build Guide

Follow this in order. Each step says WHAT to run and WHY we do it.
Don't skip the "why" — that's what you'll actually be asked about in an interview.

---

## STEP 0 — What you need installed first

```bash
python3 --version        # need 3.9+
psql --version            # your PostgreSQL client
```

Then install the Python libraries this project needs:
```bash
pip install pandas numpy matplotlib seaborn psycopg2-binary sqlalchemy --break-system-packages
```

**Why:** pandas/numpy = cleaning data. matplotlib/seaborn = charts.
psycopg2 + sqlalchemy = the actual "phone line" Python uses to talk to Postgres.
Without these two, Python has no way to open a connection to your database.

---

## STEP 1 — Generate the raw (messy) data

```bash
cd talent-analytics-pipeline/etl
python3 generate_raw_data.py
```

**What this does:** creates 4 files inside `data/raw/` —
`jobs.csv`, `candidates.csv`, `applications.csv`, `recruiter_activity.json`.

**Why we do this first:** every pipeline needs a starting point. In real life this
step wouldn't exist — you'd already have real files from the company. We generate
fake-but-realistic messy data here only because we don't have a real company's
export to use. The mess (bad dates, duplicates, inconsistent casing) is
intentional — it's what real data looks like.

---

## STEP 2 — Create the empty database structure in Postgres

```bash
psql -U postgres -c "CREATE DATABASE talent_analytics;"
psql -U postgres -d talent_analytics -f ../sql/schema.sql
```

**What this does:** the first command creates a blank database. The second
command runs `schema.sql`, which creates 5 EMPTY tables inside it:
`dim_candidate`, `dim_job`, `dim_recruiter`, `dim_date`, `fact_applications`.

**Why we do this before loading anything:** you can't put data into a table
that doesn't exist yet. This step just builds the empty shelves — Step 3 is
what actually puts data on them.

**How to check it worked:**
```bash
psql -U postgres -d talent_analytics -c "\dt"
```
This should list all 5 table names, all with 0 rows.

---

## STEP 3 — Run the Python ETL to clean and load the data

```bash
export DB_BACKEND=postgres
export PG_USER=postgres
export PG_PASSWORD=your_actual_password
export PG_DATABASE=talent_analytics

cd ../etl
python3 pipeline.py
```

**What this does, in order (this is the actual "Extract → Transform → Load"):**
1. `extract.py` — opens the 4 raw files and reads them into memory as tables
2. `transform.py` — cleans them: fixes the 4 different date formats into one,
   fixes "linkedin"/"LinkedIn"/"Linkedin " into one consistent "LinkedIn",
   removes duplicate rows, fills or nulls out broken values
3. `load.py` — opens a real connection to your Postgres database and inserts
   the now-clean data into the 5 tables you created in Step 2

**Why these are 3 separate steps and not 1 script:** if loading fails, you want
to know it failed at loading — not have to guess whether the bug was in reading
the file or in cleaning it. Separating them makes it possible to fix one part
without breaking the others.

**How to check it worked:**
```bash
psql -U postgres -d talent_analytics -c "SELECT COUNT(*) FROM fact_applications;"
```
Should return a number close to 974 (a few rows get dropped during cleaning —
that's expected and correct, not a bug).

---

## STEP 4 — Ask real business questions with SQL

```bash
psql -U postgres -d talent_analytics -f ../sql/analytics_queries.sql
```

**What this does:** runs all 7 pre-written questions (funnel, time-to-hire,
source effectiveness, etc.) directly against your now-populated tables.

**Why this step is separate from loading:** the warehouse (Step 3) and the
questions you ask of it (Step 4) are two different jobs. You load data once
a day; you might ask new questions of it 20 times a day. Keeping them separate
means you never have to re-run the whole pipeline just to ask a new question.

---

## STEP 5 — Turn answers into charts

```bash
cd ../analysis
python3 trend_analysis.py
```

**What this does:** runs similar SQL queries from Python, gets the results back
as a small table, and hands that table to matplotlib to draw 4 PNG charts into
`analysis/charts/`.

**Why this matters:** a hiring manager isn't going to read a SQL query result —
they want to glance at a chart. This step is the translation from "correct
number" to "understandable picture."

---

## What "done" looks like

At this point you have:
- 4 raw messy files → cleaned and loaded into 5 organized Postgres tables
- 7 SQL answers to real hiring questions
- 4 charts a non-technical person could actually understand

## What's NOT done yet (next steps, in order of value)
1. **Power BI dashboard** — connect Power BI directly to this same Postgres
   database so the charts become clickable/filterable, not static PNGs
2. **Hive/HBase** — only worth doing if you actually have a Hadoop environment
   to test against; otherwise it stays as an architecture explanation you can
   talk through in an interview
3. **Resume + interview prep** — turning this into words on paper and answers
   you can give out loud
