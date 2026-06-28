import sqlite3
import streamlit as st
import pandas as pd
import plotly.express as px

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

st.divider()

st.subheader("Student Detail View")

selected_student = st.selectbox("Select a student to view details", df["student_id"].tolist())

student = df[df["student_id"] == selected_student].iloc[0]

col1, col2, col3 = st.columns(3)
col1.metric("CGPA", student["cgpa"])
col2.metric("Attendance", f"{student['attendance_percentage']}%")
col3.metric("Risk score", student["risk_score"])

col4, col5, col6 = st.columns(3)
col4.metric("Backlogs", student["backlog_count"])
col5.metric("Fee Delay Days", student["fee_delay_days"])
col6.metric("Risk Band", student["risk_band"].upper())

st.write("**Recommended Intervention:**", student["recommended_intervention"])

factors = pd.DataFrame({
    "Factor": ["Attendance", "Backlogs", "Fee Delay", "CGPA"],
    "Value": [
        student["attendance_percentage"],
        student["backlog_count"] * 10,
        student["fee_delay_days"],
        student["cgpa"] * 10
    ],
    "Color": ["blue", "red", "orange", "green"]
})

fig = px.bar(
    factors,
    x="Factor",
    y="Value",
    color="Color",
    color_discrete_map={
        "blue": "#4C9BE8",
        "red": "#E85C5C",
        "orange": "#E8A24C",
        "green": "#4CE87A"
    },
    title="Risk Factor Analysis"
)

st.plotly_chart(fig, use_container_width=True)

st.divider()

st.subheader("Mentoring Workflow Tracker")

conn = sqlite3.connect("dashboard.db")
df_workflow = pd.read_sql("SELECT * FROM mentoring_workflow", conn)
conn.close()

if len(df_workflow) == 0:
    st.info("No students flagged yet")
else:
    st.dataframe(df_workflow, use_container_width=True, hide_index=True)

selected_id = st.selectbox("Select student to flag", df["student_id"].tolist())

if st.button("Flag Student"):
    conn = sqlite3.connect("dashboard.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR IGNORE INTO mentoring_workflow
        (student_id, status) VALUES (?, ?)
    """, (selected_id, "flagged"))
    conn.commit()
    conn.close()
    st.success(f"{selected_id} flagged successfully!")
    st.rerun()