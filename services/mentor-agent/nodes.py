import logging

logger = logging.getLogger(__name__)

from state import MentorState

from tools.get_risk_profile import get_risk_profile
from tools.scholarship_tool import check_scholarship_eligibility
from tools.search_support_resources import search_support_resources
from tools.intervention_tool import draft_intervention_plan


def risk_node(state: MentorState) -> MentorState:
    """
    Fetch the student's risk profile from the Risk Engine.
    """
    logger.info("Running Risk Node")  

    risk_profile = get_risk_profile(state["student_id"])

    state["risk_profile"] = risk_profile

    state["tools_called"].append("get_risk_profile")

    return state

def risk_router(state: MentorState) -> str:
    """
    Route the workflow based on the student's risk band.
    """

    risk_band = state["risk_profile"]["risk_band"].lower()

    if risk_band == "low":
        return "low_risk"

    return "scholarship"

def scholarship_node(state: MentorState) -> MentorState:
    """
    Check scholarship eligibility if fee delay is one of the
    student's top risk factors.
    """
    logger.info("Running Scholarship Node")

    risk_profile = state["risk_profile"]

    factors = [
        factor["feature"]
        for factor in risk_profile.get("top_factors", [])
    ]

    if "fee_delay_days" in risk_profile:

      state["gathered_info"]["scholarship"] = (
          check_scholarship_eligibility(
              state["student_id"],
              risk_profile["fee_delay_days"]
          )
      )

      state["tools_called"].append(
          "check_scholarship_eligibility"
      )

    return state

def resource_node(state: MentorState) -> MentorState:
    """
    Retrieve relevant university support resources based on
    the student's top risk factors.
    """
    logger.info("Running Resource Node")

    risk_profile = state["risk_profile"]

    factors = [
        factor["feature"]
        for factor in risk_profile.get("top_factors", [])
    ]

    for factor in factors:

        resources = search_support_resources(factor)

        if resources:

            state["gathered_info"]["resources"] = resources

            state["tools_called"].append(
                "search_support_resources"
            )

            break

    return state

def intervention_node(state: MentorState) -> MentorState:
    """
    Generate the intervention plan using Gemini.
    """
    logger.info("Running Intervention Node")

    recommendation = draft_intervention_plan(
        state["risk_profile"],
        state["gathered_info"]
    )

    state["tools_called"].append(
        "draft_intervention_plan"
    )

    state["status"] = "pending_approval"

    risk_profile = state["risk_profile"]

    state["response"] = {
        "student_id": risk_profile["student_id"],
        "risk_band": risk_profile["risk_band"],
        "prediction_confidence": risk_profile["risk_score"],
        **recommendation,
        "tools_called": state["tools_called"],
        "status": state["status"]
    }

    return state

def low_risk_node(state: MentorState) -> MentorState:
    """
    Create the response for low-risk students.
    """
    logger.info("Running Low Risk Node")

    risk_profile = state["risk_profile"]

    recommendation = {
        "student_summary":
        "Student is currently classified as low risk. No intervention is required.",

        "recommended_actions": [],

        "priority_level": "Low",

        "follow_up_plan":
        "Continue routine monitoring."
    }

    state["status"] = "pending_approval"

    state["response"] = {
        "student_id": risk_profile["student_id"],
        "risk_band": risk_profile["risk_band"],
        "prediction_confidence": risk_profile["risk_score"],
        **recommendation,
        "tools_called": state["tools_called"],
        "status": state["status"]
    }

    return state