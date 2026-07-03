import sqlite3
import streamlit as st
from utils import load_students, load_workflow, append_history, MENTOR_LIST, ESCALATION_CONTACTS

st.title("🗂️ Mentoring Workflow Tracker")
st.caption("Flag at-risk students, assign mentors and track case progress")

df          = load_students()
df_workflow = load_workflow()

# ── Current workflow table ────────────────────────────────────────────────────
st.subheader("Active Cases")
if len(df_workflow) == 0:
    st.info("No students flagged yet.")
else:
    st.dataframe(df_workflow, use_container_width=True, hide_index=True)

st.divider()

# ── Flag a student ────────────────────────────────────────────────────────────
st.subheader("Flag a Student")
selected_id = st.selectbox("Select student to flag", df["student_id"].tolist())

if st.button("🚩 Flag Student", use_container_width=False):
    conn   = sqlite3.connect("dashboard.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR IGNORE INTO mentoring_workflow (student_id, status) VALUES (?, ?)",
        (selected_id, "flagged")
    )
    conn.commit()
    conn.close()
    st.success(f"{selected_id} flagged successfully!")
    st.rerun()

st.divider()

# ── Update workflow ───────────────────────────────────────────────────────────
st.subheader("Update Case")

if len(df_workflow) == 0:
    st.caption("Flag a student above before updating their workflow.")
else:
    update_id   = st.selectbox("Select case to update", df_workflow["student_id"].tolist(), key="update_student")
    current_row = df_workflow[df_workflow["student_id"] == update_id].iloc[0]
    status      = current_row["status"]

    # ── Visual stepper ────────────────────────────────────────────────────────
    STAGES        = ["flagged", "assigned", "scheduled", "resolved"]
    current_index = STAGES.index(status) if status in STAGES else 1

    def stage_svg():
        width, height = 700, 70
        n   = len(STAGES)
        gap = width / n
        circles = labels = lines = ""

        for i, stage in enumerate(STAGES):
            cx = gap * i + gap / 2

            # Colour logic: green = done, blue = current, grey = upcoming
            if i < current_index or status == "resolved":
                color = "#4CE87A"
            elif i == current_index:
                color = "#4C9BE8"
            else:
                color = "#3a3f4b"

            # Escalation branches off at "assigned" — show it in orange
            if status == "escalated" and stage == "assigned":
                color = "#E8A24C"

            circles += f'<circle cx="{cx}" cy="25" r="12" fill="{color}" />'

            label_color = "#e6e6e6" if i <= current_index else "#888"
            labels += f'<text x="{cx}" y="55" font-size="13" fill="{label_color}" text-anchor="middle">{stage.capitalize()}</text>'

            if i < n - 1:
                line_color = "#4CE87A" if i < current_index else "#3a3f4b"
                lines += f'<line x1="{cx+14}" y1="25" x2="{cx+gap-14}" y2="25" stroke="{line_color}" stroke-width="3"/>'

        extra = '<text x="10" y="68" font-size="12" fill="#E8A24C">⚠ Escalated</text>' if status == "escalated" else ""
        return f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}">{lines}{circles}{labels}</svg>{extra}'

    st.markdown(stage_svg(), unsafe_allow_html=True)
    st.markdown("")  # spacer

    # ── Contextual next action ────────────────────────────────────────────────
    if status == "flagged":
        st.write("**Next step: Assign a mentor**")
        chosen_mentor = st.selectbox("Mentor", MENTOR_LIST, key="mentor_pick")
        if st.button("Assign Mentor", use_container_width=True):
            conn   = sqlite3.connect("dashboard.db")
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE mentoring_workflow SET status='assigned', assigned_mentor=?, history=? WHERE student_id=?",
                (chosen_mentor, append_history(current_row["history"], f"Assigned to {chosen_mentor}"), update_id)
            )
            conn.commit(); conn.close()
            st.success(f"{update_id} assigned to {chosen_mentor}")
            st.rerun()

    elif status == "assigned":
        st.write("**Next step: Schedule a meeting**")
        meeting_date = st.date_input("Meeting date", key="meeting_date_pick")
        if st.button("Schedule Meeting", use_container_width=True):
            conn   = sqlite3.connect("dashboard.db")
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE mentoring_workflow SET status='scheduled', meeting_date=?, history=? WHERE student_id=?",
                (str(meeting_date), append_history(current_row["history"], f"Meeting scheduled for {meeting_date}"), update_id)
            )
            conn.commit(); conn.close()
            st.success(f"Meeting scheduled for {update_id}")
            st.rerun()

    elif status == "scheduled":
        st.write("**Next step: Log outcome**")
        outcome = st.text_area("Outcome notes", key="outcome_notes_pick", height=80)

        resolve_col, escalate_col = st.columns(2)
        with resolve_col:
            if st.button("✅ Mark Resolved", use_container_width=True):
                conn   = sqlite3.connect("dashboard.db")
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE mentoring_workflow SET status='resolved', outcome_notes=?, history=? WHERE student_id=?",
                    (outcome, append_history(current_row["history"], f"Resolved: {outcome}"), update_id)
                )
                conn.commit(); conn.close()
                st.success(f"{update_id} marked resolved")
                st.rerun()

        with escalate_col:
            st.caption("Escalating reassigns the case to:")
            escalate_to = st.selectbox("Escalation contact", ESCALATION_CONTACTS, key="escalate_contact_pick")
            if st.button("⚠️ Escalate", use_container_width=True):
                conn   = sqlite3.connect("dashboard.db")
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE mentoring_workflow SET status='escalated', assigned_mentor=?, outcome_notes=?, history=? WHERE student_id=?",
                    (escalate_to, outcome, append_history(current_row["history"], f"Escalated to {escalate_to}: {outcome}"), update_id)
                )
                conn.commit(); conn.close()
                st.success(f"{update_id} escalated to {escalate_to}")
                st.rerun()

    elif status == "resolved":
        st.success(f"✅ {update_id}'s case is resolved. No further action needed.")

    elif status == "escalated":
        escalated_to = current_row.get("assigned_mentor", "Unknown")
        st.warning(f"⚠️ {update_id} has been escalated to **{escalated_to}**.")
        outcome = st.text_area("Update outcome notes", key="escalate_followup_notes", height=80,
                               value=current_row.get("outcome_notes", "") or "")
        if st.button("✅ Mark Resolved", key="resolve_after_escalate_btn", use_container_width=True):
            conn   = sqlite3.connect("dashboard.db")
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE mentoring_workflow SET status='resolved', outcome_notes=?, history=? WHERE student_id=?",
                (outcome, append_history(current_row["history"], f"Resolved after escalation: {outcome}"), update_id)
            )
            conn.commit(); conn.close()
            st.success(f"{update_id} marked resolved")
            st.rerun()