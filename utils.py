import sqlite3
import pandas as pd

# ── Constants ────────────────────────────────────────────────────────────────

# current_year is stored as 1/2/3/4 in the DB — map to readable labels for display
YEAR_LABELS = {1: "FY", 2: "SY", 3: "TY", 4: "Final Year"}

# Edit these lists as your team's roster changes
MENTOR_LIST = ["Dr. Sharma", "Dr. Mehta", "Prof. Iyer", "Prof. Kulkarni", "Ms. Rao"]

# Escalation contacts — people with more authority than a peer mentor
ESCALATION_CONTACTS = ["Counselor - Dr. Nair", "Academic Dean", "Financial Aid Office", "Department HOD"]

# ── Helpers ───────────────────────────────────────────────────────────────────

def load_students():
    """Load the students table from the DB, with display columns added."""
    conn = sqlite3.connect("dashboard.db")
    df = pd.read_sql("SELECT * FROM students ORDER BY prediction_confidence DESC", conn)
    conn.close()

    df["risk_band"] = df["risk_band"].str.lower().str.strip()
    df["year_label"] = df["current_year"].map(YEAR_LABELS).fillna(df["current_year"].astype(str))
    df["Risk"] = df["risk_band"].apply(risk_badge)
    return df


def load_workflow():
    """Load the mentoring workflow table from the DB."""
    conn = sqlite3.connect("dashboard.db")
    df = pd.read_sql("SELECT * FROM mentoring_workflow", conn)
    conn.close()
    return df


def risk_badge(band):
    """Return a coloured emoji label for a risk band string."""
    if band in ("high", "critical"): return "🔴 High"
    elif band == "medium":           return "🟡 Medium"
    else:                            return "🟢 Low"


def append_history(old_history, entry):
    """
    Append a new entry to the pipe-separated history string.
    pandas reads SQL NULLs as NaN (a float), so we use pd.isna()
    instead of a plain truthy check.
    """
    if pd.isna(old_history) or old_history == "":
        old_history = ""
    return (old_history + " | " if old_history else "") + entry


def year_filter_options(df):
    """Return sorted year label options for the sidebar filter."""
    return ["All"] + sorted(
        df["year_label"].dropna().unique().tolist(),
        key=lambda y: list(YEAR_LABELS.values()).index(y) if y in YEAR_LABELS.values() else 99
    )