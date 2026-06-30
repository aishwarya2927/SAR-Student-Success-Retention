import sqlite3
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Student Risk Dashboard", layout="wide")
st.title("🎓 Student Risk Dashboard")

conn = sqlite3.connect("dashboard.db")
df = pd.read_sql("SELECT * FROM students ORDER BY risk_score DESC", conn)
conn.close()
df["risk_band"] = df["risk_band"].str.lower().str.strip()

# current_year in the DB is numeric (1,2,3,4) — map to readable labels for display only.
# The raw numeric column stays untouched in the database.
YEAR_LABELS = {1: "FY", 2: "SY", 3: "TY", 4: "Final Year"}
df["year_label"] = df["current_year"].map(YEAR_LABELS).fillna(df["current_year"].astype(str))

def badge(band):
    if band in ("high", "critical"): return "🔴 High"
    elif band == "medium": return "🟡 Medium"
    else: return "🟢 Low"

df["Risk"] = df["risk_band"].apply(badge)

# Metrics at top
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Students", len(df))
col2.metric("🔴 High Risk", len(df[df["risk_band"].isin(["high", "critical"])]))
col3.metric("🟡 Medium Risk", len(df[df["risk_band"]=="medium"]))
col4.metric("🟢 Low Risk", len(df[df["risk_band"]=="low"]))

st.divider()

# Sidebar filters
st.sidebar.title("Filters")
filter_band = st.sidebar.selectbox("Filter by risk band", ["All", "high", "medium", "low"])

# Year classification filter (FY/SY/TY/Final Year)
year_options = ["All"] + sorted(df["year_label"].dropna().unique().tolist(), key=lambda y: list(YEAR_LABELS.values()).index(y) if y in YEAR_LABELS.values() else 99)
filter_year = st.sidebar.selectbox("Filter by year", year_options)

if filter_band == "high":
    df = df[df["risk_band"].isin(["high", "critical"])]
elif filter_band != "All":
    df = df[df["risk_band"] == filter_band]

if filter_year != "All":
    df = df[df["year_label"] == filter_year]

st.subheader(f"Showing {len(df)} students")

