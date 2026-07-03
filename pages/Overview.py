import streamlit as st
from utils import load_students, year_filter_options

st.title("🎓 Student Risk Dashboard")
st.caption("Faculty overview — all students ranked by dropout risk")

df = load_students()

# ── Top metrics ───────────────────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Students",  len(df))
col2.metric("🔴 High Risk",    len(df[df["risk_band"].isin(["high", "critical"])]))
col3.metric("🟡 Medium Risk",  len(df[df["risk_band"] == "medium"]))
col4.metric("🟢 Low Risk",     len(df[df["risk_band"] == "low"]))

st.divider()

# ── Sidebar filters ───────────────────────────────────────────────────────────
st.sidebar.header("Filters")
filter_band = st.sidebar.selectbox("Risk band", ["All", "high", "medium", "low"])
filter_year = st.sidebar.selectbox("Year", year_filter_options(df))

if filter_band == "high":
    df = df[df["risk_band"].isin(["high", "critical"])]
elif filter_band != "All":
    df = df[df["risk_band"] == filter_band]

if filter_year != "All":
    df = df[df["year_label"] == filter_year]

# ── Student table ─────────────────────────────────────────────────────────────
st.subheader(f"Showing {len(df)} students")

st.dataframe(
    df[[
        "student_id", "department", "year_label", "cgpa",
        "attendance_percentage", "backlog_count", "fee_delay_days",
        "risk_score", "Risk", "recommended_intervention"
    ]].rename(columns={"risk_score": "confidence", "year_label": "year"}),
    use_container_width=True,
    hide_index=True
)