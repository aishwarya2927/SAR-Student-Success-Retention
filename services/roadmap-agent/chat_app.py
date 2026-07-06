import requests
def get_faculty_intervention(student_id):
    try:
        response = requests.get(
    f"https://sar-student-success-retention-3kvj.onrender.com/intervention/{student_id}"
)

        if response.status_code == 200:
            return response.json()

        return None

    except Exception:
        return None
def show_faculty_intervention(student_id):
    intervention = get_faculty_intervention(student_id)

    st.subheader("🧑‍🏫 Faculty Approved Intervention Plan")

    if not intervention:
        st.info("No approved intervention plan available yet.")
        return

    st.markdown(
        f"""
        <div class="career-card">
            <h3>✅ Approved Intervention</h3>
            <p><b>Status:</b> {intervention.get("status", "N/A")}</p>
            <p><b>Approved By:</b> {intervention.get("approved_by", "N/A")}</p>
            <p><b>Approved At:</b> {intervention.get("approved_at", "N/A")}</p>
            <hr>
            <p><b>Plan:</b></p>
            <p>{intervention.get("plan", "No plan details available.")}</p>
        </div>
        """,
        unsafe_allow_html=True
    )
from calendar import week
import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR / "utils"))
import re

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from agents.intent_router import classify_intent
from modules.roadmap_generator import generate_improvement_roadmap
from modules.career_module import generate_career_guidance
@st.cache_data(ttl=3600)
def cached_roadmap(student_id):
    return generate_improvement_roadmap(student_id)
def get_faculty_intervention(student_id):

    try:
        response = requests.get(
            f"https://sar-student-success-retention-3kvj.onrender.com/intervention/{student_id}"
        )

        if response.status_code == 200:
            return response.json()

        return None

    except Exception as e:
        return None

def show_faculty_intervention(student_id):

    intervention = get_faculty_intervention(student_id)

    st.subheader("🧑‍🏫 Faculty Approved Intervention Plan")

    if not intervention:
        st.info("No approved intervention available yet.")
        return


    st.markdown(
        f"""
        <div class="career-card">

        <h3>✅ Approved Plan</h3>

        <b>Status:</b> {intervention.get("status")} <br>

        <b>Approved By:</b>
        {intervention.get("approved_by")}

        <br><br>

        📋 <b>Intervention:</b>

        <p>
        {intervention.get("plan") or intervention.get("follow_up_plan") or "<br>".join(intervention.get("recommended_actions", []))}
        </p>

        </div>

        """,
        unsafe_allow_html=True
    )

st.set_page_config(
    page_title="Student Success AI",
    page_icon="🎓",
    layout="wide",
)

