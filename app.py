import streamlit as st
from utils import load_students

st.set_page_config(
    page_title="Student Risk Dashboard",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

df = load_students()

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
    <h1 style='text-align: center; padding-top: 1rem;'>🎓 Student Success & Retention System</h1>
    <p style='text-align: center; color: #888; font-size: 1.1rem;'>
        Faculty Dashboard — Agentic AI Early Warning System
    </p>
""", unsafe_allow_html=True)

st.divider()

# ── Quick stats ───────────────────────────────────────────────────────────────
total     = len(df)
high      = len(df[df["risk_band"].isin(["high", "critical"])])
medium    = len(df[df["risk_band"] == "medium"])
low       = len(df[df["risk_band"] == "low"])

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Students",  total)
col2.metric("🔴 High Risk",    high,   delta=f"{round(high/total*100)}% of students",   delta_color="inverse")
col3.metric("🟡 Medium Risk",  medium, delta=f"{round(medium/total*100)}% of students", delta_color="off")
col4.metric("🟢 Low Risk",     low,    delta=f"{round(low/total*100)}% of students",    delta_color="normal")

st.divider()

# ── Nav cards ─────────────────────────────────────────────────────────────────
st.markdown("### Navigate to")
st.markdown("")

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown("""
        <div style='background:#1e2130; border-radius:12px; padding:24px; text-align:center; border: 1px solid #2e3250; min-height: 140px;'>
            <div style='font-size:2rem;'>📊</div>
            <div style='font-size:1.1rem; font-weight:600; margin-top:8px;'>Overview</div>
            <div style='color:#888; font-size:0.85rem; margin-top:6px;'>All students ranked by risk score with filters</div>
        </div>
    """, unsafe_allow_html=True)
    st.markdown("")
    if st.button("Go to Overview", use_container_width=True, key="nav_overview"):
        st.switch_page("pages/Overview.py")

with c2:
    st.markdown("""
        <div style='background:#1e2130; border-radius:12px; padding:24px; text-align:center; border: 1px solid #2e3250; min-height: 140px;'>
            <div style='font-size:2rem;'>👤</div>
            <div style='font-size:1.1rem; font-weight:600; margin-top:8px;'>Student Detail</div>
            <div style='color:#888; font-size:0.85rem; margin-top:6px;'>Deep dive into any student's risk profile</div>
        </div>
    """, unsafe_allow_html=True)
    st.markdown("")
    if st.button("Go to Student Detail", use_container_width=True, key="nav_detail"):
        st.switch_page("pages/Student_Detail.py")

with c3:
    st.markdown("""
        <div style='background:#1e2130; border-radius:12px; padding:24px; text-align:center; border: 1px solid #2e3250; min-height: 140px;'>
            <div style='font-size:2rem;'>⚖️</div>
            <div style='font-size:1.1rem; font-weight:600; margin-top:8px;'>Compare Students</div>
            <div style='color:#888; font-size:0.85rem; margin-top:6px;'>Side-by-side comparison of two students</div>
        </div>
    """, unsafe_allow_html=True)
    st.markdown("")
    if st.button("Go to Comparison", use_container_width=True, key="nav_compare"):
        st.switch_page("pages/Comparison.py")

with c4:
    st.markdown("""
        <div style='background:#1e2130; border-radius:12px; padding:24px; text-align:center; border: 1px solid #2e3250; min-height: 140px;'>
            <div style='font-size:2rem;'>🗂️</div>
            <div style='font-size:1.1rem; font-weight:600; margin-top:8px;'>Workflow Tracker</div>
            <div style='color:#888; font-size:0.85rem; margin-top:6px;'>Flag students and track mentoring progress</div>
        </div>
    """, unsafe_allow_html=True)
    st.markdown("")
    if st.button("Go to Workflow", use_container_width=True, key="nav_workflow"):
        st.switch_page("pages/Workflow.py")

st.divider()

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("""
    <p style='text-align:center; color:#555; font-size:0.8rem;'>
        Agentic AI Student Success & Retention System &nbsp;|&nbsp; Person C — Faculty Dashboard
    </p>
""", unsafe_allow_html=True)