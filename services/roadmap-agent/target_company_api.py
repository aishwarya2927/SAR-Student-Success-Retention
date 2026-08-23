from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(
    title="Student Roadmap Agent API"
)

# temporary storage
student_companies = {}


class TargetCompanyRequest(BaseModel):
    student_id: str
    target_companies: list[str]


@app.get("/")
def home():
    return {
        "message": "Roadmap Agent API Running"
    }


@app.post("/student-target-companies")
def save_target_companies(data: TargetCompanyRequest):

    student_companies[data.student_id] = data.target_companies

    return {
        "status": "success",
        "student_id": data.student_id,
        "target_companies": data.target_companies
    }


@app.get("/student-target-companies/{student_id}")
def get_target_companies(student_id: str):

    return {
        "student_id": student_id,
        "target_companies": student_companies.get(student_id, [])
    }