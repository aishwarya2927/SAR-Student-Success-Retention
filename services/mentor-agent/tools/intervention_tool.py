import json
from llm.gemini_client import generate_text

def draft_intervention_plan(
    risk_profile: dict,
    gathered_info: dict
) -> str:

    # Format top risk factors
    top_factors = "\n".join(
        f"- {factor['feature'].replace('_', ' ').title()}"
        for factor in risk_profile["top_factors"]
    )

    # Format scholarship information
    scholarship_info = ""

    if "scholarship" in gathered_info:

        scholarship = gathered_info["scholarship"]

        status = (
            "Eligible"
            if scholarship["eligible"]
            else "Not Eligible"
        )

        scholarship_info = f"""
Scholarship Assessment

Status:
{status}

Reason:
{scholarship['message']}
"""

    # Format retrieved resources
    resource_text = ""

    if "resources" in gathered_info:

        resource_text = "Relevant University Resources\n\n"

        for index, resource in enumerate(
            gathered_info["resources"],
            start=1
        ):

            resource_text += f"{index}. {resource}\n\n"

    # NOW create the prompt
    prompt = f"""
You are an experienced university academic mentor.

Student ID:
{risk_profile["student_id"]}

Risk Band:
{risk_profile["risk_band"]}

Risk Score:
{risk_profile["risk_score"]}

Top Risk Factors

{top_factors}

{scholarship_info}

{resource_text}

Return ONLY a valid JSON object.

Use this exact schema:

{{
  "student_summary": "string",
  "recommended_actions": [
    "string",
    "string"
  ],
  "priority_level": "High | Medium | Low",
  "follow_up_plan": "string"
}}

Requirements:
- Do not include markdown.
- Do not wrap the JSON in ``` blocks.
- Do not include explanations before or after the JSON.
- Recommend only actions supported by the provided information.
- Mention relevant university resources where applicable.
- Do not invent student information.
"""

    try:
        recommendation = generate_text(prompt)

        recommendation = json.loads(recommendation)

    except Exception as e:
        recommendation = {
            "error": f"Unable to generate intervention plan: {str(e)}"
        }

    return recommendation