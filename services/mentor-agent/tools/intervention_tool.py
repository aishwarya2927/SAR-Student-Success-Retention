import json

from llm.gemini_client import generate_text


def draft_intervention_plan(
    risk_profile: dict,
    gathered_info: dict
) -> dict:
    """
    Generates a structured intervention plan using the Gemini LLM.
    """

    # Format top risk factors (if available)
    top_factors = "Not available."

    if risk_profile.get("top_factors"):

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

    # Format retrieved university resources
    resource_text = ""

    if gathered_info.get("resources"):

        resource_text = "Relevant University Support Resources\n\n"

        for index, resource in enumerate(
            gathered_info["resources"],
            start=1
        ):

            resource_text += (
                f"{index}. {resource}\n\n"
            )

    prompt = f"""
You are an experienced university academic mentor.

Student ID:
{risk_profile["student_id"]}

Predicted Risk Band:
{risk_profile["risk_band"]}

Model Confidence:
{risk_profile["confidence"] * 100:.2f}%

The confidence represents how certain the prediction model is about the assigned risk band. It is NOT a measure of the student's level of risk.

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

        return json.loads(recommendation)

    except json.JSONDecodeError:

        return {
            "error": "Gemini returned an invalid JSON response."
        }

    except Exception as e:

        return {
            "error": f"Unable to generate intervention plan: {str(e)}"
        }