# ASRA: Student Success & Retention Platform (SAR)

ASRA is an end-to-end, decoupled multi-service educational decision-support and student mentoring platform. It is designed to predict academic dropouts, explain individual student risk drivers, automate academic verification tasks using Multimodal AI, and provide a stateful conversational coaching interface with custom career roadmaps.

## 🔗 Live Deployment
*   **Production Deployment URL**: *[Deploy Link - To be updated]*

---

## 🏗️ System Architecture

The platform is designed as a decoupled microservices architecture comprising four core services integrated with PostgreSQL, vector storage, and external AI/email API gateways.

```mermaid
flowchart TB
    subgraph Client_Layer["Client Layer (Web Interfaces)"]
        FacultyUI["Faculty Dashboard UI<br>(Streamlit / CSS Glassmorphism)"]
        StudentUI["Student Portal UI<br>(Streamlit Chat & Roadmap)"]
    end

    subgraph Service_Layer["Service Layer (FastAPI Microservices)"]
        DashboardAPI["Faculty Dashboard Backend<br>(services/dashboard)"]
        MentorAgentAPI["Mentor & Student Agent API<br>(services/mentor-agent)"]
        RiskEngineAPI["ML Risk Engine API<br>(services/risk-engine)"]
        RoadmapAPI["Roadmap Generation API<br>(services/roadmap-agent)"]
    end

    subgraph Data_Storage_Layer["Data & Knowledge Layer"]
        PostgresDB[("PostgreSQL Database<br>(Shared Students, Risks & Interventions)")]
        ChromaDB[("ChromaDB Vector Store<br>(Gemini Embeddings: Policies & Placement Guides)")]
    end

    subgraph External_Integrations["External Integrations & Fallbacks"]
        GeminiAPI["Google Gemini API<br>(API Key Pool with Rotation Wrapper)"]
        EmailCascade["Cascading Email Client<br>(Resend -> SendGrid -> Brevo -> SMTP)"]
    end

    %% Client Interactions
    FacultyUI <──> DashboardAPI
    StudentUI <──> RoadmapAPI

    %% Service to Service communication
    DashboardAPI <──> MentorAgentAPI
    RoadmapAPI <──> MentorAgentAPI
    MentorAgentAPI <──> RiskEngineAPI

    %% Service to Database
    DashboardAPI <──> PostgresDB
    MentorAgentAPI <──> PostgresDB
    RoadmapAPI <──> PostgresDB
    MentorAgentAPI <──> ChromaDB

    %% External APIs
    MentorAgentAPI <──> GeminiAPI
    RoadmapAPI <──> GeminiAPI
    MentorAgentAPI ──> EmailCascade
```

---

## 🌟 Key Features

### 1. Machine Learning Risk Engine
*   **Predictive Model**: Production-grade **XGBoost Classifier** (95.25% validation accuracy, F1-score of 0.78 for minority Critical class) trained on 30,000 student records.
*   **Target Leakage Prevention**: Programmatically sanitizes data before ingestion (excludes features like `academic_risk_score` and `placement_probability`).
*   **SHAP Explainability**: Dynamic feature-driver analysis utilizing `shap.TreeExplainer` to extract top local risk indicators (e.g. `backlog_count`, `stress_score`) per student.

### 2. LangGraph Mentor Agent Workflow
*   **Stateful Decision Tree**: Standardized Node structures (Risk node $\rightarrow$ Scholarship node $\rightarrow$ Support Resource node $\rightarrow$ Draft Intervention node).
*   **Resource Retrieval (RAG)**: Connects queries to a local ChromaDB store embedded with Gemini representations of student policies.
*   **Human-in-the-Loop**: Generates draft intervention plans that require advisor approval on the dashboard before outreach triggers.

### 3. Automated Verification via Gemini Vision OCR
*   **Resume Audit (`/verify-resume`)**: Extracts and evaluates CV content structure, scores layouts, checks off placement tasks, and logs advisory remarks automatically.
*   **Certification Verifier (`/verify-certificate`)**: Validates certificates (authenticating recipient names, issuers, and subjects) to automatically check off student roadmap tasks.

