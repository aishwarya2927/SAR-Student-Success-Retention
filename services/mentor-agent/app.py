from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from graph import graph
from tools.get_risk_profile import get_risk_profile
from tools.get_target_companies import get_target_companies
from tools.search_company_resources import search_multiple_company_resources
from tools.placement_tool import draft_placement_plan

import logging

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="Mentor Agent API",
    version="1.0.0",
    description="AI Mentor Agent for Student Success & Retention"
)


class StudentRequest(BaseModel):
    student_id: str


class PlacementRequest(BaseModel):
    student_id: str


@app.get("/")
def root():
    """
    Root endpoint.
    """
    return {
        "service": "Mentor Agent API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health")
def health():
    """
    Health check endpoint.
    """
    return {
        "status": "healthy"
    }


@app.post("/generate-intervention")
def generate_intervention(data: StudentRequest):
    """
    Generates a personalized intervention plan using the LangGraph workflow.
    """
    try:
        state = {
            "student_id": data.student_id,
            "risk_profile": {},
            "gathered_info": {},
            "tools_called": [],
            "status": "",
            "response": {}
        }

        result = graph.invoke(state)

        return result["response"]

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Mentor Agent Error: {str(e)}"
        )


@app.post("/generate-placement-plan")
def generate_placement_plan(data: PlacementRequest):
    try:
        tools_called = []

        risk_profile = get_risk_profile(data.student_id)
        tools_called.append("get_risk_profile")

        target_companies = get_target_companies(data.student_id)
        tools_called.append("get_target_companies")

        company_data = {}
        if target_companies:
            company_data = search_multiple_company_resources(target_companies)
            tools_called.append("search_company_resources")

        placement_plan = draft_placement_plan(
            student_id=data.student_id,
            target_companies=target_companies,
            risk_band=risk_profile.get("risk_band"),
            risk_factors=risk_profile.get("top_factors", []),
            company_data=company_data,
            placement_profile=risk_profile.get("placement_profile", {})
        )
        tools_called.append("draft_placement_plan")

        if company_data:
            data_source = {
                company: ("curated" if info["is_curated"] else "general_knowledge")
                for company, info in company_data.items()
            }
        else:
            data_source = "general_readiness"

        return {
            "student_id": data.student_id,
            "target_companies": target_companies,
            "placement_plan": placement_plan,
            "placement_data_source": data_source,
            "tools_called": tools_called,
            "status": "pending_approval"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Placement Plan Error: {str(e)}")