"""
transform.py - Transform stage of the ETL pipeline.

Responsible for:
 - Parsing inconsistent date formats
 - Normalizing categorical text (casing, whitespace, source names)
 - Removing exact + logical duplicates
 - Handling missing values with explicit, documented rules
 - Deriving fields needed for analysis (is_hired, days_to_close)
 - Building a conformed date dimension
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

SOURCE_MAP = {
    "linkedin": "LinkedIn",
    "referral": "Referral",
    "naukri": "Naukri",
    "indeed": "Indeed",
    "career site": "Career Site",
    "college fair": "College Fair",
}

STAGE_ORDER = ["Applied", "Screening", "Interview", "Offer", "Hired", "Rejected", "Withdrawn"]


def parse_messy_date(value):
    """Try multiple known date formats; return pd.NaT if unparseable/missing."""
    if pd.isna(value) or str(value).strip() == "":
        return pd.NaT
    value = str(value).strip()
    formats = ["%Y-%m-%d", "%d/%m/%Y", "%d-%b-%Y", "%m/%d/%Y"]
    for fmt in formats:
        try:
            return pd.to_datetime(datetime.strptime(value, fmt))
        except ValueError:
            continue
    # last resort: let pandas infer
    return pd.to_datetime(value, errors="coerce")


def clean_candidates(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["full_name"] = df["full_name"].astype(str).str.strip().str.title()
    df["email"] = df["email"].astype(str).str.strip().str.lower()
    df["source"] = (
        df["source"].astype(str).str.strip().str.lower().map(SOURCE_MAP).fillna("Unknown")
    )
    df["years_experience"] = pd.to_numeric(df["years_experience"], errors="coerce")
    median_exp = df["years_experience"].median()
    df["years_experience"] = df["years_experience"].fillna(median_exp)
    df["location"] = df["location"].astype(str).str.strip().str.title()

    before = len(df)
    df = df.drop_duplicates(subset=["candidate_id"])
    dropped = before - len(df)
    if dropped:
        print(f"[clean_candidates] dropped {dropped} duplicate candidate_id rows")
    return df


def clean_jobs(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["department"] = df["department"].astype(str).str.strip().str.title()
    df["title"] = df["title"].astype(str).str.strip().str.title()
    df["location"] = df["location"].astype(str).str.strip().str.title()
    df["date_opened"] = df["date_opened"].apply(parse_messy_date)
    df["headcount"] = pd.to_numeric(df["headcount"], errors="coerce").fillna(1).astype(int)
    df["status"] = df["status"].astype(str).str.strip().str.title()
    df = df.drop_duplicates(subset=["job_id"])
    return df


def clean_applications(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # exact duplicate rows -> drop
    before = len(df)
    df = df.drop_duplicates()
    exact_dupes = before - len(df)

    # logical duplicates: same candidate+job+applied_date counted once
    before2 = len(df)
    df = df.drop_duplicates(subset=["candidate_id", "job_id", "applied_date"])
    logical_dupes = before2 - len(df)
    print(f"[clean_applications] removed {exact_dupes} exact dupes, "
          f"{logical_dupes} additional logical dupes")

    df["stage"] = df["stage"].astype(str).str.strip().str.title()
    df.loc[~df["stage"].isin(STAGE_ORDER), "stage"] = "Unknown"

    df["applied_date"] = df["applied_date"].apply(parse_messy_date)
    df["closed_date"] = df["closed_date"].apply(parse_messy_date)

    # rows with no applied_date are unusable for funnel/trend analysis -> drop, but log it
    missing_applied = df["applied_date"].isna().sum()
    df = df.dropna(subset=["applied_date"])
    print(f"[clean_applications] dropped {missing_applied} rows with unparseable/missing applied_date")

    df["is_hired"] = df["stage"] == "Hired"
    df["days_to_close"] = (df["closed_date"] - df["applied_date"]).dt.days
    # negative days_to_close is a data quality error (closed before applied) -> null it out
    bad_duration = (df["days_to_close"] < 0).sum()
    df.loc[df["days_to_close"] < 0, "days_to_close"] = np.nan
    if bad_duration:
        print(f"[clean_applications] nulled {bad_duration} rows with closed_date before applied_date")

    return df


def build_date_dim(dates: pd.Series) -> pd.DataFrame:
    """Build a conformed date dimension from the min/max of all dates seen."""
    dates = dates.dropna()
    start, end = dates.min(), dates.max()
    all_days = pd.date_range(start, end, freq="D")
    dim = pd.DataFrame({"full_date": all_days})
    dim["date_key"] = dim["full_date"].dt.strftime("%Y%m%d").astype(int)
    dim["year"] = dim["full_date"].dt.year
    dim["quarter"] = dim["full_date"].dt.quarter
    dim["month"] = dim["full_date"].dt.month
    dim["month_name"] = dim["full_date"].dt.month_name()
    dim["week"] = dim["full_date"].dt.isocalendar().week.astype(int)
    dim["day_of_week"] = dim["full_date"].dt.day_name()
    return dim[["date_key", "full_date", "year", "quarter", "month", "month_name", "week", "day_of_week"]]


def clean_recruiter_activity(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df["recruiter_name"] = df["recruiter_name"].astype(str).str.strip().str.title()
    return df.drop_duplicates()


def transform_all(raw: dict) -> dict:
    candidates = clean_candidates(raw["candidates"])
    jobs = clean_jobs(raw["jobs"])
    applications = clean_applications(raw["applications"])
    activity = clean_recruiter_activity(raw["recruiter_activity"])

    all_dates = pd.concat([
        applications["applied_date"], applications["closed_date"], jobs["date_opened"]
    ])
    dim_date = build_date_dim(all_dates)

    return {
        "candidates": candidates,
        "jobs": jobs,
        "applications": applications,
        "recruiter_activity": activity,
        "dim_date": dim_date,
    }


if __name__ == "__main__":
    from extract import extract_all
    raw = extract_all()
    clean = transform_all(raw)
    for name, df in clean.items():
        print(f"{name}: {df.shape[0]} rows after cleaning")