# ---------------- GLOBAL CSS ----------------
st.markdown(
    """
<style>

:root {
    --purple: #6C63FF;
    --purple-dark: #4B3FE4;
    --blue: #4F8EF7;
    --green: #10B981;
    --bg-soft: #F6F7FB;
    --text-soft: #6B7280;
}

.stApp {
    background: var(--bg-soft);
}

/* ---------- Header ---------- */
.gradient-header {
    background: linear-gradient(135deg, var(--purple) 0%, var(--blue) 55%, var(--green) 120%);
    padding: 34px 38px;
    border-radius: 22px;
    color: white;
    margin-bottom: 26px;
    box-shadow: 0 12px 30px rgba(76, 63, 228, 0.25);
}
.gradient-header h1 {
    margin: 0 0 6px 0;
    font-size: 34px;
    font-weight: 800;
}
.gradient-header p {
    margin: 0;
    font-size: 15px;
    opacity: 0.92;
}

/* ---------- Generic Cards ---------- */
.card, .ai-card, .metric-card, .career-card, .risk-card, .week-card,
.support-card, .factor-card, .timeline-card, .agent-box {
    background: white;
    border-radius: 18px;
    padding: 20px 22px;
    margin-bottom: 16px;
    box-shadow: 0 6px 20px rgba(17, 24, 39, 0.06);
}

.metric-card {
    text-align: center;
    border-top: 5px solid var(--purple);
}
.metric-title {
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0.4px;
    color: var(--text-soft);
    text-transform: uppercase;
    margin-bottom: 8px;
}
.metric-value {
    font-size: 30px;
    font-weight: 800;
    color: #1F2937;
}
.metric-number {
    font-size: 38px;
    font-weight: 800;
    color: var(--purple);
}

.risk-card { border-left: 7px solid var(--purple); }

.career-card { border-left: 6px solid var(--purple); }

.agent-box {
    border-left: 6px solid var(--blue);
}

.factor-card {
    border-left: 6px solid var(--purple);
}
.factor-header {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 17px;
    font-weight: 700;
    color: #1F2937;
    margin-bottom: 6px;
}
.factor-icon {
    font-size: 22px;
}
.factor-meta {
    font-size: 13px;
    color: var(--text-soft);
    margin-bottom: 8px;
}
.factor-meta b { color: #1F2937; }
.factor-explanation {
    font-size: 13.5px;
    color: #374151;
    line-height: 1.5;
    margin-bottom: 10px;
}
.impact-bar-track {
    width: 100%;
    height: 10px;
    background: #EEF0F6;
    border-radius: 10px;
    overflow: hidden;
}
.impact-bar-fill {
    height: 100%;
    border-radius: 10px;
    background: linear-gradient(90deg, var(--purple), #FF6B6B);
}

.week-card {
    border-top: 5px solid var(--blue);
}

.goal-card {
    background: linear-gradient(135deg, #EEF2FF, #FFFFFF);
    border: 1px solid #E4E7FB;
    border-radius: 16px;
    padding: 18px 20px;
    margin-bottom: 14px;
}
.goal-card h4 {
    margin: 0 0 8px 0;
    color: var(--purple-dark);
}

.action-flashcard {
    background: #FAFAFF;
    border: 1px solid #ECECFB;
    border-radius: 14px;
    padding: 14px 16px;
    margin-bottom: 10px;
}
.action-flashcard .action-label {
    font-size: 12px;
    font-weight: 700;
    color: var(--purple-dark);
    text-transform: uppercase;
    letter-spacing: 0.3px;
    margin-bottom: 4px;
}
.action-flashcard .action-text {
    font-size: 14.5px;
    color: #1F2937;
    margin-bottom: 8px;
}
.outcome-badge {
    display: inline-block;
    background: #E7F9EF;
    color: #067A46;
    font-size: 12px;
    font-weight: 700;
    padding: 5px 12px;
    border-radius: 999px;
}

.risk-tag {
    display: inline-block;
    background: #FFF1E9;
    color: #B4530A;
    font-size: 11.5px;
    font-weight: 700;
    padding: 4px 11px;
    border-radius: 999px;
    margin-left: 8px;
}

.progress-track {
    width: 100%;
    height: 12px;
    background: #EEF0F6;
    border-radius: 10px;
    overflow: hidden;
    margin: 8px 0 4px 0;
}
.progress-fill {
    height: 100%;
    border-radius: 10px;
    background: linear-gradient(90deg, var(--blue), var(--green));
}
.progress-label {
    font-size: 12px;
    color: var(--text-soft);
    font-weight: 600;
}

.support-card {
    background: #F7FBF9;
    border-left: 5px solid var(--green);
}

.skill-badge, .skill-card {
    display: inline-block;
    background: #EDE9FE;
    color: #4B3FE4;
    padding: 9px 16px;
    border-radius: 999px;
    margin: 5px 6px 5px 0;
    font-weight: 600;
    font-size: 13.5px;
}

.timeline-card {
    background: linear-gradient(135deg, #EEF2FF, #ffffff);
    border: 1px solid #E4E7FB;
    border-radius: 16px;
    padding: 18px 20px;
    margin-bottom: 12px;
}
.timeline-card h4 {
    margin: 0 0 6px 0;
    color: var(--purple-dark);
}

.section-title {
    font-size: 20px;
    font-weight: 800;
    color: #1F2937;
    margin: 22px 0 10px 0;
}

.pill {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 700;
}
.pill-purple { background:#EDE9FE; color:#4B3FE4; }
.pill-green { background:#E7F9EF; color:#067A46; }
.pill-blue { background:#E6F0FF; color:#1D5FCE; }

@media (max-width: 768px) {
    .gradient-header h1 { font-size: 26px; }
    .gradient-header { padding: 22px; }
}
</style>
""",
    unsafe_allow_html=True,
)


