from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

student_target_companies = {}

class TargetCompanyRequest(BaseModel):
    student_id: str
    target_companies: list[str]

@app.post("/student-target-companies")
def save_target_companies(request: TargetCompanyRequest):
    student_target_companies[request.student_id] = request.target_companies
    return {
        "message": "Target companies saved successfully",
        "student_id": request.student_id,
        "target_companies": request.target_companies
    }

@app.get("/student-target-companies/{student_id}")
def get_target_companies(student_id: str):
    return {
        "student_id": student_id,
        "target_companies": student_target_companies.get(student_id, [])
    }
