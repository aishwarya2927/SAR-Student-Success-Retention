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

Generate a professional intervention plan for the assigned faculty mentor.

Use the following structure exactly:

1. Student Summary
2. Recommended Actions
3. Priority Level
4. Follow-up Plan

Requirements:
- Use a professional and concise tone.
- Recommend only actions supported by the provided information.
- Mention relevant university resources where applicable.
- Do not invent student information.
- Return only the intervention plan.
"""

    try:
      recommendation = generate_text(prompt)

    except Exception as e:
        recommendation = (
            "Unable to generate intervention plan at this time. "
            f"Error: {str(e)}"
        )

    return recommendation