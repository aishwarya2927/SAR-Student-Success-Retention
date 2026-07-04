from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from graph import graph

import logging

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="Mentor Agent API",
    version="1.0.0",
    description="AI Mentor Agent for Student Success & Retention"
)


class StudentRequest(BaseModel):
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