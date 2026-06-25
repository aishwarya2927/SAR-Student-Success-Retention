import sqlite3
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Student Risk Dashboard", layout="wide")
st.title("🎓 Student Risk Dashboard")

conn = sqlite3.connect("dashboard.db")
df = pd.read_sql("SELECT * FROM students ORDER BY risk_score DESC", conn)
conn.close()

def badge(band):
    if band == "high": return "🔴 High"
    elif band == "medium": return "🟡 Medium"
    else: return "🟢 Low"

df["Risk"] = df["risk_band"].apply(badge)

# Metrics at top
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Students", len(df))
col2.metric("🔴 High Risk", len(df[df["risk_band"]=="high"]))
col3.metric("🟡 Medium Risk", len(df[df["risk_band"]=="medium"]))
col4.metric("🟢 Low Risk", len(df[df["risk_band"]=="low"]))

st.divider()

# Sidebar filter
st.sidebar.title("Filters")
filter_band = st.sidebar.selectbox("Filter by risk band", ["All", "high", "medium", "low"])


if filter_band != "All":
    df = df[df["risk_band"] == filter_band]

st.subheader(f"Showing {len(df)} students")

st.dataframe(
    df[["student_id", "department", "cgpa", "attendance_percentage",
        "backlog_count", "fee_delay_days", "risk_score", "Risk",
        "recommended_intervention"]],
    use_container_width=True,
    hide_index=True
)