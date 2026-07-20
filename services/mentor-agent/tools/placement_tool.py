import os
import time
import json
import sys
from google import genai

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_student

_client = None

VALID_PRIORITIES = {"primary", "secondary", "ongoing", "final-stage"}
DEFAULT_PRIORITY = "secondary"


def _get_client():
    global _client
    if _client is None:
        api_key = os.getenv("GEMINI_API_KEY_PLACEMENT") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY_PLACEMENT or GEMINI_API_KEY environment variable is not set.")
        _client = genai.Client(api_key=api_key)
    return _client


def _stringify_factors(risk_factors: list) -> str:
    if not risk_factors:
        return "none flagged"
    parts = []
    for f in risk_factors:
        if isinstance(f, dict):
            name = f.get("feature") or f.get("factor") or f.get("name") or str(f)
            value = f.get("value")
            parts.append(f"{name} ({value})" if value is not None else str(name))
        else:
            parts.append(str(f))
    return ", ".join(parts)


def _stringify_placement_profile(profile: dict) -> str:
    if not profile:
        return "No placement readiness data available."

    lines = []
    if "weekly_study_hours" in profile:
        lines.append(f"Weekly study hours: {profile['weekly_study_hours']}")
    if "time_management_score" in profile:
        lines.append(f"Time management score: {profile['time_management_score']}/100")

    tech = profile.get("technical_skills", {})
    if tech:
        lines.append(f"Coding score: {tech.get('coding_score', 'N/A')}/100, AI/ML score: {tech.get('ai_ml_score', 'N/A')}/100")

    soft = profile.get("soft_skills", {})
    if soft:
        lines.append(
            f"Communication: {soft.get('communication_skill_score', 'N/A')}/100, "
            f"Teamwork: {soft.get('teamwork_score', 'N/A')}/100, "
            f"Presentation: {soft.get('presentation_score', 'N/A')}/100"
        )

    portfolio = profile.get("portfolio_metrics", {})
    if portfolio:
        lines.append(
            f"Internships completed: {portfolio.get('internship_count', 0)}, "
            f"Certifications completed: {portfolio.get('completed_certifications', 0)}"
        )

    return "\n".join(lines) if lines else "No placement readiness data available."


def _verification_note(company_data: dict) -> str:
    """Computed deterministically in Python instead of asked from the LLM."""
    if not company_data:
        return "No target companies selected; guidance is based on general knowledge."

    curated = [c for c, d in company_data.items() if d.get("is_curated")]
    general = [c for c, d in company_data.items() if not d.get("is_curated")]

    parts = []
    if curated:
        parts.append(f"{', '.join(curated)} data verified from institutional placement guides")
    if general:
        parts.append(f"{', '.join(general)} based on general knowledge — recommend placement cell verification")

    return "; ".join(parts) + "."


def _normalize_priority(value) -> str:
    """Never trust the LLM's exact spelling/casing for fields other code
    branches on. Snap anything unrecognized to a safe default."""
    if not isinstance(value, str):
        return DEFAULT_PRIORITY
    cleaned = value.strip().lower()
    return cleaned if cleaned in VALID_PRIORITIES else DEFAULT_PRIORITY


def _normalize_preparation_steps(steps) -> list:
    """Guarantee every step has the same 4 keys, correct types, every time —
    regardless of what Gemini actually returned."""
    if not isinstance(steps, list):
        return []

    normalized = []
    for step in steps:
        if not isinstance(step, dict):
            continue
        normalized.append({
            "title": str(step.get("title", "")).strip(),
            "duration": str(step.get("duration", "")).strip() or "unspecified",
            "priority": _normalize_priority(step.get("priority")),
            "detail": str(step.get("detail", "")).strip(),
        })
    return normalized


def _normalize_risk_factors_and_actions(items) -> list:
    if not isinstance(items, list):
        return []
    normalized = []
    for item in items:
        if not isinstance(item, dict):
            continue
        normalized.append({
            "risk": str(item.get("risk", "")).strip(),
            "action": str(item.get("action", "")).strip(),
        })
    return normalized


def _normalize_recommended_resources(resources) -> list:
    if not isinstance(resources, list):
        return []
    normalized = []
    for res in resources:
        if not isinstance(res, dict):
            continue
        normalized.append({
            "title": str(res.get("title", "")).strip(),
            "type": str(res.get("type", "Course")).strip(),
            "link": str(res.get("link", "")).strip(),
            "description": str(res.get("description", "")).strip(),
        })
    return normalized



