from tools.get_risk_profile import get_risk_profile
from tools.scholarship_tool import (
    check_scholarship_eligibility
)
from tools.search_support_resources import (
    search_support_resources
)
from tools.intervention_tool import (
    draft_intervention_plan
)


def run_agent(student_id: str) -> dict:
    """
    Runs the Mentor Agent workflow and returns a structured
    intervention recommendation.
    """

    tools_called = []

    # Step 1: Fetch risk profile
    risk_profile = get_risk_profile(student_id)
    tools_called.append("get_risk_profile")

    # Step 2: Exit early for low-risk students
    if risk_profile["risk_band"].lower() == "low":

        return {
            "student_id": risk_profile["student_id"],
            "risk_band": risk_profile["risk_band"],
            "prediction_confidence": risk_profile["risk_score"],
            "student_summary": "Student is currently classified as low risk. No intervention is required.",
            "recommended_actions": [],
            "priority_level": "Low",
            "follow_up_plan": "Continue routine monitoring.",
            "tools_called": tools_called,
            "status": "pending_approval"
        }

    gathered_info = {}

    # Step 3: Process top risk factors (when available)
    factors = [
        factor["feature"]
        for factor in risk_profile.get("top_factors", [])
    ]

    # Scholarship Tool
    if "fee_delay_days" in risk_profile:

        gathered_info["scholarship"] = (
            check_scholarship_eligibility(
                student_id,
                risk_profile["fee_delay_days"]
            )
        )

        tools_called.append(
            "check_scholarship_eligibility"
        )

    # Resource Retrieval
    for factor in factors:

        resources = search_support_resources(factor)

        if resources:

            gathered_info["resources"] = resources

            tools_called.append(
                "search_support_resources"
            )

            break

    # Step 4: Generate intervention plan
    recommendation = draft_intervention_plan(
        risk_profile,
        gathered_info
    )

    tools_called.append(
        "draft_intervention_plan"
    )

    return {
        "student_id": risk_profile["student_id"],
        "risk_band": risk_profile["risk_band"],
        "prediction_confidence": risk_profile["risk_score"],
        **recommendation,
        "tools_called": tools_called,
        "status": "pending_approval"
    }


if __name__ == "__main__":

    result = run_agent("STU202600033")

    print(result)