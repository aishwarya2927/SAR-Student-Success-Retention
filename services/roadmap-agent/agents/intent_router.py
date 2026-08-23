from agents.roadmap_agent import get_llm


def classify_intent(question: str) -> str:
    llm = get_llm()

    prompt = f"""
You are an intent classification engine.

Your job is to classify the student's question into exactly ONE category.

Possible categories:

ROADMAP
CAREER
RISK
SUPPORT
RAG
UNKNOWN

Definitions:

ROADMAP
Questions about improving grades, attendance, backlog, study plans, academic improvement.

CAREER
Questions about internships, placements, resume, jobs, AI career, higher studies.

RISK
Questions asking why the student's risk score is high or what caused the prediction.

SUPPORT
Questions asking about scholarships, fee support, counselling, financial aid.

RAG
Questions asking about college policies, attendance rules, regulations, FAQs.

UNKNOWN
Anything unrelated.

Return ONLY the category.

Question:
{question}
"""

    response = llm.invoke(prompt)

    return response.content.strip().upper()