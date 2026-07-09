import streamlit as st
import plotly.graph_objects as go
from auth import authenticator
from utils import load_students

st.title("⚖️ Compare Students")
st.caption("Select two students to compare their risk profiles side by side")

if st.session_state.get("authentication_status"):
    authenticator.logout("Logout", location="sidebar")
    st.sidebar.write(f"Logged in as **{st.session_state['name']}**")
    
df = load_students()

st.divider()

# ── Student selectors ─────────────────────────────────────────────────────────
col1, col2 = st.columns(2)
with col1:
    student_a_id = st.selectbox("Student A", sorted(df["student_id"].tolist()), key="student_a")
with col2:
    other_ids  = [s for s in df["student_id"].tolist() if s != student_a_id]
    default_b  = other_ids[0] if other_ids else student_a_id
    sorted_ids = sorted(df["student_id"].tolist())
    student_b_id = st.selectbox(
        "Student B",
        sorted_ids,
        index=sorted_ids.index(default_b),
        key="student_b"
    )

st.divider()

# ── Comparison ────────────────────────────────────────────────────────────────
if student_a_id == student_b_id:
    st.info("Select two different students to compare.")
else:
    student_a = df[df["student_id"] == student_a_id].iloc[0]
    student_b = df[df["student_id"] == student_b_id].iloc[0]

    compare_metrics = ["cgpa", "attendance_percentage", "backlog_count", "fee_delay_days", "prediction_confidence"]
    metric_labels   = ["CGPA", "Attendance %", "Backlogs", "Fee Delay (days)", "Prediction Confidence"]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name=student_a_id,
        x=metric_labels,
        y=[student_a[m] for m in compare_metrics],
        marker_color="#4C9BE8"
    ))
    fig.add_trace(go.Bar(
        name=student_b_id,
        x=metric_labels,
        y=[student_b[m] for m in compare_metrics],
        marker_color="#E85C5C"
    ))
    fig.update_layout(
        barmode="group",
        title=f"{student_a_id}  vs  {student_b_id}",
        yaxis_title="Value"
    )
    st.plotly_chart(fig, use_container_width=True)

    # Summary table
    summary_df = {
        "Metric":      ["Department", "Year", "Risk Band"] + metric_labels,
        student_a_id:  [student_a["department"], student_a["year_label"], student_a["risk_band"].upper()] +
                       [student_a[m] for m in compare_metrics],
        student_b_id:  [student_b["department"], student_b["year_label"], student_b["risk_band"].upper()] +
                       [student_b[m] for m in compare_metrics],
    }
    import pandas as pd
    st.dataframe(pd.DataFrame(summary_df), use_container_width=True, hide_index=True)