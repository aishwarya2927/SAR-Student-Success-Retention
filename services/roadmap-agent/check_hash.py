"""
chat_app.py — Student Success & Retention Platform
Person D — Student Roadmap Agent & Student Dashboard

Organization:
  1. Standard-library imports
  2. Third-party imports
  3. Local imports
  4. Constants and URLs
  5. Page config
  6. Generic utility helpers
  7. Dataset functions
  8. Risk-engine integration
  9. Placement and faculty API integration
 10. Response normalization helpers
 11. CSS
 12. Login flow
 13. Sidebar
 14. Risk UI functions
 15. Roadmap UI functions
 16. Career UI functions
 17. Placement UI functions
 18. Main page flow
"""

# ============================================================
# 1. STANDARD-LIBRARY IMPORTS
# ============================================================
import os
import re
import json
import datetime
import sys
from pathlib import Path
from typing import Optional, Any

# ============================================================
# 2. THIRD-PARTY IMPORTS
# ============================================================
import requests
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR / "utils"))

# ============================================================
# 3. LOCAL IMPORTS
# ============================================================
from agents.intent_router import classify_intent
from modules.career_module import generate_career_guidance

# ============================================================
# 4. CONSTANTS AND URLS
# ============================================================
RISK_ENGINE_URL = os.getenv("RISK_ENGINE_URL", "http://127.0.0.1:8000")
MENTOR_AGENT_URL = os.getenv(
    "MENTOR_AGENT_URL", "https://sar-mentor-agent.onrender.com"
)
FACULTY_API_BASE = os.getenv(
    "FACULTY_API_BASE", "https://sar-student-success-retention-3kvj.onrender.com"
)
ROADMAP_AGENT_BASE = os.getenv(
    "ROADMAP_AGENT_BASE", "https://sar-roadmap-agent.onrender.com"
)
STUDENT_DATASET_PATH = os.getenv(
    "STUDENT_DATASET_PATH",
    str(BASE_DIR.parent.parent / "datasets" / "student_success_dataset_30000.csv"),
)

TARGET_COMPANY_OPTIONS = [
    "Google", "Microsoft", "Amazon", "Meta", "Apple",
    "Adobe", "Salesforce", "Oracle", "IBM",
    "PhonePe", "Paytm", "Razorpay", "Flipkart", "Meesho",
    "Zomato", "Swiggy", "CRED", "Zepto",
    "TCS", "Infosys", "Wipro", "Accenture", "Capgemini",
    "Deloitte", "Cognizant", "LTIMindtree", "Tech Mahindra",
    "JPMorgan Chase", "Morgan Stanley", "Goldman Sachs",
    "Barclays", "Deutsche Bank", "HSBC",
    "NVIDIA", "Intel", "Qualcomm", "Cisco", "Samsung",
    "ISRO", "DRDO", "NIC", "RBI",
]

# ============================================================
# 5. PAGE CONFIG (called exactly once, before any other st.* call)
# ============================================================
st.set_page_config(
    page_title="Student Success AI",
    page_icon="🎓",
    layout="wide",
)


# ============================================================
# 6. GENERIC UTILITY HELPERS
# ============================================================
def clean_html_text(value: Any) -> str:
    """
    Single canonical HTML/text cleaner. Converts any HTML fragment or
    plain-text block into safe, readable plain text.
    """
    if value is None:
        return ""

    text = str(value)

    # decode a few common HTML entities
    text = (
        text.replace("&nbsp;", " ")
        .replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&#39;", "'")
        .replace("&quot;", '"')
    )

    # line breaks
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(
        r"</(?:p|h1|h2|h3|h4|h5|div|li|ul|ol)>",
        "\n",
        text,
        flags=re.IGNORECASE,
    )

    # strip all remaining tags (including orphan closing tags like </p>)
    text = re.sub(r"<[^>]+>", "", text)

    # collapse blank lines / excess whitespace
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)

    return text.strip()


def _is_meaningful_text(text: str) -> bool:
    if not text:
        return False
    stripped = text.strip()
    if not stripped:
        return False
    tag_only = re.sub(r"</?[a-zA-Z0-9]+>", "", stripped).strip()
    return bool(tag_only)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        if isinstance(value, float) and pd.isna(value):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_json_safe(value: Any) -> Any:
    """Converts a single value (possibly numpy/pandas typed) into a JSON-safe Python type."""
    if value is None:
        return None
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return None if np.isnan(value) else float(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, float) and pd.isna(value):
        return None
    if isinstance(value, (pd.Timestamp, datetime.datetime, datetime.date)):
        return value.isoformat()
    return value


def make_json_safe_student_payload(student_data: dict) -> dict:
    """Converts a raw CSV-row dict into a JSON-safe payload for the Risk Engine."""
    if not student_data:
        return {}
    return {key: _to_json_safe(value) for key, value in student_data.items()}


# ============================================================
# 7. DATASET FUNCTIONS
# ============================================================
@st.cache_data(ttl=600, show_spinner=False)
def load_student_dataset() -> pd.DataFrame:
    return pd.read_csv(STUDENT_DATASET_PATH)


@st.cache_data(ttl=300, show_spinner=False)
def get_student_data(student_id: str) -> Optional[dict]:
    df = load_student_dataset()
    student_row = df[df["student_id"] == student_id]
    if student_row.empty:
        return None
    return student_row.iloc[0].to_dict()


@st.cache_data(ttl=300, show_spinner=False)
def find_canonical_student_id(login_username: str) -> Optional[str]:
    """
    Resolves a login username (as returned by streamlit-authenticator, which
    normalizes usernames to lowercase internally) back to the exact-case
    Student ID used everywhere else in the app (CSV, Risk Engine, Mentor
    Agent, Faculty API). Matching is case-insensitive and whitespace-trimmed
    on both sides; the CSV's own casing is always what gets returned, so
    every downstream system keeps receiving the Student ID in the form it
    actually expects (e.g. "STU202600001"), never the lowercased login
    username.
    """
    if not login_username:
        return None

    normalized_login = str(login_username).strip().lower()

    df = load_student_dataset()
    normalized_column = df["student_id"].astype(str).str.strip().str.lower()
    matches = df[normalized_column == normalized_login]

    if matches.empty:
        return None

    return str(matches.iloc[0]["student_id"])


# ============================================================
# 8. RISK-ENGINE INTEGRATION
# ============================================================
@st.cache_data(ttl=300, show_spinner=False)
def get_risk_prediction(student_id: str) -> Optional[dict]:
    """Calls the trained Risk Engine for this student. Returns None on any failure."""
    student_data = get_student_data(student_id)
    if not student_data:
        return None

    payload = make_json_safe_student_payload(student_data)
    url = f"{RISK_ENGINE_URL}/predict"

    try:
        response = requests.post(url, json=payload, timeout=10)
    except requests.exceptions.ConnectTimeout:
        return None
    except requests.exceptions.ReadTimeout:
        return None
    except requests.exceptions.ConnectionError:
        return None
    except requests.exceptions.RequestException:
        return None

    if response.status_code != 200:
        return None

    try:
        return response.json()
    except ValueError:
        return None


