from agents.roadmap_agent import ask_gemini
from utils.mock_data import get_mock_risk_profile
from prompts.roadmap_prompt import (
    ROADMAP_SYSTEM_PROMPT,
    ROADMAP_OUTPUT_FORMAT,
)
from utils.response_validator import validate_roadmap_response
import json


def generate_improvement_roadmap(student_id: str):
    # Get mock student risk profile
    risk_data = get_mock_risk_profile(student_id)

    # Build risk factor list
    factor_lines = []
    for factor in risk_data["top_factors"]:
        factor_lines.append(
            f"- {factor['feature']} | "
            f"value: {factor['value']} | "
            f"contribution: {factor['shap_contribution']}"
        )

    factor_text = "\n".join(factor_lines)

    # Build final prompt
    prompt = f"""
{ROADMAP_SYSTEM_PROMPT}

STUDENT CONTEXT

Student ID: {student_id}

Risk Score: {risk_data['risk_score']}

Risk Band: {risk_data['risk_band']}

Last Updated: {risk_data['last_updated']}

TOP RISK FACTORS

{factor_text}

==================================================

PRIMARY TASK

==================================================

Analyze the student's academic risk profile.

Generate a highly personalized 4-week improvement roadmap.

Requirements:

- Every recommendation MUST reference one or more risk factors.
- Never generate generic advice.
- Never invent university policies.
- Never invent student data.
- Every week should contain realistic actions.
- Every action should be measurable.
- Recommend free or low-cost resources whenever possible.
- Keep the tone encouraging and supportive.

==================================================

OUTPUT REQUIREMENTS

==================================================

Return ONLY valid JSON.

Do NOT include markdown.

Do NOT include explanations.

Do NOT include headings.

Do NOT wrap JSON inside ```.

Your response must begin with a JSON object.

If you cannot answer, still return valid JSON.

Follow this schema exactly.

{ROADMAP_OUTPUT_FORMAT}
"""

    # Call Gemini
    roadmap_json = ask_gemini(prompt)

    # DEBUG: Print Gemini response
    print("\n========== GEMINI ROADMAP RESPONSE ==========")
    print(json.dumps(roadmap_json, indent=2))
    print("=============================================\n")

    # Validate JSON
    validation = validate_roadmap_response(roadmap_json)

    # Return result
    return {
        "student_id": student_id,
        "risk_profile": risk_data,
        "roadmap": roadmap_json,
        "validation": validation,
    }