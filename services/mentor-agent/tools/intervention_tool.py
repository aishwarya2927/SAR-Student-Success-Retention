def draft_intervention_plan(
    risk_profile: dict,
    gathered_info: dict
) -> str:

    recommendation = f"""
Student ID:
{risk_profile['student_id']}

Risk Band:
{risk_profile['risk_band']}

Recommended Action:
Schedule mentor follow-up.

Additional Information:
{gathered_info}
"""

    return recommendation