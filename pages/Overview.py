import ast
import streamlit as st
from auth import authenticator
from utils import load_students, year_filter_options

st.title("🎓 Student Risk Dashboard")
st.caption("Faculty overview — all students ranked by dropout risk")

if st.session_state.get("authentication_status"):
    authenticator.logout("Logout", location="sidebar")
    st.sidebar.write(f"Logged in as **{st.session_state['name']}**")

df = load_students()

df["top_factor"] = df["top_factors"].apply(
    lambda tf: ast.literal_eval(tf)[0]["feature"] if tf and tf != "[]" else "—"
)

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
filter_dept = st.sidebar.selectbox("Department", ["All"] + sorted(df["department"].dropna().unique().tolist()))

if filter_band == "high":
    df = df[df["risk_band"].isin(["high", "critical"])]
elif filter_band != "All":
    df = df[df["risk_band"] == filter_band]

if filter_year != "All":
    df = df[df["year_label"] == filter_year]

if filter_dept != "All":
    df = df[df["department"] == filter_dept]

# ── Student table ─────────────────────────────────────────────────────────────
st.subheader(f"Showing {len(df)} students")

st.dataframe(
    df[[
        "student_id", "department", "year_label", "cgpa",
        "attendance_percentage", "backlog_count", "fee_delay_days",
        "prediction_confidence", "Risk","top_factor", "recommended_intervention"
    ]].rename(columns={"prediction_confidence": "confidence", "year_label": "year"}),
    use_container_width=True,
    hide_index=True
)