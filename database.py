import sqlite3
import pandas as pd
import requests

conn = sqlite3.connect("dashboard.db")
cursor = conn.cursor()

cursor.execute("PRAGMA foreign_keys = ON")

cursor.execute("""
CREATE TABLE IF NOT EXISTS students(
    student_id TEXT PRIMARY KEY, 
    department TEXT,
    current_year TEXT,
    academic_risk_band TEXT,
    attendance_percentage REAL, 
    backlog_count INTEGER, 
    fee_delay_days INTEGER, 
    cgpa REAL,
    recommended_intervention TEXT,
    risk_score REAL,
    risk_band TEXT,
    score_source TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS risk_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT,
    risk_score REAL,
    risk_band TEXT,
    timestamp TEXT,
    FOREIGN KEY (student_id) REFERENCES students(student_id))
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS mentoring_workflow (
    student_id TEXT PRIMARY KEY,
    status TEXT CHECK(status IN ('flagged','assigned','scheduled','resolved','escalated')),
    assigned_mentor TEXT,
    meeting_date TEXT,
    outcome_notes TEXT,
    history TEXT,
    FOREIGN KEY (student_id) REFERENCES students(student_id)
)
""")

conn.commit()

df = pd.read_csv("student_success_dataset_30000.csv")

# Keep old functions as fallback
def band_to_score(band):
    if "Critical" in band: return 90
    elif "High" in band: return 75
    elif "Moderate" in band: return 55
    else: return 30

def band_to_simple(band):
    if "Critical" in band or "High" in band: return "high"
    elif "Moderate" in band: return "medium"
    else: return "low"

# New function — calls real API
# Now returns a THIRD value: source = "api" or "fallback", so we always know
# which students actually got a real XGBoost score vs an estimated one.
def get_real_risk(row):
    try:
        student_dict = row.to_dict()
        student_dict["current_year"] = str(student_dict["current_year"])
        response = requests.post(
            "http://localhost:8000/predict",
            json=student_dict,
            timeout=5
        )
        response.raise_for_status()  # don't silently accept HTTP errors (4xx/5xx)
        result = response.json()

        # Validate the response actually has what we expect before trusting it
        if "risk_score" not in result or "risk_band" not in result:
            raise ValueError(f"API response missing expected keys: {result}")

        return result["risk_score"], result["risk_band"].lower(), "api"

    except Exception as e:
        print(f"  [WARN] API call failed for {row['student_id']}: {e}")
        return band_to_score(row["academic_risk_band"]), band_to_simple(row["academic_risk_band"]), "fallback"

# Use only first 200 students for now
df = df.head(200)

print("Getting real risk scores from Person A's API...")
df[["risk_score", "risk_band", "score_source"]] = df.apply(
    lambda row: pd.Series(get_real_risk(row)), axis=1
)

n_api = (df["score_source"] == "api").sum()
n_fallback = (df["score_source"] == "fallback").sum()
print(f"Done. {n_api} scored by API, {n_fallback} fell back to estimated scores.")
if n_fallback > 0:
    print(f"  -> Fallback student_ids: {df[df['score_source']=='fallback']['student_id'].tolist()}")

df_students = df[[
    "student_id",
    "department", 
    "current_year",
    "cgpa",
    "attendance_percentage",
    "backlog_count",
    "fee_delay_days",
    "academic_risk_band",
    "recommended_intervention",
    "risk_score",
    "risk_band",
    "score_source"
]]

df_students.to_sql("students", conn, if_exists="replace", index=False)

print(f"Loaded {len(df_students)} students successfully")
conn.close()