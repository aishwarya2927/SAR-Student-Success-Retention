# Student Agent & Student Dashboard (Person D)

## Overview

The Student Agent is the student-facing component of the Student Success & Retention Platform.

It provides personalized academic guidance by combining:
- Risk Engine predictions
- SHAP explainability
- Gemini AI reasoning
- Career guidance
- Support recommendations


---

## Workflow

Student enters query

        ↓

Intent Router

        ↓

Classifies request:
- Risk Explanation
- Improvement Roadmap
- Career Guidance
- Support Query

        ↓

Risk Engine API

        ↓

Student Risk Profile:
- Risk Score
- Risk Band
- Top SHAP Factors

        ↓

Gemini Student Agent

        ↓

Personalized Output:
- Four-week improvement roadmap
- Risk explanation
- Career guidance
- Support resources


---

## Features Completed

### Risk Explanation Agent

- Uses Risk Engine output
- Displays risk score
- Shows SHAP factor contribution
- Explains why student is at risk


### Roadmap Agent

Generates personalized 4-week improvement roadmap containing:

- Weekly goals
- Action items
- Improvement tasks
- Risk reduction suggestions


### Career Guidance Agent

Provides:

- Career path suggestions
- Skill recommendations
- Learning direction


### Intent Router

Routes student questions automatically:

Student Query → Correct Agent


### Streamlit Student Dashboard

Includes:

- Risk score visualization
- SHAP charts
- Roadmap cards
- Career guidance cards
- Support section


---

## Integration

### Person A — Risk Engine

Consumes:

- student_id
- risk_score
- risk_band
- top_factors


### Person B — Mentor Agent

Uses the same Risk Engine profile to maintain consistency between:

Faculty intervention flow

and

Student guidance flow


### Person C — Dashboard

Planned integration:

Student Dashboard
        ↓
Student Agent
        ↓
Roadmap / Career / Support Output


---

## Current Status

Completed:

✅ Student Roadmap Agent  
✅ Career Guidance Module  
✅ Intent Router  
✅ Gemini Integration  
✅ Risk Engine Integration  
✅ Streamlit UI  
✅ SHAP Explanation UI  