### 4. Interactive Student Chatbot & Mock Interviews
*   **Placement Coach**: Stateful 3-turn sequential mock placement interview engine customized to specific target companies (e.g. TCS, Goldman Sachs).
*   **Automated Evaluation**: Grades student responses, offering a comprehensive performance and review report.

### 5. Interactive Web Portals
*   **Faculty Dashboard (Streamlit)**: Multipage dashboard tracking student pipelines, displaying SHAP waterfalls, managing approvals, and viewing year/comparison trends.
*   **Student Roadmap Portal (Streamlit)**: Personal onboarding UI displaying custom roadmaps, checklists, certificate uploads, and the conversational mentoring chatbot.

---

## 📂 Project Repository Structure

```
├── datasets/                 # Datasets for model training and bulk imports
├── docs/                     # Documentation assets and templates (locally git-ignored)
├── research/                 # Model evaluation and playground assets
├── shared/                   # Shared utility classes and structures
└── services/                 # Decoupled backend and frontend services
    ├── risk-engine/          # XGBoost FastAPI predictor API & model pipelines
    ├── mentor-agent/         # LangGraph workflows, database interfaces, & OCR endpoints
    ├── dashboard/            # Faculty dashboard Streamlit frontend and REST API
    └── roadmap-agent/        # Student career roadmap portal Streamlit client
```

---

## ⚙️ Configuration & Environment Setup

Each service reads variables from local environment keys. Create a `.env` file inside each directory under `services/` as specified:

### 1. Mentor Agent Setup (`services/mentor-agent/.env`)
```bash
# Gemini API Key Pool for automatic rotation
GEMINI_API_KEY=AQ.your_primary_key
GEMINI_API_KEY_PLACEMENT=AQ.your_placement_key
GEMINI_API_KEY_3=AQ.your_fallback_key_3
GEMINI_API_KEY_4=AQ.your_fallback_key_4

# Database Connection (PostgreSQL or local fallback)
DATABASE_URL=postgresql://user:password@host:port/database

# Cascading Email Client Configurations
BREVO_API_KEY=xkeysib-your_brevo_key
SENDER_EMAIL=successpath-alerts@spit.ac.in

# SMTP Fallback
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_16_char_app_password
```

### 2. Student Roadmap Setup (`services/roadmap-agent/.env`)
```bash
# Gemini API Key
GEMINI_API_KEY=AQ.your_roadmap_key

# Database Connection
DATABASE_URL=postgresql://user:password@host:port/database
```

---

## 🚀 Running locally

### Prerequisites
*   Python 3.10+
*   PostgreSQL Database instance

### 1. Ingest Data & Vector Store
1.  Initialize database tables and import initial dataset:
    ```bash
    cd services/mentor-agent
    python scratch/import_college_roster.py
    ```
2.  Ingest knowledge policies into the vector store:
    ```bash
    python vector_store/ingest.py
    ```

### 2. Start the APIs
*   **Risk Engine API**:
    ```bash
    cd services/risk-engine/api
    uvicorn main:app --port 8000 --reload
    ```
*   **Mentor Agent Backend**:
    ```bash
    cd services/mentor-agent
    uvicorn app:app --port 8001 --reload
    ```

### 3. Launch Frontends
*   **Faculty Dashboard Streamlit**:
    ```bash
    cd services/dashboard
    streamlit run app.py
    ```
*   **Student Roadmap Streamlit**:
    ```bash
    cd roadmap-agent  # (Or run inside services/roadmap-agent)
    streamlit run app.py
    ```

---

## 🛡️ Reliability Engineering
*   **Gemini Client Rotation Pool**: Handles `429 Too Many Requests` API exceptions by placing exhausted keys on a 2-minute cooldown and rotating requests.
*   **Cascading Email Delivery**: Email client automatically cascades calls across **Resend $\rightarrow$ SendGrid $\rightarrow$ Brevo $\rightarrow$ SMTP**.
*   **Non-Blocking UI Threads**: Offloads outreach email generation to separate background threads to prevent UI freezes.