def normalize_risk_prediction(response: Optional[dict], student_data: Optional[dict]) -> Optional[dict]:
    """
    Normalizes any Risk Engine response shape into:
    {
        "risk_score": float,
        "risk_band": str,
        "confidence": float | None,
        "top_factors": [{"feature": str, "value": Any, "shap_contribution": float}],
        "source": "ml"
    }
    """
    if not response:
        return None

    raw_factors = (
        response.get("top_factors")
        or response.get("shap_values")
        or response.get("feature_contributions")
        or response.get("explanations")
    )

    factors = []

    if isinstance(raw_factors, dict):
        for feature, contribution in raw_factors.items():
            try:
                contribution_val = float(contribution)
            except (TypeError, ValueError):
                continue
            value = student_data.get(feature, "N/A") if student_data else "N/A"
            factors.append(
                {"feature": feature, "value": value, "shap_contribution": contribution_val}
            )

    elif isinstance(raw_factors, list):
        for item in raw_factors:
            if not isinstance(item, dict):
                continue
            feature = item.get("feature") or item.get("name")
            if not feature:
                continue
            contribution = item.get(
                "shap_contribution", item.get("shap_value", item.get("contribution"))
            )
            try:
                contribution_val = float(contribution)
            except (TypeError, ValueError):
                continue
            value = item.get("value")
            if value is None and student_data:
                value = student_data.get(feature, "N/A")
            factors.append(
                {
                    "feature": feature,
                    "value": value if value is not None else "N/A",
                    "shap_contribution": contribution_val,
                }
            )

    factors.sort(key=lambda f: abs(f["shap_contribution"]), reverse=True)
    factors = factors[:5]

    return {
        "risk_score": _safe_float(response.get("risk_score"), 0.0),
        "risk_band": str(response.get("risk_band") or "N/A"),
        "confidence": (
            float(response["confidence"]) if response.get("confidence") is not None else None
        ),
        "top_factors": factors,
        "source": "ml",
    }


def _build_default_four_week_plan(student_data: dict, risk_profile: dict) -> dict:
    """Generates a generic-but-relevant four-week structure. Task content is templated;
    the risk score/band driving it comes from the real (ML or fallback) risk_profile."""
    band = risk_profile.get("risk_band", "N/A")
    return {
        "week_1": {
            "goal": "Identify weak areas and stabilize attendance.",
            "tasks": [
                {
                    "description": "Review attendance and recent academic performance.",
                    "measurable_outcome": "Risk areas identified.",
                },
                {
                    "description": "Create a subject-wise study/recovery list.",
                    "measurable_outcome": "Clear recovery plan started.",
                },
            ],
        },
        "week_2": {
            "goal": "Improve academic consistency.",
            "tasks": [
                {
                    "description": "Study weak subjects for at least 2 hours daily.",
                    "measurable_outcome": "Academic consistency improves.",
                }
            ],
        },
        "week_3": {
            "goal": "Take mentor/faculty support.",
            "tasks": [
                {
                    "description": "Meet a mentor or faculty member for targeted guidance.",
                    "measurable_outcome": "Support received.",
                }
            ],
        },
        "week_4": {
            "goal": f"Track progress and reassess ({band} risk).",
            "tasks": [
                {
                    "description": "Review attendance, marks, and pending backlog work.",
                    "measurable_outcome": "Progress tracked.",
                }
            ],
        },
    }


def build_roadmap_from_prediction(student_id: str) -> Optional[dict]:
    """
    Single canonical builder.
    1. get_student_data
    2. get_risk_prediction
    3. normalize_risk_prediction
    4. dataset fallback if ML unavailable (no invented SHAP values)
    5. build roadmap
    6. include source field
    """
    student_data = get_student_data(student_id)
    if not student_data:
        return None

    raw_prediction = get_risk_prediction(student_id)
    risk_profile = normalize_risk_prediction(raw_prediction, student_data)

    if not risk_profile:
        risk_profile = {
            "risk_score": _safe_float(student_data.get("academic_risk_score"), 0.0),
            "risk_band": str(student_data.get("academic_risk_band", "N/A")),
            "confidence": None,
            "top_factors": [],
            "source": "dataset_fallback",
        }

    roadmap = {
        "risk_summary": (
            f"Student {student_id} currently shows {risk_profile['risk_band']} academic risk "
            f"with a risk score of {risk_profile['risk_score']}."
        ),
        "four_week_plan": _build_default_four_week_plan(student_data, risk_profile),
        "support_needed": {
            "Academic Mentor": "Guidance for weak subjects and structured risk reduction.",
        },
        "risk_reduction_estimate": (
            "Following this roadmap consistently can help reduce academic risk over the next month."
        ),
        "encouraging_note": "Small, consistent weekly effort leads to meaningful academic improvement.",
    }

    return {
        "student_id": student_id,
        "risk_profile": risk_profile,
        "roadmap": roadmap,
        "validation": {
            "is_valid": True,
            "risk_source": risk_profile["source"],
        },
    }


# ============================================================
# 9. PLACEMENT AND FACULTY API INTEGRATION
# ============================================================
def get_faculty_intervention(student_id: str) -> Optional[dict]:
    url = f"{FACULTY_API_BASE}/intervention/{student_id}"
    try:
        response = requests.get(url, timeout=15)
    except requests.exceptions.ConnectTimeout:
        return None
    except requests.exceptions.ReadTimeout:
        return None
    except requests.exceptions.ConnectionError:
        return None
    except requests.exceptions.RequestException:
        return None

    if response.status_code != 200:
        return None
    try:
        return response.json()
    except ValueError:
        return None


def get_placement_data(student_id: str) -> Optional[dict]:
    url = f"{FACULTY_API_BASE}/placement/{student_id}"
    try:
        response = requests.get(url, timeout=30)
    except requests.exceptions.ConnectTimeout:
        return None
    except requests.exceptions.ReadTimeout:
        return None
    except requests.exceptions.ConnectionError:
        return None
    except requests.exceptions.RequestException:
        return None

    if response.status_code != 200:
        return None
    try:
        return response.json()
    except ValueError:
        return None


def save_target_companies(student_id: str, companies: list) -> Optional[dict]:
    url = f"{ROADMAP_AGENT_BASE}/student-target-companies"
    payload = {"student_id": student_id, "target_companies": companies}
    try:
        response = requests.post(url, json=payload, timeout=120)
    except requests.exceptions.ConnectTimeout:
        st.error("Timed out connecting to the roadmap agent service.")
        return None
    except requests.exceptions.ReadTimeout:
        st.error("Timed out saving target companies.")
        return None
    except requests.exceptions.ConnectionError:
        st.error("Could not connect to the roadmap agent service.")
        return None
    except requests.exceptions.RequestException as error:
        st.error(f"Could not save target companies: {error}")
        return None

    if response.status_code != 200:
        st.error(f"Saving target companies failed (status {response.status_code}).")
        return None
    try:
        return response.json()
    except ValueError:
        st.error("Target companies were saved but the response was invalid.")
        return None


