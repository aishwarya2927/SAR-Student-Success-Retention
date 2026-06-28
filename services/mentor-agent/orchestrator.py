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


def run_agent(student_id: str):

    tools_called = []

    risk_profile = get_risk_profile(student_id)

    tools_called.append("get_risk_profile")

    if risk_profile["risk_band"] == "low":

        return {
            "recommendation_text":
            "No action needed.",

            "tools_called":
            tools_called,

            "status":
            "pending_approval"
        }

    factors = [
        factor["feature"]
        for factor
        in risk_profile["top_factors"]
    ]

    gathered_info = {}

    if "fee_delay" in factors:

        gathered_info["scholarship"] = (
            check_scholarship_eligibility(
                student_id,
                risk_profile["fee_delay_days"]
            )
        )

        tools_called.append(
            "check_scholarship_eligibility"
        )

    resource_query = None

    if "backlog_count" in factors:
      resource_query = "support for students with academic backlogs"

    elif "gpa_trend" in factors:
      resource_query = "study skills and tutoring for low GPA"

    elif "attendance_drop" in factors:
        resource_query = "attendance counselling and mentoring"

    if resource_query:

        gathered_info["resources"] = (
            search_support_resources(resource_query)
        )

        tools_called.append(
            "search_support_resources"
        )

    recommendation = (
            draft_intervention_plan(
                risk_profile,
                gathered_info
            )
        )

    tools_called.append(
        "draft_intervention_plan"
    )

    return {
    **recommendation,
    "tools_called": tools_called,
    "status": "pending_approval"
}