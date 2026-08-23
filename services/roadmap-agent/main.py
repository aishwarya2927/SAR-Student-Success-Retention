from fastapi import FastAPI
from pydantic import BaseModel

from modules.roadmap_generator import generate_improvement_roadmap
from modules.career_module import generate_career_guidance

app = FastAPI(
    title="Student Roadmap Agent",
    version="1.0"
)


class StudentRequest(BaseModel):
    student_id: str
    gpa: float
    interest: str


@app.get("/")
def home():
    return {
        "message": "Student Roadmap Agent API is running."
    }


@app.post("/generate")
def generate(request: StudentRequest):

    roadmap_result = generate_improvement_roadmap(
        request.student_id
    )

    career = generate_career_guidance(
        request.gpa,
        request.interest
    )

    return {
        "student_id": request.student_id,
        "risk_profile": roadmap_result["risk_profile"],
        "roadmap": roadmap_result["roadmap"],
        "validation": roadmap_result["validation"],
        "career_guidance": career
    }