def generate_placement_plan(student_id: str) -> Optional[dict]:
    url = f"{MENTOR_AGENT_URL}/generate-placement-plan"
    payload = {"student_id": student_id}

    for attempt in range(2):
        try:
            response = requests.post(url, json=payload, timeout=(15, 180))
        except requests.exceptions.ReadTimeout:
            if attempt == 0:
                st.info("Mentor Agent is waking up. Retrying once...")
                continue
            st.error("Mentor Agent is currently unavailable (timed out).")
            return None
        except requests.exceptions.ConnectTimeout:
            st.error("Could not connect to Mentor Agent (connection timeout).")
            return None
        except requests.exceptions.ConnectionError:
            st.error("Could not connect to Mentor Agent.")
            return None
        except requests.exceptions.RequestException as error:
            st.error(f"Mentor Agent request failed: {error}")
            return None

        if response.status_code == 200:
            try:
                return response.json()
            except ValueError:
                st.error("Mentor Agent returned an invalid response.")
                return None

        st.error(f"Mentor Agent returned status {response.status_code}.")
        return None

    return None


# ============================================================
# 10. RESPONSE NORMALIZATION HELPERS
# ============================================================
def extract_placement_plan(response: dict) -> dict:
    """
    Handles:
      response["placement_plan"]["placement_plan"]
      response["placement_plan"]
      response directly
    """
    if not isinstance(response, dict):
        raise ValueError("Invalid placement plan response.")

    outer = response.get("placement_plan")
    if isinstance(outer, dict):
        inner = outer.get("placement_plan")
        if isinstance(inner, dict):
            return inner
        return outer

    return response


def get_company_guidance(plan: dict) -> str:
    candidates = [
        plan.get("company_selection_guidance"),
        plan.get("company_guidance"),
        plan.get("company_comparison"),
    ]
    for candidate in candidates:
        cleaned = clean_html_text(candidate)
        if _is_meaningful_text(cleaned):
            return cleaned
    return ""


def _parse_step_text_block(text: str) -> list:
    clean_text = clean_html_text(text)
    if not clean_text:
        return []

    parts = re.split(r"(?:🚀\s*)?Step\s*\d+\s*:?", clean_text, flags=re.IGNORECASE)
    parts = [p.strip() for p in parts if p.strip()]
    if not parts:
        parts = [clean_text]

    results = []
    for part in parts:
        lines = [line.strip() for line in part.split("\n") if line.strip()]
        if not lines:
            continue

        title = lines[0]
        body = "\n".join(lines[1:]) if len(lines) > 1 else ""

        priority_match = re.search(r"🔥\s*([A-Za-z\-]+)", body) or re.search(
            r"\b(PRIMARY|SECONDARY|OPTIONAL|HIGH|MEDIUM|LOW)\b", body, flags=re.IGNORECASE
        )
        duration_match = re.search(r"⏳\s*([^\n]+)", body) or re.search(
            r"(\d+\s*[-to]+\s*\d+\s*weeks?)", body, flags=re.IGNORECASE
        )

        priority = priority_match.group(1).strip() if priority_match else "Focus"
        duration = duration_match.group(1).strip() if duration_match else "As planned"

        detail = re.sub(r"🔥\s*[A-Za-z\-]+", "", body)
        detail = re.sub(r"⏳\s*[^\n]+", "", detail).strip()

        results.append(
            {
                "title": title,
                "priority": priority,
                "duration": duration,
                "detail": detail if detail else body,
            }
        )

    return results


def normalize_preparation_steps(raw_steps: Any) -> list:
    """
    Always returns: [{"title": str, "priority": str, "duration": str, "detail": str}]
    Supports: list[dict] (multiple key formats), list[str], HTML block, plain-text block.
    """
    if not raw_steps:
        return []

    if isinstance(raw_steps, list):
        normalized = []
        for idx, step in enumerate(raw_steps, start=1):
            if isinstance(step, dict):
                title = clean_html_text(step.get("title")) or f"Preparation Step {idx}"
                priority = clean_html_text(step.get("priority")) or "Focus"
                duration = clean_html_text(step.get("duration")) or "As planned"
                detail = clean_html_text(
                    step.get("detail") or step.get("description") or step.get("action") or ""
                )
                normalized.append(
                    {"title": title, "priority": priority, "duration": duration, "detail": detail}
                )
            else:
                cleaned = clean_html_text(step)
                if cleaned:
                    normalized.append(
                        {
                            "title": f"Preparation Step {idx}",
                            "priority": "Focus",
                            "duration": "As planned",
                            "detail": cleaned,
                        }
                    )
        return normalized

    if isinstance(raw_steps, str):
        return _parse_step_text_block(raw_steps)

    return []


def normalize_risk_actions(raw: Any) -> list:
    if not raw:
        return []

    if isinstance(raw, str):
        cleaned = clean_html_text(raw)
        return [{"risk": "Risk Factor", "action": cleaned}] if cleaned else []

    if isinstance(raw, list):
        results = []
        for item in raw:
            if isinstance(item, dict):
                risk = clean_html_text(item.get("risk") or item.get("factor")) or "Risk Factor"
                action = clean_html_text(item.get("action") or item.get("recommendation") or "")
                if risk or action:
                    results.append({"risk": risk, "action": action})
            else:
                cleaned = clean_html_text(str(item))
                if cleaned:
                    results.append({"risk": "Risk Factor", "action": cleaned})
        return results

    return []


# ============================================================
# 11. CSS
# ============================================================
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
.stApp { background: var(--bg-soft); }

.gradient-header {
    background: linear-gradient(135deg, var(--purple) 0%, var(--blue) 55%, var(--green) 120%);
    padding: 34px 38px;
    border-radius: 22px;
    color: white;
    margin-bottom: 26px;
    box-shadow: 0 12px 30px rgba(76, 63, 228, 0.25);
}
.gradient-header h1 { margin: 0 0 6px 0; font-size: 34px; font-weight: 800; }
.gradient-header p { margin: 0; font-size: 15px; opacity: 0.92; }

.card, .ai-card, .metric-card, .career-card, .risk-card, .week-card,
.support-card, .factor-card, .timeline-card, .agent-box, .placement-card, .step-card {
    background: white;
    border-radius: 18px;
    padding: 20px 22px;
    margin-bottom: 16px;
    box-shadow: 0 6px 20px rgba(17, 24, 39, 0.06);
}