st.dataframe(
    df[["student_id", "department", "year_label", "cgpa", "attendance_percentage",
        "backlog_count", "fee_delay_days", "risk_score", "Risk",
        "recommended_intervention"]].rename(columns={"risk_score": "confidence", "year_label": "year"}),
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

st.write("**Year:**", student["year_label"])
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

# NEW: Student Comparison
st.subheader("Compare Two Students")

comp_col1, comp_col2 = st.columns(2)
with comp_col1:
    student_a_id = st.selectbox("Student A", df["student_id"].tolist(), key="student_a")
with comp_col2:
    # default to a different student than A where possible, for a sane starting comparison
    other_ids = [s for s in df["student_id"].tolist() if s != student_a_id]
    default_b = other_ids[0] if other_ids else student_a_id
    student_b_id = st.selectbox(
        "Student B",
        df["student_id"].tolist(),
        index=df["student_id"].tolist().index(default_b),
        key="student_b"
    )

if student_a_id == student_b_id:
    st.info("Select two different students to compare.")
else:
    student_a = df[df["student_id"] == student_a_id].iloc[0]
    student_b = df[df["student_id"] == student_b_id].iloc[0]

    compare_metrics = ["cgpa", "attendance_percentage", "backlog_count", "fee_delay_days", "risk_score"]
    metric_labels = ["CGPA", "Attendance %", "Backlogs", "Fee Delay (days)", "Risk Score"]

    fig_compare = go.Figure()
    fig_compare.add_trace(go.Bar(
        name=student_a_id,
        x=metric_labels,
        y=[student_a[m] for m in compare_metrics],
        marker_color="#4C9BE8"
    ))
    fig_compare.add_trace(go.Bar(
        name=student_b_id,
        x=metric_labels,
        y=[student_b[m] for m in compare_metrics],
        marker_color="#E85C5C"
    ))
    fig_compare.update_layout(
        barmode="group",
        title=f"{student_a_id} vs {student_b_id}",
        yaxis_title="Value"
    )
    st.plotly_chart(fig_compare, use_container_width=True)

    # Quick side-by-side summary table underneath the chart
    summary_df = pd.DataFrame({
        "Metric": ["Department", "Year", "Risk Band"] + metric_labels,
        student_a_id: [student_a["department"], student_a["year_label"], student_a["risk_band"].upper()] +
                       [student_a[m] for m in compare_metrics],
        student_b_id: [student_b["department"], student_b["year_label"], student_b["risk_band"].upper()] +
                       [student_b[m] for m in compare_metrics],
    })
    st.dataframe(summary_df, use_container_width=True, hide_index=True)

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

st.markdown("#### Update Workflow")

# Editable mentor list — add new mentors here as your team grows. Kept simple
# (in-code list) for now; can move to its own DB table later if needed.
MENTOR_LIST = ["Dr. Sharma", "Dr. Mehta", "Prof. Iyer", "Prof. Kulkarni", "Ms. Rao"]

# Separate list for escalation contacts — these are people/departments with more
# authority or specialized support than a regular mentor (counselor, dean, financial aid).
ESCALATION_CONTACTS = ["Counselor - Dr. Nair", "Academic Dean", "Financial Aid Office", "Department HOD"]

if len(df_workflow) == 0:
    st.caption("Flag a student above before updating their workflow.")
else:
    update_id = st.selectbox("Select flagged student to update", df_workflow["student_id"].tolist(), key="update_student")
    current_row = df_workflow[df_workflow["student_id"] == update_id].iloc[0]
    st.caption(f"Current status: **{current_row['status']}**")

    def append_history(old_history, entry):
        # Keep a simple pipe-separated audit trail in the history column.
        # pandas reads SQL NULLs as NaN (a float), not None or "", so we
        # need pd.isna() here — a plain truthy check misses that case.
        if pd.isna(old_history) or old_history == "":
            old_history = ""
        return (old_history + " | " if old_history else "") + entry

    # --- Visual stepper showing pipeline progress ---
    STAGES = ["flagged", "assigned", "scheduled", "resolved"]
    status = current_row["status"]
    # "escalated" branches off — treat it visually as having passed "assigned" at least
    current_index = STAGES.index(status) if status in STAGES else 1

    def stage_svg():
        width = 700
        height = 70
        n = len(STAGES)
        gap = width / n
        circles = ""
        labels = ""
        lines = ""
        for i, stage in enumerate(STAGES):
            cx = gap * i + gap / 2
            if i < current_index or status == "resolved":
                color = "#4CE87A"  # done
            elif i == current_index:
                color = "#4C9BE8"  # current
            else:
                color = "#3a3f4b"  # upcoming
            if status == "escalated" and stage == "assigned":
                color = "#E8A24C"  # mark assigned as the escalation branch point
            circles += f'<circle cx="{cx}" cy="25" r="12" fill="{color}" />'
            label_color = "#e6e6e6" if i <= current_index else "#888"
            labels += f'<text x="{cx}" y="55" font-size="13" fill="{label_color}" text-anchor="middle">{stage.capitalize()}</text>'
            if i < n - 1:
                line_color = "#4CE87A" if i < current_index else "#3a3f4b"
                lines += f'<line x1="{cx + 14}" y1="25" x2="{cx + gap - 14}" y2="25" stroke="{line_color}" stroke-width="3" />'
        extra = ""
        if status == "escalated":
            extra = '<text x="10" y="68" font-size="12" fill="#E8A24C">⚠ Escalated</text>'
        return f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}">{lines}{circles}{labels}</svg>{extra}'

    st.markdown(stage_svg(), unsafe_allow_html=True)

    st.markdown("")  # small spacer

    # --- Single contextual action based on current status ---
    if status == "flagged":
        st.write("**Next step: Assign a mentor**")
        chosen_mentor = st.selectbox("Mentor", MENTOR_LIST, key="mentor_pick")
        if st.button("Assign Mentor", key="assign_btn", use_container_width=True):
            conn = sqlite3.connect("dashboard.db")
            cursor = conn.cursor()
            new_history = append_history(current_row["history"], f"Assigned to {chosen_mentor}")
            cursor.execute("""
                UPDATE mentoring_workflow
                SET status = 'assigned', assigned_mentor = ?, history = ?
                WHERE student_id = ?
            """, (chosen_mentor, new_history, update_id))
            conn.commit()
            conn.close()
            st.success(f"{update_id} assigned to {chosen_mentor}")
            st.rerun()

    elif status == "assigned":
        st.write("**Next step: Schedule a meeting**")
        meeting_date = st.date_input("Meeting date", key="meeting_date_pick")
        if st.button("Schedule Meeting", key="schedule_btn", use_container_width=True):
            conn = sqlite3.connect("dashboard.db")
            cursor = conn.cursor()
            new_history = append_history(current_row["history"], f"Meeting scheduled for {meeting_date}")
            cursor.execute("""
                UPDATE mentoring_workflow
                SET status = 'scheduled', meeting_date = ?, history = ?
                WHERE student_id = ?
            """, (str(meeting_date), new_history, update_id))
            conn.commit()
            conn.close()
            st.success(f"Meeting scheduled for {update_id}")
            st.rerun()

    elif status == "scheduled":
        st.write("**Next step: Log outcome**")
        outcome = st.text_area("Outcome notes", key="outcome_notes_pick", height=80)

        resolve_col, escalate_col = st.columns(2)
        with resolve_col:
            if st.button("Mark Resolved", key="resolve_btn", use_container_width=True):
                conn = sqlite3.connect("dashboard.db")
                cursor = conn.cursor()
                new_history = append_history(current_row["history"], f"Resolved: {outcome}")
                cursor.execute("""
                    UPDATE mentoring_workflow
                    SET status = 'resolved', outcome_notes = ?, history = ?
                    WHERE student_id = ?
                """, (outcome, new_history, update_id))
                conn.commit()
                conn.close()
                st.success(f"{update_id} marked resolved")
                st.rerun()
        with escalate_col:
            st.caption("Escalating reassigns the case to:")
            escalate_to = st.selectbox("Escalation contact", ESCALATION_CONTACTS, key="escalate_contact_pick")
            if st.button("Escalate", key="escalate_btn", use_container_width=True):
                conn = sqlite3.connect("dashboard.db")
                cursor = conn.cursor()
                new_history = append_history(
                    current_row["history"],
                    f"Escalated to {escalate_to}: {outcome}"
                )
                cursor.execute("""
                    UPDATE mentoring_workflow
                    SET status = 'escalated', assigned_mentor = ?, outcome_notes = ?, history = ?
                    WHERE student_id = ?
                """, (escalate_to, outcome, new_history, update_id))
                conn.commit()
                conn.close()
                st.success(f"{update_id} escalated to {escalate_to}")
                st.rerun()

    elif status == "resolved":
        st.success(f"✅ {update_id}'s case is resolved. No further action needed.")

    elif status == "escalated":
        escalated_to = current_row.get("assigned_mentor", "Unknown")
        st.warning(f"⚠️ {update_id} has been escalated to **{escalated_to}**.")
        st.write("**Final outcome notes**")
        outcome = st.text_area("Update outcome notes", key="escalate_followup_notes", height=80, value=current_row.get("outcome_notes", "") or "")
        if st.button("Mark Resolved", key="resolve_after_escalate_btn", use_container_width=True):
            conn = sqlite3.connect("dashboard.db")
            cursor = conn.cursor()
            new_history = append_history(current_row["history"], f"Resolved after escalation: {outcome}")
            cursor.execute("""
                UPDATE mentoring_workflow
                SET status = 'resolved', outcome_notes = ?, history = ?
                WHERE student_id = ?
            """, (outcome, new_history, update_id))
            conn.commit()
            conn.close()
            st.success(f"{update_id} marked resolved")
            st.rerun()