import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from agents.intent_router import classify_intent
from modules.roadmap_generator import generate_improvement_roadmap
from modules.career_module import generate_career_guidance


st.set_page_config(
    page_title="Student Success AI",
    page_icon="🎓",
    layout="wide"
)

# ---------------- CSS ----------------
st.markdown("""
<style>
.main {
    background-color: #f8fafc;
}
.big-title {
    font-size: 42px;
    font-weight: 800;
    color: #111827;
}
.subtitle {
    font-size: 18px;
    color: #6b7280;
    margin-bottom: 25px;
}
.card {
    background: white;
    padding: 22px;
    border-radius: 16px;
    border: 1px solid #e5e7eb;
    box-shadow: 0 4px 14px rgba(0,0,0,0.04);
    margin-bottom: 18px;
}
.metric-title {
    font-size: 14px;
    color: #6b7280;
}
.metric-value {
    font-size: 32px;
    font-weight: 800;
    color: #111827;
}
.agent-box {
    padding: 12px;
    border-radius: 12px;
    background-color: #eef2ff;
    border-left: 5px solid #4f46e5;
    margin-bottom: 10px;
}
</style>
""", unsafe_allow_html=True)


# ---------------- SIDEBAR ----------------
with st.sidebar:
    st.title("🎓 Student Profile")

    student_id = st.text_input("Student ID", value="S1001")
    gpa = st.number_input("Current GPA", min_value=0.0, max_value=10.0, value=7.4)
    interest = st.selectbox(
        "Career Interest",
        ["AI", "Web Development", "Cybersecurity", "Data Science", "Other"]
    )

    st.divider()
    st.caption("Student Academic Success & Retention Platform")


# ---------------- HEADER ----------------
st.markdown('<div class="big-title">Student Success & Career Roadmap AI</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="subtitle">Agentic AI assistant for academic risk explanation, personalized roadmap, and career readiness.</div>',
    unsafe_allow_html=True
)


# ---------------- HELPERS ----------------
def show_agent_pipeline(intent):
    st.subheader("🤖 Agent Execution Pipeline")

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


def show_risk_gauge(score):
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
    fig.update_layout(height=320)
    st.plotly_chart(fig, use_container_width=True)


def show_shap_chart(risk_profile):
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
        title="SHAP Contribution of Risk Factors"
    )

    fig.update_layout(
        height=380,
        xaxis_title="Contribution",
        yaxis_title="Risk Factor",
        template="plotly_white",
        coloraxis_showscale=False
    )

    st.plotly_chart(fig, use_container_width=True)