.metric-card { text-align: center; border-top: 5px solid var(--purple); }
.metric-title {
    font-size: 13px; font-weight: 700; letter-spacing: 0.4px;
    color: var(--text-soft); text-transform: uppercase; margin-bottom: 8px;
}
.metric-value { font-size: 30px; font-weight: 800; color: #1F2937; }

.risk-card { border-left: 7px solid var(--purple); }
.career-card { border-left: 6px solid var(--purple); }
.agent-box { border-left: 6px solid var(--blue); }
.placement-card { border-left: 7px solid var(--purple); }

.factor-card { border-left: 6px solid var(--purple); }
.factor-header {
    display: flex; align-items: center; gap: 10px;
    font-size: 17px; font-weight: 700; color: #1F2937; margin-bottom: 6px;
}
.factor-icon { font-size: 22px; }
.factor-meta { font-size: 13px; color: var(--text-soft); margin-bottom: 8px; }
.factor-meta b { color: #1F2937; }
.factor-explanation { font-size: 13.5px; color: #374151; line-height: 1.5; margin-bottom: 10px; }
.impact-bar-track { width: 100%; height: 10px; background: #EEF0F6; border-radius: 10px; overflow: hidden; }
.impact-bar-fill { height: 100%; border-radius: 10px; background: linear-gradient(90deg, var(--purple), #FF6B6B); }

.week-card { border-top: 5px solid var(--blue); }
.goal-card {
    background: linear-gradient(135deg, #EEF2FF, #FFFFFF);
    border: 1px solid #E4E7FB; border-radius: 16px; padding: 18px 20px; margin-bottom: 14px;
}
.goal-card h4 { margin: 0 0 8px 0; color: var(--purple-dark); }

.action-flashcard {
    background: #FAFAFF; border: 1px solid #ECECFB; border-radius: 14px;
    padding: 14px 16px; margin-bottom: 10px;
}
.action-flashcard .action-label {
    font-size: 12px; font-weight: 700; color: var(--purple-dark);
    text-transform: uppercase; letter-spacing: 0.3px; margin-bottom: 4px;
}
.action-flashcard .action-text { font-size: 14.5px; color: #1F2937; margin-bottom: 8px; }
.outcome-badge {
    display: inline-block; background: #E7F9EF; color: #067A46;
    font-size: 12px; font-weight: 700; padding: 5px 12px; border-radius: 999px;
}
.risk-tag {
    display: inline-block; background: #FFF1E9; color: #B4530A;
    font-size: 11.5px; font-weight: 700; padding: 4px 11px; border-radius: 999px; margin-left: 8px;
}
.progress-track { width: 100%; height: 12px; background: #EEF0F6; border-radius: 10px; overflow: hidden; margin: 8px 0 4px 0; }
.progress-fill { height: 100%; border-radius: 10px; background: linear-gradient(90deg, var(--blue), var(--green)); }
.progress-label { font-size: 12px; color: var(--text-soft); font-weight: 600; }

.support-card { background: #F7FBF9; border-left: 5px solid var(--green); }

.skill-badge {
    display: inline-block; background: #EDE9FE; color: #4B3FE4;
    padding: 9px 16px; border-radius: 999px; margin: 5px 6px 5px 0; font-weight: 600; font-size: 13.5px;
}

.section-title { font-size: 20px; font-weight: 800; color: #1F2937; margin: 22px 0 10px 0; }

.step-number {
    background: #6C63FF; color: white; padding: 6px 14px; border-radius: 20px; font-weight: 700;
}
.badge {
    display: inline-block; padding: 6px 14px; border-radius: 20px;
    background: #EDE9FE; color: #4B3FE4; margin: 5px 5px 5px 0; font-weight: 700; font-size: 12.5px;
}

@media (max-width: 768px) {
    .gradient-header h1 { font-size: 26px; }
    .gradient-header { padding: 22px; }
}
</style>
""",
    unsafe_allow_html=True,
)


# ============================================================
# 12. LOGIN FLOW (Student ID + Password via streamlit-authenticator)
# ============================================================
import streamlit_authenticator as stauth


def _secrets_to_dict(node: Any) -> Any:
    """Recursively converts a Streamlit secrets AttrDict (or any mapping) into a
    plain, JSON/YAML-friendly dict so it can be handed to streamlit-authenticator."""
    if hasattr(node, "keys") and hasattr(node, "values"):
        return {key: _secrets_to_dict(value) for key, value in node.items()}
    return node


def _load_auth_config() -> Optional[dict]:
    """
    Loads authentication configuration from st.secrets.

    Expected structure in .streamlit/secrets.toml:

        [auth.cookie]
        name = "sar_student_auth"
        key = "a-long-random-secret"
        expiry_days = 1

        [auth.credentials.usernames.STU202600058]
        name = "Student Name"
        email = "student@example.com"
        password = "$2b$..."

    Returns None (and shows a professional, non-technical error) if the
    configuration is missing or malformed, so the caller can stop safely
    without ever reaching the dashboard.

    IMPORTANT: streamlit-authenticator normalizes usernames to lowercase
    internally (this is documented library behaviour, not a bug we're
    introducing). If the usernames dict here still had mixed/upper case
    keys, the entered Student ID and the stored key could end up being
    compared inconsistently depending on the exact installed version,
    causing valid credentials to be rejected. We defensively lowercase
    every username key here ourselves so behaviour is identical and
    predictable no matter which patch version of the library is installed.
    """
    try:
        auth_secrets = st.secrets["auth"]
    except Exception:
        st.error(
            "⚠️ Sign-in is not available right now. Please contact the "
            "platform administrator."
        )
        return None

    try:
        cookie_cfg = _secrets_to_dict(auth_secrets["cookie"])
        credentials_cfg = _secrets_to_dict(auth_secrets["credentials"])

        cookie_name = cookie_cfg["name"]
        cookie_key = cookie_cfg["key"]
        cookie_expiry_days = int(cookie_cfg.get("expiry_days", 1))

        if not cookie_key or cookie_key.strip() in {
            "",
            "replace-with-a-long-random-secret",
        }:
            raise ValueError("Cookie signing key is missing or is a placeholder value.")

        raw_usernames = credentials_cfg.get("usernames")
        if not raw_usernames:
            raise ValueError("No student credentials are configured.")

        # Normalize every username key to lowercase and trim whitespace, so
        # login matching is stable regardless of streamlit-authenticator's
        # own internal lowercasing behaviour.
        credentials_cfg["usernames"] = {
            str(username).strip().lower(): details
            for username, details in raw_usernames.items()
        }

    except Exception:
        st.error(
            "⚠️ Sign-in is not available right now. Please contact the "
            "platform administrator."
        )
        return None

    return {
        "credentials": credentials_cfg,
        "cookie_name": cookie_name,
        "cookie_key": cookie_key,
        "cookie_expiry_days": cookie_expiry_days,
    }


def clear_student_session_state() -> None:
    """Removes every student-specific key from session state. Used on logout,
    on a failed post-authentication CSV lookup, and before returning to the
    login screen, so no previous student's data can remain visible."""
    keys_to_clear = [
        "student_logged_in",
        "student_id",
        "student_name",
        "placement_plan_response",
        "placement_plan_student_id",
        "placement_student_id",
        "selected_target_companies",
        "last_risk_prediction",
        "last_risk_student_id",
        "show_dev_json",
        "roadmap_cache",
    ]
    for key in keys_to_clear:
        st.session_state.pop(key, None)


def require_student_authentication() -> tuple:
    """
    Renders the Student ID + Password login widget (streamlit-authenticator),
    validates the authenticated Student ID against the student CSV dataset,
    and returns (student_id, student_name).

    Every non-success path calls st.stop(), so no sidebar, API call, CSV
    lookup, or dashboard content below this function can ever render before
    authentication succeeds.

    Note on casing: streamlit-authenticator returns whatever username it
    matched internally, which it normalizes to lowercase. That lowercased
    value is NOT what we use as the student_id going forward — we resolve
    it back to the exact-case Student ID from the CSV via
    find_canonical_student_id(), so every downstream call (Risk Engine,
    Mentor Agent, Faculty API, roadmap, etc.) receives the Student ID in
    the exact form those systems expect (e.g. "STU202600001").
    """
    auth_config = _load_auth_config()
    if auth_config is None:
        st.stop()

    authenticator = stauth.Authenticate(
        auth_config["credentials"],
        auth_config["cookie_name"],
        auth_config["cookie_key"],
        auth_config["cookie_expiry_days"],
    )
    # Kept in session_state so the sidebar can render the matching logout widget.
    st.session_state["_authenticator"] = authenticator

    st.markdown(
        """
        <div class="gradient-header">
        <h1>🎓 Student Sign In</h1>
        <p>Welcome to the Student Success &amp; Retention Platform</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    try:
        authenticator.login(location="main")
    except Exception:
        st.error("⚠️ Sign-in is temporarily unavailable. Please try again shortly.")
        st.stop()

    authentication_status = st.session_state.get("authentication_status")

    if authentication_status is False:
        st.error("Student ID or password is incorrect.")
        st.stop()

    if authentication_status is None:
        st.info("Please enter your Student ID and password.")
        st.stop()

    # authentication_status is True beyond this point.
    login_username = st.session_state.get("username")
    authenticated_name = st.session_state.get("name") or login_username

    if not login_username:
        st.error("⚠️ A sign-in error occurred. Please try again.")
        clear_student_session_state()
        st.stop()

    # Resolve the (possibly lowercased-by-the-library) login username back
    # to the exact-case Student ID used by the CSV and every backend system.
    canonical_student_id = find_canonical_student_id(login_username)

    if canonical_student_id is None:
        st.error(
            "⚠️ Your account could not be matched to a student record. "
            "Please contact the platform administrator."
        )
        try:
            # Programmatically clears the auth cookie/session without
            # rendering a visible button.
            authenticator.logout(button_name="Logout", location="unrendered")
        except Exception:
            pass
        clear_student_session_state()
        st.stop()

    st.session_state.student_logged_in = True
    st.session_state.student_id = canonical_student_id
    st.session_state.student_name = authenticated_name

    return canonical_student_id, authenticated_name


student_id, student_name = require_student_authentication()


# ============================================================
# 13. SIDEBAR
# ============================================================
with st.sidebar:
    st.markdown("### 🎓 Student Profile")

    student_data = get_student_data(student_id)

    if student_data is None:
        st.error("Student data not found")
        st.stop()

    gpa = student_data.get("cgpa", "N/A")
    interest = student_data.get("recommended_career_path", "N/A")

    # Use cached ML prediction when available, otherwise clearly-labeled dataset value.
    cached_roadmap = build_roadmap_from_prediction(student_id)
    if cached_roadmap:
        st.session_state.setdefault("roadmap_cache", {})[student_id] = cached_roadmap
        sidebar_risk_profile = cached_roadmap["risk_profile"]
    else:
        sidebar_risk_profile = {
            "risk_score": student_data.get("academic_risk_score", "N/A"),
            "risk_band": student_data.get("academic_risk_band", "N/A"),
            "source": "dataset_fallback",
        }

    placement_score = student_data.get("placement_readiness_score", "N/A")
    placement_probability = student_data.get("placement_probability", "N/A")

    st.markdown("### Current Snapshot")
    st.write(f"🆔 **{student_id}**")
    st.write(f"🏫 **Department:** {student_data.get('department', 'N/A')}")
    st.write(f"📘 **Year:** {student_data.get('current_year', 'N/A')}")
    st.write(f"🎓 **CGPA:** {gpa}")

    if sidebar_risk_profile.get("source") == "ml":
        st.write(
            f"⚠️ **Risk (ML):** {sidebar_risk_profile['risk_band']} "
            f"({sidebar_risk_profile['risk_score']})"
        )
    else:
        st.write(
            f"⚠️ **Risk (stored):** {sidebar_risk_profile['risk_band']} "
            f"({sidebar_risk_profile['risk_score']})"
        )
        st.caption("ML Risk Engine unavailable — showing stored dataset value.")

    st.write(f"💼 **Placement Score:** {placement_score}")
    st.write(f"📈 **Placement Probability:** {placement_probability}")
    st.write(f"🎯 **Career:** {interest}")

    st.divider()
    show_dev_json = st.checkbox("🛠️ Show Developer Raw JSON", value=False, key="developer_json")
    st.session_state["show_dev_json"] = show_dev_json

    st.divider()
    _authenticator = st.session_state.get("_authenticator")
    if _authenticator is not None:
        _authenticator.logout(button_name="Logout", location="sidebar", key="sidebar_logout_btn")

    st.caption("Student Academic Success & Retention Platform")

# If the logout button above was clicked, streamlit-authenticator has already
# flipped authentication_status for this run. Clear all student-specific
# state immediately and return to the login screen before any further
# dashboard content (header, risk UI, placement UI, etc.) renders.
if st.session_state.get("authentication_status") is not True:
    clear_student_session_state()
    st.rerun()


# ============================================================
# HEADER
# ============================================================
st.markdown(
    """
<div class="gradient-header">
<h1>🎓 Student Success AI</h1>
<p>Personalized academic roadmap, risk explanation and career guidance powered by Agentic AI.</p>
</div>
""",
    unsafe_allow_html=True,
)


# ============================================================
# 14. RISK UI FUNCTIONS
# ============================================================
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
            number={"valueformat": ".2f"},   # ← ADD THIS LINE
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

    valid_factors = []
    for f in factors:
        if not isinstance(f, dict):
            continue
        if "feature" not in f or "shap_contribution" not in f:
            continue
        try:
            contribution = float(f["shap_contribution"])
        except (TypeError, ValueError):
            continue
        valid_factors.append({"feature": f["feature"], "shap_contribution": contribution})

    if not valid_factors:
        if risk_profile.get("source") == "dataset_fallback":
            st.info("SHAP explanation is unavailable because the ML Risk Engine did not respond.")
        else:
            st.info("SHAP explanation is unavailable because the ML Risk Engine did not respond.")
        return

    valid_factors.sort(key=lambda f: abs(f["shap_contribution"]), reverse=True)
    df = pd.DataFrame(valid_factors)

    fig = px.bar(
        df,
        x="shap_contribution",
        y="feature",
        orientation="h",
        text="shap_contribution",
        color="shap_contribution",
        color_continuous_scale="Reds",
        title="ML Feature Contributions",
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
    "attendance_drop": "📉", "attendance_percentage": "📅", "attendance_trend": "📈",
    "backlog_count": "📚", "fee_delay": "💳", "fee_delay_days": "💳",
    "cgpa": "🎓", "internal_marks_avg": "📝", "financial_stress_score": "💰",
    "coding_score": "💻", "internships_completed": "🧑‍💼", "internship_count": "🧑‍💼",
    "study_hours_per_week": "⏱️",
}


def _risk_factor_icon(feature: str) -> str:
    return _FACTOR_ICONS.get(feature, "📌")


def _risk_factor_explanation(feature: str) -> str:
    explanations = {
        "attendance_drop": "Attendance is contributing strongly to academic risk. Improving attendance should be a top priority.",
        "attendance_percentage": "Overall attendance percentage is influencing the risk assessment.",
        "attendance_trend": "The recent direction of attendance (improving/declining) affects risk.",
        "backlog_count": "Pending backlogs are increasing academic pressure and need a focused recovery plan.",
        "fee_delay": "Fee delay may create administrative or financial stress, so support or clarification may be needed.",
        "fee_delay_days": "Days of fee delay may indicate financial stress affecting academics.",
        "cgpa": "Overall CGPA is a strong indicator of current academic standing.",
        "internal_marks_avg": "Internal assessment performance reflects ongoing academic engagement.",
        "financial_stress_score": "Financial stress can affect focus, attendance, and academic performance.",
        "coding_score": "Coding proficiency contributes to overall academic/technical readiness.",
        "internships_completed": "Practical exposure through internships affects overall readiness.",
        "internship_count": "Practical exposure through internships affects overall readiness.",
        "study_hours_per_week": "Weekly study hours reflect consistency of academic effort.",
    }
    return explanations.get(
        feature,
        "This factor is contributing to the student's risk profile and should be monitored.",
    )


def _render_factor_cards(risk_profile: dict) -> None:
    factors = [
        f for f in risk_profile.get("top_factors", [])
        if isinstance(f, dict) and "feature" in f and "shap_contribution" in f
    ]
    if not factors:
        st.info("SHAP explanation is unavailable because the ML Risk Engine did not respond.")
        return

    max_contrib = max(abs(_safe_float(f.get("shap_contribution"))) for f in factors) or 1
    cols = st.columns(2)
    for idx, factor in enumerate(factors):
        feature = factor.get("feature", "Unknown factor")
        value = factor.get("value", "NA")
        contribution = _safe_float(factor.get("shap_contribution"))
        bar_pct = min(100, round((abs(contribution) / max_contrib) * 100))
        icon = _risk_factor_icon(feature)
        explanation = _risk_factor_explanation(feature)

        with cols[idx % 2]:
            st.markdown(
                f"""
                <div class="factor-card">
                    <div class="factor-header">
                        <span class="factor-icon">{icon}</span>
                        <span>{str(feature).replace('_', ' ').title()}</span>
                    </div>
                    <div class="factor-meta">
                        Value: <b>{value}</b> &nbsp;•&nbsp; Contribution: <b>{contribution}</b>
                    </div>
                    <div class="factor-explanation">{explanation}</div>
                    <div class="impact-bar-track">
                        <div class="impact-bar-fill" style="width:{bar_pct}%;"></div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def show_risk_ui(roadmap_result: dict) -> None:
    roadmap = roadmap_result["roadmap"]
    risk_profile = roadmap_result["risk_profile"]

    st.markdown('<div class="section-title">🔎 Risk Explanation</div>', unsafe_allow_html=True)

    if risk_profile.get("source") == "dataset_fallback":
        st.warning("ML Risk Engine unavailable. Showing stored dataset risk information.")

    show_risk_gauge(_safe_float(risk_profile.get("risk_score", 0)))
    st.markdown(
        f"""<div class="card">{roadmap.get("risk_summary", "No summary available.")}</div>""",
        unsafe_allow_html=True,
    )

    st.markdown('<div class="section-title">🔍 Key Risk Factors</div>', unsafe_allow_html=True)

    factors = risk_profile.get("top_factors", [])
    if not factors:
        st.info("SHAP explanation is unavailable because the ML Risk Engine did not respond.")
    else:
        _render_factor_cards(risk_profile)
        show_shap_chart(risk_profile)

    if st.session_state.get("show_dev_json", False):
        with st.expander("🔍 Developer View: Raw JSON", expanded=False):
            st.json(roadmap_result)


# ============================================================
# 15. ROADMAP UI FUNCTIONS
# ============================================================
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

    if risk_profile.get("source") == "dataset_fallback":
        st.warning("ML Risk Engine unavailable. Showing stored dataset risk information.")

    st.markdown('<div class="section-title">📊 Risk Snapshot</div>', unsafe_allow_html=True)

    risk_score = risk_profile.get("risk_score", "NA")
    risk_band = str(risk_profile.get("risk_band", "NA")).upper()
    validation_status = "✅ Passed" if validation.get("is_valid") else "⚠️ Failed"

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(
            f"""<div class="metric-card"><div class="metric-title">Risk Score</div><div class="metric-value">{risk_score}</div></div>""",
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            f"""<div class="metric-card"><div class="metric-title">Risk Band</div><div class="metric-value">{risk_band}</div></div>""",
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            f"""<div class="metric-card"><div class="metric-title">Validation</div><div class="metric-value">{validation_status}</div></div>""",
            unsafe_allow_html=True,
        )

    show_risk_gauge(_safe_float(risk_score, 0))

    st.markdown('<div class="section-title">📌 Risk Summary</div>', unsafe_allow_html=True)
    st.markdown(
        f"""<div class="card">{roadmap.get("risk_summary", "No risk summary available.")}</div>""",
        unsafe_allow_html=True,
    )

    factors = risk_profile.get("top_factors", [])

    st.markdown('<div class="section-title">🔥 Risk Factor Analysis</div>', unsafe_allow_html=True)
    if not factors:
        st.info("SHAP explanation is unavailable because the ML Risk Engine did not respond.")
    else:
        show_shap_chart(risk_profile)

    st.markdown('<div class="section-title">🔍 Why am I at Risk?</div>', unsafe_allow_html=True)
    if factors:
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

            with st.expander(f"📅 {week_key.replace('_', ' ').title()}", expanded=(idx == 0)):
                goal = (
                    details.get("goal")
                    or details.get("weekly_goal")
                    or details.get("objective")
                    or "Improve academic performance"
                )
                progress_pct = round(((idx + 1) / total_weeks) * 100) if total_weeks else 0
                filled_blocks = round(progress_pct / 25)
                progress_bar_text = "🟦" * filled_blocks + "⬜" * (4 - filled_blocks)

                st.markdown(
                    f"""
                    <div class="goal-card">
                        <h4>🎯 Weekly Goal</h4>
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
                f"""<div class="support-card"><b>{key.replace('_', ' ').title()}</b><br>{value}</div>""",
                unsafe_allow_html=True,
            )
    else:
        st.info("No additional support recommendations at this time.")

    st.markdown('<div class="section-title">📉 Risk Reduction Estimate</div>', unsafe_allow_html=True)
    st.markdown(
        f"""<div class="card" style="border-left:6px solid var(--green);">{roadmap.get("risk_reduction_estimate", "")}</div>""",
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
        key="download_roadmap_json",
    )

    if st.session_state.get("show_dev_json", False):
        with st.expander("🔍 Developer View: Raw JSON", expanded=False):
            st.json(roadmap_result)


def show_faculty_intervention(student_id: str) -> None:
    intervention = get_faculty_intervention(student_id)

    st.markdown('<div class="section-title">🧑‍🏫 Faculty Approved Intervention Plan</div>', unsafe_allow_html=True)

    if not intervention:
        st.info("No approved intervention available yet.")
        return

    status = clean_html_text(intervention.get("status")) or "N/A"
    approved_by = clean_html_text(intervention.get("approved_by")) or "N/A"

    actions = intervention.get("recommended_actions", [])
    if isinstance(actions, list):
        actions_text = "; ".join(clean_html_text(a) for a in actions if clean_html_text(a))
    else:
        actions_text = clean_html_text(actions)

    plan_text = clean_html_text(
        intervention.get("plan") or intervention.get("follow_up_plan") or actions_text
    )

    with st.container(border=True):
        st.markdown(f"**Status:** {status}")
        st.markdown(f"**Approved By:** {approved_by}")
        st.markdown("**📋 Intervention:**")
        st.write(plan_text if plan_text else "No details provided.")


# ============================================================
# 16. CAREER UI FUNCTIONS
# ============================================================
_FALLBACK_SKILLS = {
    "AI": ["🐍 Python", "🤖 Machine Learning", "🧠 Deep Learning", "🔗 LLMs"],
    "Web Development": ["🌐 HTML/CSS", "⚛️ React", "🟩 Node.js", "🗄️ Databases"],
    "Cybersecurity": ["🛰️ Networking", "🐧 Linux", "🛡️ Security Tools", "🕵️ Ethical Hacking"],
    "Data Science": ["🐍 Python", "🗃️ SQL", "📊 Statistics", "📈 Visualization"],
}


def _extract_section(text: str, headings: list) -> str:
    if not text:
        return ""
    pattern = r"(?:" + "|".join(re.escape(h) for h in headings) + r")\s*[:\-]?\s*\n?"
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if not match:
        return ""
    rest = text[match.end():]
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
    return {
        "summary": _extract_section(text, ["Summary", "Why this field", "Overview", "Career Fit"]),
        "skills": _split_bullets(_extract_section(text, ["Skills", "Skills to Master", "Skill Stack"])),
        "timeline": _split_bullets(_extract_section(text, ["Timeline", "Roadmap", "Learning Plan", "Week"])),
        "projects": _split_bullets(_extract_section(text, ["Projects", "Project Recommendations"])),
        "certifications": _split_bullets(_extract_section(text, ["Certifications", "Courses"])),
        "internship_prep": _extract_section(text, ["Internship", "Internship Preparation"]),
    }


def show_career_ui() -> None:
    response = generate_career_guidance(gpa, interest)
    response_data = response if isinstance(response, dict) else {}
    response_text = response if isinstance(response, str) else ""
    parsed = _parse_career_text(response_text) if response_text else {}

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(
            f"""<div class="ai-card"><div class="metric-title">🎯 Career Interest</div><div class="metric-value">{interest}</div></div>""",
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            f"""<div class="ai-card"><div class="metric-title">🎓 Current GPA</div><div class="metric-value">{gpa}</div></div>""",
            unsafe_allow_html=True,
        )

    summary_text = (
        response_data.get("summary")
        or response_data.get("why_this_field")
        or response_data.get("overview")
        or parsed.get("summary")
        or (
            f"Based on your GPA of {gpa} and interest in {interest}, here is a tailored "
            "guidance plan to help you build the right skills and move toward your career goal."
        )
    )
    st.markdown('<div class="section-title">💡 Career Summary</div>', unsafe_allow_html=True)
    st.markdown(f"""<div class="career-card">{clean_html_text(summary_text)}</div>""", unsafe_allow_html=True)

    skills_list = (
        response_data.get("skills")
        or response_data.get("skill_stack")
        or parsed.get("skills")
        or _FALLBACK_SKILLS.get(interest, ["💡 Problem Solving", "🧩 Projects", "🗣️ Communication"])
    )
    st.markdown('<div class="section-title">🛠 Skills To Master</div>', unsafe_allow_html=True)
    st.markdown(
        "".join(f'<span class="skill-badge">⚡ {clean_html_text(s)}</span>' for s in skills_list),
        unsafe_allow_html=True,
    )

    timeline = response_data.get("timeline") or response_data.get("weekly_plan") or response_data.get("eight_week_plan")
    st.markdown('<div class="section-title">🗓️ Learning Roadmap</div>', unsafe_allow_html=True)

    if isinstance(timeline, dict) and timeline:
        for period, task in timeline.items():
            st.markdown(
                f"""<div class="timeline-card"><h4>{period}</h4><div>🎯 {clean_html_text(task)}</div></div>""",
                unsafe_allow_html=True,
            )
    elif isinstance(timeline, list) and timeline:
        for idx, item in enumerate(timeline, start=1):
            st.markdown(
                f"""<div class="timeline-card"><h4>Step {idx}</h4><div>🎯 {clean_html_text(item)}</div></div>""",
                unsafe_allow_html=True,
            )
    elif parsed.get("timeline"):
        for idx, item in enumerate(parsed["timeline"], start=1):
            st.markdown(
                f"""<div class="timeline-card"><h4>Step {idx}</h4><div>🎯 {clean_html_text(item)}</div></div>""",
                unsafe_allow_html=True,
            )
    else:
        st.info("No detailed roadmap steps were returned for this guidance request.")

    projects = response_data.get("projects") or response_data.get("recommended_projects") or parsed.get("projects")
    st.markdown('<div class="section-title">🚀 Recommended Projects</div>', unsafe_allow_html=True)
    if projects:
        proj_cols = st.columns(min(len(projects), 3) or 1)
        for idx, project in enumerate(projects):
            with proj_cols[idx % len(proj_cols)]:
                st.markdown(
                    f"""<div class="ai-card" style="text-align:center;"><div style="font-size:22px;">📁</div><div style="font-weight:700; margin-top:6px;">{clean_html_text(project)}</div></div>""",
                    unsafe_allow_html=True,
                )
    else:
        st.info("No specific project recommendations were returned.")

    certifications = response_data.get("certifications") or response_data.get("courses") or parsed.get("certifications")
    if certifications:
        st.markdown('<div class="section-title">📜 Certifications & Courses</div>', unsafe_allow_html=True)
        for cert in certifications:
            cert_name = clean_html_text(cert.get("name", cert)) if isinstance(cert, dict) else clean_html_text(cert)
            cert_provider = clean_html_text(cert.get("provider", "")) if isinstance(cert, dict) else ""
            st.markdown(
                f"""<div class="ai-card"><b>📜 {cert_name}</b>{f"<br><small>{cert_provider}</small>" if cert_provider else ""}</div>""",
                unsafe_allow_html=True,
            )

    internship_prep = response_data.get("internship_prep") or response_data.get("internship_preparation") or parsed.get("internship_prep")
    if internship_prep:
        st.markdown('<div class="section-title">💼 Internship Preparation</div>', unsafe_allow_html=True)
        st.markdown(f"""<div class="career-card">{clean_html_text(internship_prep)}</div>""", unsafe_allow_html=True)

    if response_text and not any(parsed.values()):
        st.markdown('<div class="section-title">🧠 AI Career Insights</div>', unsafe_allow_html=True)
        st.markdown(f"""<div class="career-card">{clean_html_text(response_text)}</div>""", unsafe_allow_html=True)

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


# ============================================================
# 17. PLACEMENT UI FUNCTIONS
# ============================================================
def render_placement_plan(plan: dict) -> None:
    """Single canonical placement renderer. Renders every section exactly once."""
    st.markdown('<div class="section-title">💼 Personalized Placement Plan</div>', unsafe_allow_html=True)

    readiness_summary = clean_html_text(plan.get("readiness_summary"))
    with st.container(border=True):
        st.markdown("#### 📌 Readiness Summary")
        st.write(readiness_summary) if readiness_summary else st.info(
            "Readiness summary was not returned by the Mentor Agent."
        )

    company_guidance = get_company_guidance(plan)
    with st.container(border=True):
        st.markdown("#### 🏢 Company Selection Guidance")
        st.write(company_guidance) if company_guidance else st.info(
            "Company-specific guidance was not returned by the Mentor Agent."
        )

    st.markdown("#### 📚 Preparation Roadmap")
    steps = normalize_preparation_steps(plan.get("preparation_steps"))
    if steps:
        for idx, step in enumerate(steps, start=1):
            with st.container(border=True):
                left, right = st.columns([4, 1])
                with left:
                    st.markdown(f"**🚀 Step {idx}: {step['title']}**")
                with right:
                    st.caption(f"⏳ {step['duration']}")
                st.markdown(f'<span class="badge">🔥 {step["priority"].upper()}</span>', unsafe_allow_html=True)
                if step["detail"]:
                    st.write(step["detail"])
    else:
        st.info("No preparation roadmap was returned.")

    risk_actions = normalize_risk_actions(plan.get("risk_factors_and_actions"))
    if risk_actions:
        st.markdown("#### ⚠️ Risk Factors & Actions")
        for item in risk_actions:
            with st.container(border=True):
                st.markdown(f"**⚠️ {item['risk']}**")
                if item["action"]:
                    st.write(item["action"])

    timeline = clean_html_text(plan.get("timeline"))
    if timeline:
        with st.container(border=True):
            st.markdown("#### 📅 Timeline")
            st.write(timeline)

    verification_note = clean_html_text(plan.get("data_verification_note"))
    if verification_note:
        with st.container(border=True):
            st.markdown("#### ✅ Data Verification")
            st.write(verification_note)


# ============================================================
# 18. MAIN PAGE FLOW
# ============================================================
st.markdown('<div class="section-title">💼 Placement Plan Request</div>', unsafe_allow_html=True)

if "placement_plan_response" not in st.session_state:
    st.session_state.placement_plan_response = None
if "placement_student_id" not in st.session_state:
    st.session_state.placement_student_id = None

target_companies = st.multiselect(
    "Select target companies", TARGET_COMPANY_OPTIONS, key="target_companies_select"
)
custom_company = st.text_input(
    "Add another company if not listed",
    placeholder="Example: Atlassian, Uber, Mastercard",
    key="custom_company_input",
)

if st.button("📩 Prepare Placement Plan Request", key="prepare_placement_btn"):
    companies = list(target_companies)
    if custom_company and custom_company.strip():
        companies.append(custom_company.strip())

    if not companies:
        st.warning("Please select or enter at least one target company.")
    else:
        saved_response = save_target_companies(student_id, companies)
        if saved_response:
            st.success(f"✅ Target companies saved: {', '.join(companies)}")

            with st.spinner("Generating placement plan from Mentor Agent..."):
                placement_plan_response = generate_placement_plan(student_id)

            if placement_plan_response:
                try:
                    plan = extract_placement_plan(placement_plan_response)
                    st.session_state.placement_plan_response = plan
                    st.session_state.placement_student_id = student_id
                except ValueError:
                    st.error("Received an invalid placement plan response.")
                    st.session_state.placement_plan_response = None
            else:
                st.error("Placement plan could not be generated.")
                st.session_state.placement_plan_response = None

if (
    st.session_state.placement_plan_response
    and st.session_state.placement_student_id == student_id
):
    render_placement_plan(st.session_state.placement_plan_response)


st.markdown('<div class="section-title">💬 Ask the Student Success Agent</div>', unsafe_allow_html=True)

user_question = st.text_input(
    "Your question",
    placeholder="Example: Why is my risk score high? How should I improve my GPA?",
    key="ask_agent_question",
)

if st.button("🚀 Ask Agent", use_container_width=True, key="ask_agent_btn"):
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
                roadmap_result = build_roadmap_from_prediction(student_id)
            if roadmap_result:
                show_roadmap_ui(roadmap_result)
                show_faculty_intervention(student_id)
            else:
                st.error("Could not build a roadmap for this student.")

        elif intent == "RISK":
            with st.spinner("Analyzing risk factors..."):
                roadmap_result = build_roadmap_from_prediction(student_id)
            if roadmap_result:
                show_risk_ui(roadmap_result)
            else:
                st.error("Could not analyze risk for this student.")

        elif intent == "SUPPORT":
            show_support_ui()
            show_faculty_intervention(student_id)

        elif intent == "RAG":
            show_rag_ui()

        else:
            st.warning("I couldn't understand your question clearly.")
