# Mentor Agent (Person B)

## Student Success & Retention Platform

The Mentor Agent is an AI-powered decision support system designed to assist faculty in identifying and supporting at-risk students. It consumes predictions from the Risk Engine, retrieves relevant institutional support resources, evaluates scholarship eligibility, and generates personalized intervention plans using Google's Gemini LLM.

Unlike a traditional chatbot, the Mentor Agent follows a **LangGraph-based workflow**, allowing modular execution, conditional routing, and future extensibility.

---

# Objective

The objective of the Mentor Agent is to help faculty make informed intervention decisions rather than replacing human judgment.

The generated intervention plans are marked as **Pending Approval** and are intended to be reviewed by faculty before any action is taken.

---

# Overall Workflow

```text
                    Student ID
                         │
                         ▼
                  Risk Engine API
                         │
                         ▼
                Student Risk Profile
                         │
                         ▼
                 LangGraph Workflow
                         │
             ┌───────────┴────────────┐
             ▼                        ▼
     Low Risk Student          Medium / High Risk
             │                        │
             ▼                        ▼
      Monitoring Response     Scholarship Check
                                      │
                                      ▼
                          Support Resource Retrieval
                                      │
                                      ▼
                       Gemini Intervention Planner
                                      │
                                      ▼
                         Structured Intervention
                                      │
                                      ▼
                          Pending Faculty Approval
```

---

# LangGraph Workflow

The Mentor Agent is implemented using LangGraph.

### Nodes

### 1. Risk Node

- Calls the Risk Engine API.
- Retrieves:
  - Risk Band
  - Prediction Confidence
  - Top Risk Factors
  - Fee Delay Days

---

### 2. Risk Router

Routes the workflow.

- Low Risk → Low Risk Node
- Medium / High Risk → Scholarship Node

---

### 3. Low Risk Node

Returns a monitoring recommendation.

No LLM or RAG is invoked.

---

### 4. Scholarship Node

Checks scholarship eligibility using

```
fee_delay_days
```

returned by the Risk Engine.

---

### 5. Resource Node

Retrieves semantically relevant university support resources using

- ChromaDB
- HuggingFace Embeddings

---

### 6. Intervention Node

Uses Gemini to generate a structured intervention plan using

- Risk Profile
- Scholarship Information
- Retrieved Support Resources

---

# Folder Structure

```text
mentor-agent/

app.py

graph.py

nodes.py

state.py

tools/
    get_risk_profile.py
    intervention_tool.py
    scholarship_tool.py
    search_support_resources.py

vector_store/
    ingest.py
    search.py
    chroma_db/

resources/

llm/

requirements.txt

README.md
```

---

# Technologies Used

- Python
- FastAPI
- LangGraph
- LangChain
- Google Gemini
- ChromaDB
- HuggingFace Embeddings
- HTTPX
- Pydantic

---

# Mentor Agent Tools

## Risk Profile Tool

Retrieves student predictions from the Risk Engine API.

---

## Scholarship Eligibility Tool

Determines whether a student should be considered for financial assistance based on

```
fee_delay_days
```

---

## Support Resource Retrieval Tool

Uses semantic search to retrieve relevant university support resources based on the student's top risk factors.

---

## Intervention Planning Tool

Uses Gemini to generate structured intervention recommendations.

---

# Knowledge Base (RAG)

The Mentor Agent uses Retrieval-Augmented Generation (RAG) to ground intervention recommendations using institutional support resources.

Instead of relying solely on the LLM, relevant documents are retrieved from a ChromaDB vector database before generating recommendations.

Current knowledge base includes:

- Attendance Policy
- Career Services
- Counselling Support
- Exam Support
- Financial Assistance
- Peer Mentoring
- Academic Probation
- Scholarships
- Study Skills
- Tutoring Services

---

# Sources Used

The knowledge base is built primarily using publicly available resources from Indian educational institutions.

| Resource Document | Primary Reference |
|------------------|------------------|
| attendance_policy.md | SPIT Academic Rules & Examination Manual |
| probation.md | SPIT Academic Rules & Examination Manual |
| career_services.md | SPIT Placement Cell + IIT Delhi Office of Career Services |
| exam_support.md | SPIT Examination Resources + IIT Madras Student Wellbeing Centre |
| counselling.md | IIT Bombay Student Wellness Centre |
| study_skills.md | IIT Bombay Student Wellness Centre |
| tutoring.md | IIT Madras Student Wellbeing Centre |
| peer_mentoring.md | IIT Madras Student Wellbeing Centre |
| scholarship.md | National Scholarship Portal (Government of India) |
| financial_assistance.md | National Scholarship Portal + IIT Bombay Student Financial Support |

The documents are summarized and adapted into a consistent institutional knowledge base for use by the Mentor Agent.

---

# API

### Generate Intervention

```
POST /generate-intervention
```

Request

```json
{
    "student_id": "STU202600033"
}
```

Returns

- Student Summary
- Recommended Actions
- Priority Level
- Follow-up Plan
- Tool Execution History
- Approval Status

---

# Current Features

- LangGraph-based workflow orchestration
- Risk Engine API integration
- Conditional routing
- Scholarship Eligibility Tool
- Retrieval-Augmented Generation (RAG)
- ChromaDB vector search
- Gemini intervention planning
- Automatic Gemini retry mechanism
- Tool execution tracking
- Human approval workflow (Pending Approval)
- Swagger documentation
- Workflow logging

---

# Integration

## Person A

Consumes predictions from the Risk Engine.

---

## Person C

Faculty Dashboard calls

```
POST /generate-intervention
```

to retrieve intervention recommendations.

The Dashboard is responsible for storing recommendations and managing the approval workflow.

---

## Person D

The Student Agent may consume only faculty-approved interventions for personalized student guidance.

---

# Future Enhancements

- Persistent approval workflow
- Expanded institutional knowledge base
- Additional support tools
- Parallel LangGraph execution
- Multi-level faculty approval
- Analytics dashboard

---

# Author

Person B – Mentor Agent

Student Success & Retention Platform
Agentic AI Internship Project