def show_roadmap_ui(roadmap_result):
    roadmap = roadmap_result["roadmap"]
    risk_profile = roadmap_result["risk_profile"]
    validation = roadmap_result["validation"]

    st.subheader("📊 Risk Snapshot")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(
            f"""
            <div class="card">
                <div class="metric-title">Risk Score</div>
                <div class="metric-value">{risk_profile["risk_score"]}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col2:
        st.markdown(
            f"""
            <div class="card">
                <div class="metric-title">Risk Band</div>
                <div class="metric-value">{risk_profile["risk_band"].upper()}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col3:
        status = "Passed" if validation["is_valid"] else "Failed"
        st.markdown(
            f"""
            <div class="card">
                <div class="metric-title">Validation</div>
                <div class="metric-value">{status}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    show_risk_gauge(risk_profile["risk_score"])

    st.subheader("📌 Risk Summary")
    st.info(roadmap.get("risk_summary", "No risk summary available."))

    st.subheader("🔥 Risk Factor Analysis")
    show_shap_chart(risk_profile)

    st.subheader("🚨 Top Risk Factors")
    for factor in risk_profile["top_factors"]:
        st.markdown(
            f"""
            <div class="agent-box">
                <b>{factor["feature"]}</b><br>
                Value: <code>{factor["value"]}</code><br>
                SHAP Contribution: <code>{factor["shap_contribution"]}</code>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.subheader("🗓️ Personalized Four-Week Roadmap")

    for week, details in roadmap["four_week_plan"].items():
        with st.expander(f"📅 {week.replace('_', ' ').title()}", expanded=(week == "week_1")):
            goal = (
            details.get("goal")
            or details.get("weekly_goal")
            or details.get("objective")
            or details.get("focus")
            or "Focus on the recommended improvement actions for this week."
        )

        st.markdown(f"### Goal: {goal}")

        for task in details.get("tasks", []):
            if isinstance(task, dict):
                st.markdown(f"- **Task:** {task.get('description', '')}")
                st.caption(
                    f"Measurable Outcome: {task.get('measurable_outcome', 'Not provided')}"
                )
            else:
                st.markdown(f"- {task}")

    st.subheader("🧩 Support Recommendations")
    st.json(roadmap.get("support_needed", {}))

    st.subheader("📉 Risk Reduction Estimate")
    st.success(
    roadmap.get(
        "risk_reduction_estimate",
        "Following this roadmap can reduce academic risk by targeting attendance, backlog, and fee-delay factors."
    )
)
    st.subheader("💬 Encouraging Note")
    st.write(roadmap.get("encouraging_note", ""))

    st.download_button(
        label="⬇️ Download Roadmap JSON",
        data=json.dumps(roadmap_result, indent=2),
        file_name=f"{student_id}_roadmap.json",
        mime="application/json"
    )

    with st.expander("🔍 Developer View: Raw JSON"):
        st.json(roadmap_result)


def show_risk_ui(roadmap_result):
    roadmap = roadmap_result["roadmap"]
    risk_profile = roadmap_result["risk_profile"]

    st.subheader("🔎 Risk Explanation")
    show_risk_gauge(risk_profile["risk_score"])
    st.info(roadmap.get("risk_summary", "No summary available."))
    show_shap_chart(risk_profile)


def show_career_ui():
    response = generate_career_guidance(gpa, interest)

    st.subheader("💼 Career Readiness Guidance")
    st.success(response)


def show_support_ui():
    st.subheader("🧑‍🏫 Support Guidance")

    st.markdown("""
    <div class="card">
    <b>Recommended Support Channels</b><br><br>
    ✅ Academic mentor meeting<br>
    ✅ Peer study group<br>
    ✅ Financial aid / fee support office<br>
    ✅ Counselling support if stress is high<br>
    ✅ Library and learning resources
    </div>
    """, unsafe_allow_html=True)


def show_rag_ui():
    st.subheader("📚 College Knowledge Base")

    st.info(
        "This module will answer policy and FAQ questions using ChromaDB/RAG. "
        "Currently this is marked as the upcoming Week 4 integration."
    )


# ---------------- MAIN CHAT ----------------
st.subheader("💬 Ask the Student Success Agent")

user_question = st.text_input(
    "Your question",
    placeholder="Example: Why is my risk score high? How should I improve my GPA?"
)

if st.button("🚀 Ask Agent", use_container_width=True):

    if user_question.strip() == "":
        st.warning("Please enter a question.")

    else:
        with st.spinner("Routing your question to the right AI agent..."):
            intent = classify_intent(user_question)

        st.success(f"Detected Intent: {intent}")
        show_agent_pipeline(intent)

        if intent == "CAREER":
            with st.spinner("Generating career guidance..."):
                show_career_ui()

        elif intent == "ROADMAP":
            with st.spinner("Generating personalized roadmap..."):
                roadmap_result = generate_improvement_roadmap(student_id)
                show_roadmap_ui(roadmap_result)

        elif intent == "RISK":
            with st.spinner("Analyzing risk factors..."):
                roadmap_result = generate_improvement_roadmap(student_id)
                show_risk_ui(roadmap_result)

        elif intent == "SUPPORT":
            show_support_ui()

        elif intent == "RAG":
            show_rag_ui()

        else:
            st.warning("I couldn't understand your question clearly.")