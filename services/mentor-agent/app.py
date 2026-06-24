from fastapi import FastAPI
from orchestrator import run_agent

app = FastAPI()


@app.post("/generate-intervention")
def generate_intervention(
    data: dict
):

    student_id = data["student_id"]

    return run_agent(student_id)