def _success_envelope(plan: dict) -> dict:
    return {
        "generation_status": "ok",
        "placement_plan": plan,
        "error_message": None,
    }


def _error_envelope(message: str, raw_text: str = "") -> dict:
    return {
        "generation_status": "error",
        "placement_plan": None,
        "error_message": message,
        "raw_text": raw_text,
    }


# Single unified schema is requested regardless of whether the student has
# target companies selected. Both "company_comparison" and
# "company_selection_guidance" are ALWAYS present in the response (one will
# just be an empty string / short note when not applicable), so downstream
# consumers never need to check "does this key exist" based on branch logic.

COMBINED_PLAN_TEMPLATE = """You are a placement mentor assistant. Generate a personalized, actionable placement roadmap for this student, covering ALL of their target companies together in one combined plan.

Student ID: {student_id}
Risk Band: {risk_band}
Key Risk Factors: {risk_factors}

Student's Placement Readiness Profile:
{placement_profile_str}

{career_preferences}

Target Companies and available information:
{company_sections}

Respond ONLY with valid JSON, no markdown code fences, no preamble, no markdown formatting (no asterisks, no bold, no headers) anywhere inside any string value, matching this EXACT structure with EVERY key present:

{{
  "readiness_summary": "short paragraph summarizing overall readiness, referencing actual scores",
  "company_comparison": "paragraph comparing preparation focus areas across the target companies",
  "company_selection_guidance": "",
  "preparation_steps": [
    {{
      "title": "short 3-6 word action title, no numbering, no formatting",
      "duration": "short duration or timeframe, e.g. '10-12 weeks' or 'ongoing'",
      "priority": "one of: primary, secondary, ongoing, final-stage",
      "detail": "1-3 plain sentences explaining the step, referencing actual scores where relevant"
    }}
  ],
  "timeline": "paragraph describing a realistic timeline",
  "risk_factors_and_actions": [
    {{"risk": "risk factor name", "action": "how to address it"}}
  ],
  "recommended_resources": [
    {{
      "title": "Resource/Course/Playlist Title (e.g. 'freeCodeCamp System Design Course' or 'LeetCode Top Interview 150')",
      "type": "Course | Playlist | Documentation | Book",
      "link": "MUST be a 100% valid, existing URL. If recommending a specific course or playlist, use a search results link (e.g., 'https://www.youtube.com/results?search_query=system+design+playlist+freecodecamp' or 'https://www.coursera.org/search?query=system+design') to prevent 404 errors. Standard homepages like 'https://leetcode.com/' or 'https://www.geeksforgeeks.org/' are also acceptable. NEVER invent specific paths that do not exist.",
      "description": "Short explanation of why this resource is suggested for the student's needs"
    }}
  ]
}}

Leave "company_selection_guidance" as an empty string since target companies are already selected.
Provide 3-5 recommended_resources tailored to the student's technical/soft skill gaps or target companies.
Provide 4-6 preparation_steps, ordered by when the student should tackle them."""


GENERAL_READINESS_TEMPLATE = """You are a placement mentor assistant. This student has not selected any target companies yet. Generate a general placement-readiness plan.

Student ID: {student_id}
Risk Band: {risk_band}
Key Risk Factors: {risk_factors}

Student's Placement Readiness Profile:
{placement_profile_str}

{career_preferences}

Respond ONLY with valid JSON, no markdown code fences, no preamble, no markdown formatting (no asterisks, no bold, no headers) anywhere inside any string value, matching this EXACT structure with EVERY key present:

{{
  "readiness_summary": "short paragraph summarizing current readiness based on risk profile and skill scores",
  "company_comparison": "",
  "company_selection_guidance": "paragraph on how to identify and shortlist target companies",
  "preparation_steps": [
    {{
      "title": "short 3-6 word action title, no numbering, no formatting",
      "duration": "short duration or timeframe, e.g. '10-12 weeks' or 'ongoing'",
      "priority": "one of: primary, secondary, ongoing, final-stage",
      "detail": "1-3 plain sentences explaining the step, referencing actual scores where relevant"
    }}
  ],
  "timeline": "paragraph describing a realistic timeline, e.g. general skill-building milestones",
  "risk_factors_and_actions": [
    {{"risk": "risk factor name", "action": "how to address it"}}
  ],
  "recommended_resources": [
    {{
      "title": "Resource/Course/Playlist Title (e.g. 'freeCodeCamp System Design Course' or 'LeetCode Top Interview 150')",
      "type": "Course | Playlist | Documentation | Book",
      "link": "MUST be a 100% valid, existing URL. If recommending a specific course or playlist, use a search results link (e.g., 'https://www.youtube.com/results?search_query=system+design+playlist+freecodecamp' or 'https://www.coursera.org/search?query=system+design') to prevent 404 errors. Standard homepages like 'https://leetcode.com/' or 'https://www.geeksforgeeks.org/' are also acceptable. NEVER invent specific paths that do not exist.",
      "description": "Short explanation of why this resource is suggested for the student's needs"
    }}
  ]
}}

Leave "company_comparison" as an empty string since no target companies are selected yet.
Provide 3-5 recommended_resources tailored to the student's technical/soft skill gaps or general career focus.
Provide 4-6 preparation_steps, ordered by when the student should tackle them."""


