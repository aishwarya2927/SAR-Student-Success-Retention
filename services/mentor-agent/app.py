from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from orchestrator import run_agent


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
    Generates a personalized intervention plan for a student.
    """

    try:

        return run_agent(data.student_id)

    except HTTPException:
        raise

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Mentor Agent Error: {str(e)}"
        )