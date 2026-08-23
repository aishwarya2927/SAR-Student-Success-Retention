# 🎓 SAR - Student Success & Retention Platform

An Agentic AI powered Student Academic Success & Retention System designed to identify student risk, generate personalized improvement roadmaps, provide mentorship support, and enable faculty-driven intervention planning.

The platform uses multiple AI agents working together to improve student outcomes through early risk detection, personalized academic guidance, and continuous support.

---

# 👩‍🎓 Person D – Student Roadmap Agent

## 🚀 Deployment Link

🔗 Student Roadmap Agent Dashboard:

https://sar-student-success-retention-lnxakgsa3fuxwvyomb7f2d.streamlit.app/

---

## 📌 Module Overview

The **Student Roadmap Agent** is the student-facing AI assistant of the Student Success & Retention Platform.

It allows students to:
- Understand their academic risk factors
- Receive personalized improvement plans
- Get career-oriented guidance
- View faculty-approved intervention recommendations

The agent provides personalized support by analyzing student information and generating actionable academic improvement strategies using Agentic AI.

---

# ✨ Features

### 🎯 Personalized Academic Roadmap Generation
- Generates customized 4-week improvement roadmap
- Provides weekly academic action plans
- Suggests practical improvement steps

### 📊 Risk Explanation Support
- Explains academic risk factors
- Identifies possible causes affecting performance
- Provides improvement suggestions

### 🚀 Career Guidance Module
- Generates career suggestions based on student interest
- Provides skill improvement recommendations
- Helps students plan their learning path

### 🧑‍🏫 Faculty Intervention Integration
- Fetches faculty-approved support plans
- Displays intervention status
- Shows approved academic recommendations

### 💻 Student Dashboard
Built using Streamlit with:
- Student profile input
- GPA information
- Career interest selection
- AI query interface
- Roadmap visualization
- JSON roadmap download option

---

# 🧠 Agent Workflow

```text
Student Query
      |
      ↓
Intent Router Agent
      |
      ↓
Classifies User Intent
      |
      ↓
Student Roadmap Agent
      |
      ↓
Generates Personalized Response
      |
      ↓
Fetch Faculty Approved Intervention API
      |
      ↓
Streamlit Student Dashboard
```

---

# 🔗 Integrated APIs

## Faculty Approved Intervention API

Used to retrieve faculty-reviewed intervention plans.

Endpoint:

```text
https://sar-student-success-retention-3kvj.onrender.com/intervention/{student_id}
```

Example:

```text
https://sar-student-success-retention-3kvj.onrender.com/intervention/STU202600058
```

---

# 🧪 Test Details

## Test Student ID

```text
STU202600058
```

---

# 📝 Example Queries

Students can interact with the AI agent using natural language.

## Academic Roadmap

```text
Create my 4 week improvement roadmap
```

```text
Prepare an academic improvement plan for me
```

```text
How should I improve my GPA?
```

---

## Risk Explanation

```text
Why is my academic risk high?
```

```text
Explain my academic risk factors
```

```text
What factors are affecting my performance?
```

---

## Support Recommendation

```text
Give me support recommendations
```

```text
Suggest actions to improve my academic progress
```

```text
How can I reduce my academic risk?
```

---

## Career Guidance

```text
Suggest a career roadmap for AI
```

```text
What skills should I learn for my career goal?
```

```text
Create a learning path according to my interest
```

---

## Faculty Intervention

```text
Show my faculty approved intervention plan
```

```text
What intervention has faculty suggested for me?
```

---

# 🛠️ Technologies Used

- Python
- Streamlit
- Gemini API
- Agentic AI Architecture
- REST API Integration
- Requests Library
- Pandas
- Plotly
- Python-dotenv

---

# 📂 Module Structure

```text
services/
│
└── roadmap-agent/
    │
    ├── agents/
    │   ├── intent_router.py
    │   └── roadmap_agent.py
    │
    ├── modules/
    │
    ├── utils/
    │
    ├── chat_app.py
    │
    ├── requirements.txt
    │
    └── README.md
```

---

# ⚙️ How To Run Locally

Install dependencies:

```bash
pip install -r requirements.txt
```

Run Streamlit application:

```bash
streamlit run chat_app.py
```

---

# 🌐 Deployment

Platform:

```text
Streamlit Cloud
```

Main file:

```text
services/roadmap-agent/chat_app.py
```

Environment Variables:

```text
GOOGLE_API_KEY
```

---

# ✅ Completed Work

- ✔ Student Roadmap Agent Development
- ✔ Intent Classification Agent
- ✔ Personalized Roadmap Generation
- ✔ Career Guidance Support
- ✔ Student Dashboard UI
- ✔ Faculty Intervention API Integration
- ✔ Streamlit Deployment

---

# 🎯 Future Enhancements

- More student analytics visualization
- Multi-semester roadmap generation
- Real-time faculty feedback loop
- Advanced recommendation engine

---

## Developed as part of Student Academic Success & Retention Agentic AI System