def _build_company_sections(company_data: dict) -> str:
    sections = []
    for company, data in company_data.items():
        if data["is_curated"] and data["context"]:
            content = "Verified information:\n" + "\n\n".join(data["context"])
        else:
            content = "No verified institutional data available — use general knowledge, flag for placement cell verification."
        sections.append(f"### {company}\n{content}")
    return "\n\n".join(sections)


def draft_placement_plan(student_id: str, target_companies: list[str], risk_band: str, risk_factors: list, company_data: dict, placement_profile: dict = None):
    risk_factors_str = _stringify_factors(risk_factors)
    placement_profile_str = _stringify_placement_profile(placement_profile)

    local_student = get_student(student_id)
    pref_str = ""
    if local_student:
        pref_str = f"""
Student Career & Placement Preferences (Tailor preparation recommendations to these):
- Target Job Roles: {", ".join(local_student.get("preferred_roles", []))}
- Preferred Locations: {", ".join(local_student.get("preferred_locations", []))}
- Minimum Expected Package (CTC): {local_student.get("min_ctc") or "No Preference"}
- Preferred Company Types: {", ".join(local_student.get("company_types", []))}
- Max Service Bond Acceptable: {local_student.get("max_bond_years") or "No Limit"}
- Preferred Work Mode: {local_student.get("work_mode") or "No Preference"}
"""

    if not target_companies:
        prompt = GENERAL_READINESS_TEMPLATE.format(
            student_id=student_id,
            risk_band=risk_band,
            risk_factors=risk_factors_str,
            placement_profile_str=placement_profile_str,
            career_preferences=pref_str
        )
    else:
        company_sections = _build_company_sections(company_data)
        prompt = COMBINED_PLAN_TEMPLATE.format(
            student_id=student_id,
            risk_band=risk_band,
            risk_factors=risk_factors_str,
            placement_profile_str=placement_profile_str,
            company_sections=company_sections,
            career_preferences=pref_str
        )

    client = _get_client()
    max_retries = 5
    raw_text = ""

    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model="gemini-3.1-flash-lite",
                contents=prompt
            )
            raw_text = response.text.strip()

            if raw_text.startswith("```"):
                raw_text = raw_text.strip("`")
                if raw_text.startswith("json"):
                    raw_text = raw_text[4:].strip()

            parsed = json.loads(raw_text)

            # Rebuild the plan explicitly so the response ALWAYS has the same
            # keys, types, and normalized values — regardless of what Gemini
            # actually returned. This is the real consistency guarantee, not
            # just the prompt instructions above.
            plan = {
                "readiness_summary": str(parsed.get("readiness_summary", "")).strip(),
                "company_comparison": str(parsed.get("company_comparison", "")).strip(),
                "company_selection_guidance": str(parsed.get("company_selection_guidance", "")).strip(),
                "preparation_steps": _normalize_preparation_steps(parsed.get("preparation_steps")),
                "timeline": str(parsed.get("timeline", "")).strip(),
                "risk_factors_and_actions": _normalize_risk_factors_and_actions(parsed.get("risk_factors_and_actions")),
                "recommended_resources": _normalize_recommended_resources(parsed.get("recommended_resources")),
                "data_verification_note": _verification_note(company_data),
            }

            return _success_envelope(plan)

        except json.JSONDecodeError:
            return _error_envelope("Could not parse structured plan", raw_text)
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(20 * (attempt + 1))
            else:
                return _error_envelope(f"Unable to generate placement plan after {max_retries} attempts: {e}")