# ---------------- SIDEBAR ----------------
with st.sidebar:
    st.markdown("### 🎓 Student Profile")

    student_id = st.text_input("Student ID", value="S1001")
    gpa = st.number_input("Current GPA", min_value=0.0, max_value=10.0, value=7.4)
    interest = st.selectbox(
        "Career Interest",
        ["AI", "Web Development", "Cybersecurity", "Data Science", "Other"],
    )

    st.divider()

    st.markdown(
        f"""
        <div class="card" style="padding:16px;">
            <div class="metric-title">Current Snapshot</div>
            <div style="font-size:14px; color:#374151; line-height:1.7;">
                🆔 <b>{student_id}</b><br>
                🎓 GPA: <b>{gpa}</b><br>
                🎯 Interest: <b>{interest}</b>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.divider()
    show_dev_json = st.checkbox("🛠️ Show Developer Raw JSON", value=False)
    st.session_state["show_dev_json"] = show_dev_json

    st.caption("Student Academic Success & Retention Platform")


# ---------------- HEADER ----------------
st.markdown(
    """
<div class="gradient-header">
<h1>🎓 Student Success AI</h1>
<p>Personalized academic roadmap, risk explanation and career guidance powered by Agentic AI.</p>
</div>
""",
    unsafe_allow_html=True,
)


# ================= HELPERS =================

def show_agent_pipeline(intent: str) -> None:
    st.markdown('<div class="section-title">🤖 Agent Execution Pipeline</div>', unsafe_allow_html=True)

    steps = [
        ("Intent Router", True),
        ("Risk Engine", intent in ["ROADMAP", "RISK"]),
        ("Roadmap Agent", intent in ["ROADMAP", "RISK"]),
        ("Career Agent", intent == "CAREER"),
        ("Support/RAG Agent", intent in ["SUPPORT", "RAG"]),
        ("Validator", intent in ["ROADMAP", "RISK"]),
    ]

    cols = st.columns(len(steps))
    for col, (name, active) in zip(cols, steps):
        with col:
            if active:
                st.success(f"✅ {name}")
            else:
                st.info(f"⏭️ {name}")


def show_risk_gauge(score: float) -> None:
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=score,
            title={"text": "Academic Risk Score"},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": "#ef4444" if score >= 70 else "#f59e0b"},
                "steps": [
                    {"range": [0, 40], "color": "#dcfce7"},
                    {"range": [40, 70], "color": "#fef3c7"},
                    {"range": [70, 100], "color": "#fee2e2"},
                ],
            },
        )
    )
    fig.update_layout(height=320, margin=dict(l=20, r=20, t=50, b=20))
    st.plotly_chart(fig, use_container_width=True)


def show_shap_chart(risk_profile: dict) -> None:
    factors = risk_profile.get("top_factors", [])
    if not factors:
        st.warning("No risk factor data available.")
        return

    df = pd.DataFrame(factors)

    fig = px.bar(
        df,
        x="shap_contribution",
        y="feature",
        orientation="h",
        text="shap_contribution",
        color="shap_contribution",
        color_continuous_scale="Reds",
        title="SHAP Contribution of Risk Factors",
    )

    fig.update_layout(
        height=380,
        xaxis_title="Contribution",
        yaxis_title="Risk Factor",
        template="plotly_white",
        coloraxis_showscale=False,
    )

    st.plotly_chart(fig, use_container_width=True)


_FACTOR_ICONS = {
    "attendance_drop": "📉",
    "backlog_count": "📚",
    "fee_delay": "💳",
}


def _risk_factor_icon(feature: str) -> str:
    return _FACTOR_ICONS.get(feature, "📌")


def _risk_factor_explanation(feature: str) -> str:
    explanations = {
        "attendance_drop":
            "Attendance is contributing strongly to academic risk. Improving attendance should be a top priority.",

        "backlog_count":
            "Pending backlogs are increasing academic pressure and need a focused recovery plan.",

        "fee_delay":
            "Fee delay may create administrative or financial stress, so support or clarification may be needed.",
    }

    return explanations.get(
        feature,
        "This factor is contributing to the student's risk profile and should be monitored.",
    )


def _render_factor_cards(risk_profile: dict) -> None:
    factors = risk_profile.get("top_factors", [])
    if not factors:
        st.info("No risk factor data available.")
        return

    max_contrib = max(abs(f.get("shap_contribution", 0) or 0) for f in factors) or 1

    cols = st.columns(2)
    for idx, factor in enumerate(factors):
        feature = factor.get("feature", "Unknown factor")
        value = factor.get("value", "NA")
        contribution = factor.get("shap_contribution", 0) or 0
        bar_pct = min(100, round((abs(contribution) / max_contrib) * 100))
        icon = _risk_factor_icon(feature)
        explanation = _risk_factor_explanation(feature)

        with cols[idx % 2]:
            st.markdown(
                f"""
                <div class="factor-card">
                    <div class="factor-header">
                        <span class="factor-icon">{icon}</span>
                        <span>{feature.replace('_', ' ').title()}</span>
                    </div>
                    <div class="factor-meta">
                        Value: <b>{value}</b> &nbsp;•&nbsp; SHAP Contribution: <b>{contribution}</b>
                    </div>
                    <div class="factor-explanation">{explanation}</div>
                    <div class="impact-bar-track">
                        <div class="impact-bar-fill" style="width:{bar_pct}%;"></div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def _get_week_tasks(details: dict) -> list:
    return (
        details.get("tasks")
        or details.get("actions")
        or details.get("weekly_tasks")
        or details.get("daily_tasks")
        or details.get("recommendations")
        or []
    )


def show_roadmap_ui(roadmap_result: dict) -> None:
    roadmap = roadmap_result["roadmap"]
    risk_profile = roadmap_result["risk_profile"]
    validation = roadmap_result["validation"]

    st.markdown('<div class="section-title">📊 Risk Snapshot</div>', unsafe_allow_html=True)

    risk_score = risk_profile.get("risk_score", "NA")
    risk_band = str(risk_profile.get("risk_band", "NA")).upper()
    priority_level = risk_profile.get("priority_level") or risk_profile.get("risk_band", "NA")
    validation_status = "✅ Passed" if validation.get("is_valid") else "⚠️ Failed"

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-title">Risk Score</div>
                <div class="metric-value">{risk_score}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-title">Risk Band</div>
                <div class="metric-value">{risk_band}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col3:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-title">Priority Level</div>
                <div class="metric-value">{str(priority_level).upper()}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col4:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-title">Validation</div>
                <div class="metric-value">{validation_status}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    show_risk_gauge(risk_profile.get("risk_score", 0))

    st.markdown('<div class="section-title">📌 Risk Summary</div>', unsafe_allow_html=True)
    st.markdown(
        f"""<div class="card">{roadmap.get("risk_summary", "No risk summary available.")}</div>""",
        unsafe_allow_html=True,
    )

    st.markdown('<div class="section-title">🔥 Risk Factor Analysis</div>', unsafe_allow_html=True)
    show_shap_chart(risk_profile)

    st.markdown('<div class="section-title">🔍 Why am I at Risk?</div>', unsafe_allow_html=True)
    _render_factor_cards(risk_profile)

    st.markdown('<div class="section-title">🗓️ Personalized Four-Week Roadmap</div>', unsafe_allow_html=True)

    four_week_plan = roadmap.get("four_week_plan", {})
    if not four_week_plan:
        st.warning("Roadmap plan not available.")
    else:
        total_weeks = len(four_week_plan)
        for idx, (week_key, details) in enumerate(four_week_plan.items()):
            if not isinstance(details, dict):
                details = {}

            with st.expander(
                f"📅 {week_key.replace('_', ' ').title()}",
                expanded=(idx == 0),
            ):
                goal = (
                    details.get("goal")
                    or details.get("weekly_goal")
                    or details.get("objective")
                    or "Improve academic performance"
                )

                risk_factor_tag = (
                    details.get("risk_factor")
                    or details.get("target_factor")
                    or details.get("related_risk_factor")
                )

                tag_html = (
                    f'<span class="risk-tag">🎯 {risk_factor_tag.replace("_", " ").title()}</span>'
                    if risk_factor_tag
                    else ""
                )

                progress_pct = round(((idx + 1) / total_weeks) * 100) if total_weeks else 0
                filled_blocks = round(progress_pct / 25)
                progress_bar_text = "🟦" * filled_blocks + "⬜" * (4 - filled_blocks)

                st.markdown(
                    f"""
                    <div class="goal-card">
                        <h4>🎯 Weekly Goal {tag_html}</h4>
                        <p style="margin:0 0 10px 0; color:#374151;">{goal}</p>
                        <div class="progress-label">Progress</div>
                        <div class="progress-track">
                            <div class="progress-fill" style="width:{progress_pct}%;"></div>
                        </div>
                        <div class="progress-label">{progress_bar_text} {progress_pct}%</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                st.markdown("**📌 Action Plan**")

                tasks = _get_week_tasks(details)

                if not tasks:
                    st.info("No tasks available for this week.")
                else:
                    for task in tasks:
                        if isinstance(task, dict):
                            task_text = task.get("description", "")
                            outcome = task.get("measurable_outcome", "Improvement expected")
                        else:
                            task_text = str(task)
                            outcome = "Improvement expected"

                        st.markdown(
                            f"""
                            <div class="action-flashcard">
                                <div class="action-label">✅ Action</div>
                                <div class="action-text">{task_text}</div>
                                <span class="outcome-badge">📈 {outcome}</span>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

    st.markdown('<div class="section-title">🧩 Support Recommendations</div>', unsafe_allow_html=True)
    support_needed = roadmap.get("support_needed", {})
    if isinstance(support_needed, dict) and support_needed:
        for key, value in support_needed.items():
            st.markdown(
                f"""
                <div class="support-card">
                    <b>{key.replace('_', ' ').title()}</b><br>
                    {value}
                </div>
                """,
                unsafe_allow_html=True,
            )
    elif support_needed:
        st.markdown(f'<div class="support-card">{support_needed}</div>', unsafe_allow_html=True)
    else:
        st.info("No additional support recommendations at this time.")

    st.markdown('<div class="section-title">📉 Risk Reduction Estimate</div>', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="card" style="border-left:6px solid var(--green);">
            {roadmap.get(
                "risk_reduction_estimate",
                "Following this roadmap can reduce academic risk by targeting attendance, backlog, and fee-delay factors.",
            )}
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="section-title">💬 Encouraging Note</div>', unsafe_allow_html=True)
    st.markdown(
        f"""<div class="card">{roadmap.get("encouraging_note", "Keep following the plan consistently.")}</div>""",
        unsafe_allow_html=True,
    )

    st.download_button(
        label="⬇️ Download Roadmap JSON",
        data=json.dumps(roadmap_result, indent=2),
        file_name=f"{student_id}_roadmap.json",
        mime="application/json",
    )

    if st.session_state.get("show_dev_json", False):
        with st.expander("🔍 Developer View: Raw JSON", expanded=False):
            st.json(roadmap_result)


def show_risk_ui(roadmap_result: dict) -> None:
    roadmap = roadmap_result["roadmap"]
    risk_profile = roadmap_result["risk_profile"]

    st.markdown('<div class="section-title">🔎 Risk Explanation</div>', unsafe_allow_html=True)
    show_risk_gauge(risk_profile.get("risk_score", 0))
    st.markdown(
        f"""<div class="card">{roadmap.get("risk_summary", "No summary available.")}</div>""",
        unsafe_allow_html=True,
    )

    st.markdown('<div class="section-title">🔍 Key Risk Factors</div>', unsafe_allow_html=True)
    _render_factor_cards(risk_profile)

    show_shap_chart(risk_profile)

    if st.session_state.get("show_dev_json", False):
        with st.expander("🔍 Developer View: Raw JSON", expanded=False):
            st.json(roadmap_result)


# ---------- Career UI parsing helpers (fallback only, used when Gemini response lacks structure) ----------

_FALLBACK_SKILLS = {
    "AI": ["🐍 Python", "🤖 Machine Learning", "🧠 Deep Learning", "🔗 LLMs"],
    "Web Development": ["🌐 HTML/CSS", "⚛️ React", "🟩 Node.js", "🗄️ Databases"],
    "Cybersecurity": ["🛰️ Networking", "🐧 Linux", "🛡️ Security Tools", "🕵️ Ethical Hacking"],
    "Data Science": ["🐍 Python", "🗃️ SQL", "📊 Statistics", "📈 Visualization"],
}
def classify_intent_local(question: str) -> str:
    q = question.lower()

    if "career" in q or "skill" in q or "job" in q or "ai roadmap" in q:
        return "CAREER"

    if "risk" in q or "score" in q or "why" in q or "factor" in q:
        return "RISK"

    if "support" in q or "help" in q or "recommendation" in q:
        return "SUPPORT"

    if "roadmap" in q or "4 week" in q or "improve" in q or "plan" in q:
        return "ROADMAP"

    return "ROADMAP"

def _extract_section(text: str, headings: list) -> str:
    """Best-effort extraction of a labeled section from a plain-text Gemini response."""
    if not text:
        return ""
    pattern = r"(?:" + "|".join(re.escape(h) for h in headings) + r")\s*[:\-]?\s*\n?"
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if not match:
        return ""
    start = match.end()
    rest = text[start:]
    next_heading = re.search(r"\n\s*(?:[A-Z][A-Za-z /]{2,40}):\s*\n|\n\s*#{1,3}\s", rest)
    end = next_heading.start() if next_heading else len(rest)
    return rest[:end].strip()


def _split_bullets(section_text: str) -> list:
    if not section_text:
        return []
    lines = re.split(r"\n|•", section_text)
    items = []
    for line in lines:
        cleaned = line.strip(" -*\u2022\t")
        cleaned = re.sub(r"^\d+[\.\)]\s*", "", cleaned)
        if cleaned:
            items.append(cleaned)
    return items


def _parse_career_text(text: str) -> dict:
    """Parses a plain-text Gemini career response into structured sections, if possible."""
    parsed = {
        "summary": _extract_section(text, ["Summary", "Why this field", "Overview", "Career Fit"]),
        "skills": _split_bullets(_extract_section(text, ["Skills", "Skills to Master", "Skill Stack"])),
        "timeline": _split_bullets(_extract_section(text, ["Timeline", "Roadmap", "Learning Plan", "Week"])),
        "projects": _split_bullets(_extract_section(text, ["Projects", "Project Recommendations"])),
        "certifications": _split_bullets(_extract_section(text, ["Certifications", "Courses"])),
        "internship_prep": _extract_section(text, ["Internship", "Internship Preparation"]),
    }
    return parsed


def show_career_ui() -> None:
    """Builds the full career guidance dashboard using the live Gemini response."""
    response = generate_career_guidance(gpa, interest)

    response_data = response if isinstance(response, dict) else {}
    response_text = response if isinstance(response, str) else ""

    if response_text:
        parsed = _parse_career_text(response_text)
    else:
        parsed = {}

    # ---- Top profile row ----
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(
            f"""
            <div class="ai-card">
                <div class="metric-title">🎯 Career Interest</div>
                <div class="metric-value">{interest}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            f"""
            <div class="ai-card">
                <div class="metric-title">🎓 Current GPA</div>
                <div class="metric-value">{gpa}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ---- Career summary card ----
    summary_text = (
        response_data.get("summary")
        or response_data.get("why_this_field")
        or response_data.get("overview")
        or parsed.get("summary")
    )
    if not summary_text:
        summary_text = (
            f"Based on your GPA of {gpa} and interest in {interest}, here is a tailored "
            "guidance plan to help you build the right skills and move toward your career goal."
        )

    st.markdown('<div class="section-title">💡 Career Summary</div>', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="career-card">
            <p style="margin:0; color:#374151;">{summary_text}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ---- Skill flashcards ----
    skills_list = (
        response_data.get("skills")
        or response_data.get("skill_stack")
        or parsed.get("skills")
    )
    if not skills_list:
        skills_list = _FALLBACK_SKILLS.get(interest, ["💡 Problem Solving", "🧩 Projects", "🗣️ Communication"])

    st.markdown('<div class="section-title">🛠 Skills To Master</div>', unsafe_allow_html=True)
    skills_html = "".join(f'<span class="skill-badge">⚡ {skill}</span>' for skill in skills_list)
    st.markdown(skills_html, unsafe_allow_html=True)

    # ---- Learning roadmap cards ----
    timeline = (
        response_data.get("timeline")
        or response_data.get("weekly_plan")
        or response_data.get("eight_week_plan")
    )

    st.markdown('<div class="section-title">🗓️ Learning Roadmap</div>', unsafe_allow_html=True)

    if isinstance(timeline, dict) and timeline:
        total_slots = len(timeline)
        for idx, (period, task) in enumerate(timeline.items()):
            progress_pct = round(((idx + 1) / total_slots) * 100)
            filled_blocks = round(progress_pct / 25)
            progress_bar_text = "🟦" * filled_blocks + "⬜" * (4 - filled_blocks)
            st.markdown(
                f"""
                <div class="timeline-card">
                    <h4>{period}</h4>
                    <div>🎯 {task}</div>
                    <div class="progress-label" style="margin-top:8px;">Progress</div>
                    <div class="progress-track">
                        <div class="progress-fill" style="width:{progress_pct}%;"></div>
                    </div>
                    <div class="progress-label">{progress_bar_text} {progress_pct}%</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    elif isinstance(timeline, list) and timeline:
        for idx, item in enumerate(timeline):
            st.markdown(
                f"""<div class="timeline-card"><h4>Step {idx + 1}</h4><div>🎯 {item}</div></div>""",
                unsafe_allow_html=True,
            )
    elif parsed.get("timeline"):
        for idx, item in enumerate(parsed["timeline"]):
            st.markdown(
                f"""<div class="timeline-card"><h4>Step {idx + 1}</h4><div>🎯 {item}</div></div>""",
                unsafe_allow_html=True,
            )
    else:
        st.info("No detailed roadmap steps were returned for this guidance request.")

    # ---- Project recommendation cards ----
    projects = (
        response_data.get("projects")
        or response_data.get("recommended_projects")
        or parsed.get("projects")
    )

    st.markdown('<div class="section-title">🚀 Recommended Projects</div>', unsafe_allow_html=True)
    if projects:
        proj_cols = st.columns(min(len(projects), 3) or 1)
        for idx, project in enumerate(projects):
            with proj_cols[idx % len(proj_cols)]:
                st.markdown(
                    f"""
                    <div class="ai-card" style="text-align:center;">
                        <div style="font-size:22px;">📁</div>
                        <div style="font-weight:700; margin-top:6px;">{project}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
    else:
        st.info("No specific project recommendations were returned.")

    # ---- Certification / course cards ----
    certifications = (
        response_data.get("certifications")
        or response_data.get("courses")
        or parsed.get("certifications")
    )

    if certifications:
        st.markdown('<div class="section-title">📜 Certifications & Courses</div>', unsafe_allow_html=True)
        for cert in certifications:
            cert_name = cert.get("name", cert) if isinstance(cert, dict) else cert
            cert_provider = cert.get("provider", "") if isinstance(cert, dict) else ""
            st.markdown(
                f"""
                <div class="ai-card">
                    <b>📜 {cert_name}</b>
                    {f"<br><small>{cert_provider}</small>" if cert_provider else ""}
                </div>
                """,
                unsafe_allow_html=True,
            )

    # ---- Internship preparation card ----
    internship_prep = (
        response_data.get("internship_prep")
        or response_data.get("internship_preparation")
        or parsed.get("internship_prep")
    )

    if internship_prep:
        st.markdown('<div class="section-title">💼 Internship Preparation</div>', unsafe_allow_html=True)
        st.markdown(f"""<div class="career-card">{internship_prep}</div>""", unsafe_allow_html=True)

    # ---- Fallback: show any remaining plain-text response cleanly (never raw/unformatted) ----
    if response_text and not any(parsed.values()):
        st.markdown('<div class="section-title">🧠 AI Career Insights</div>', unsafe_allow_html=True)
        st.markdown(f"""<div class="career-card">{response_text}</div>""", unsafe_allow_html=True)

    if st.session_state.get("show_dev_json", False):
        with st.expander("🔍 Developer View: Raw Response", expanded=False):
            st.write(response)


def show_support_ui() -> None:
    st.markdown('<div class="section-title">🧑‍🏫 Support Guidance</div>', unsafe_allow_html=True)
    st.markdown(
        """
        <div class="support-card">
            <b>Recommended Support Channels</b><br><br>
            ✅ Academic mentor meeting<br>
            ✅ Peer study group<br>
            ✅ Financial aid / fee support office<br>
            ✅ Counselling support if stress is high<br>
            ✅ Library and learning resources
        </div>
        """,
        unsafe_allow_html=True,
    )


def show_rag_ui() -> None:
    st.markdown('<div class="section-title">📚 College Knowledge Base</div>', unsafe_allow_html=True)
    st.markdown(
        """
        <div class="card">
            This module will answer policy and FAQ questions using ChromaDB/RAG.
            Currently this is marked as the upcoming Week 4 integration.
        </div>
        """,
        unsafe_allow_html=True,
    )

def fallback_roadmap(student_id):
    return {
        "student_id": student_id,
        "risk_profile": {
            "risk_score": 78,
            "risk_band": "High",
            "top_factors": [
                {"feature": "attendance_drop", "value": -18, "shap_contribution": 0.31},
                {"feature": "backlog_count", "value": 2, "shap_contribution": 0.24},
                {"feature": "fee_delay", "value": 45, "shap_contribution": 0.19},
            ],
        },
        "roadmap": {
            "risk_summary": f"Student {student_id} is at academic risk due to attendance drop, backlogs, and fee delay.",
            "four_week_plan": {
                "week_1": {
                    "goal": "Stabilize attendance and identify weak subjects.",
                    "tasks": [
                        {"description": "Attend all lectures this week.", "measurable_outcome": "Attendance consistency improves."},
                        {"description": "List backlog subjects and collect notes.", "measurable_outcome": "Backlog recovery starts."},
                    ],
                },
                "week_2": {
                    "goal": "Start backlog recovery.",
                    "tasks": [
                        {"description": "Study backlog subjects for 2 hours daily.", "measurable_outcome": "Regular preparation begins."}
                    ],
                },
                "week_3": {
                    "goal": "Take academic support.",
                    "tasks": [
                        {"description": "Meet mentor or faculty for guidance.", "measurable_outcome": "Targeted support received."}
                    ],
                },
                "week_4": {
                    "goal": "Track improvement and plan next month.",
                    "tasks": [
                        {"description": "Review attendance and backlog progress.", "measurable_outcome": "Risk reduction is tracked."}
                    ],
                },
            },
            "support_needed": {
                "Academic Advisor": "For study planning and mentoring.",
                "Financial Aid": "For fee delay support.",
            },
            "risk_reduction_estimate": "Following this plan can reduce academic risk by improving attendance and backlog progress.",
            "encouraging_note": "Small consistent actions can improve your academic standing.",
        },
        "validation": {"is_valid": True},
    }
# ================= MAIN PAGE FLOW =================
# Only this section runs on every page load: header (already rendered above),
# sidebar (already rendered above), and the chat input below.
# NOTHING else executes until "Ask Agent" is clicked.

st.markdown('<div class="section-title">💬 Ask the Student Success Agent</div>', unsafe_allow_html=True)

user_question = st.text_input(
    "Your question",
    placeholder="Example: Why is my risk score high? How should I improve my GPA?",
)

if st.button("🚀 Ask Agent", use_container_width=True):
    if user_question.strip() == "":
        st.warning("Please enter a question.")
    else:
        with st.spinner("Routing your question to the right AI agent..."):
            intent = classify_intent_local(user_question)

        st.success(f"Detected Intent: {intent}")
        show_agent_pipeline(intent)

        if intent == "CAREER":
            with st.spinner("Generating career guidance..."):
                show_career_ui()

        elif intent == "ROADMAP":
            with st.spinner("Generating personalized roadmap..."):
                try:
                    roadmap_result = cached_roadmap(student_id)

                except Exception:
                    roadmap_result = fallback_roadmap(student_id)

                show_roadmap_ui(roadmap_result)
                show_faculty_intervention(student_id)

        elif intent == "RISK":
            with st.spinner("Analyzing risk factors..."):
                try:
                    roadmap_result = fallback_roadmap(student_id)
                except Exception:
                    st.error("Fallback roadmap is not defined properly.")
                    st.stop()

                show_risk_ui(roadmap_result)

        elif intent == "SUPPORT":
            show_support_ui()
            show_faculty_intervention(student_id)

        elif intent == "RAG":
            show_rag_ui()

        else:
            st.warning("I couldn't understand your question clearly.")