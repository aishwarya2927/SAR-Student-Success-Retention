# 🧠 ASRA Risk Prediction Engine Microservice

This directory houses the core predictive tier of the Agentic Student Retention Assistant (ASRA) ecosystem. It operates as a high-performance, stateless FastAPI web service designed to execute real-time student attrition and placement readiness risk classifications.

---

## 🛠️ Microservice Architecture & Design Choices

The engine is decoupled from the user interfaces and orchestration frameworks, communicating strictly via a versioned REST API. This isolation ensures that the machine learning runtime can scale independently across containerized infrastructure without bottlenecking downstream conversational agents.

### Key Implementation Features:
* **Target Leakage Prevention:** To maintain complete mathematical and diagnostic validity, all identifier rows (`student_id`) and true validation labels (`academic_risk_band`, `dropout_risk_band`, `placement_risk_band`) are programmatically scrubbed from the feature tensor before inference.
* **Feature Vectorization:** String attributes (such as department or target tracks) are mapped into dense numeric fields using pre-trained, isolated standard Label Encoders.
* **Vectorized Matrix Inferences:** Tabular records are processed simultaneously utilizing multi-threaded Pandas vectorization arrays directly inside the internal XGBoost inference matrix rather than slow, resource-heavy row-by-row parsing loops.

---

## 🔬 Mathematical Formulation & Optimization Rationale

The predictive engine uses an extreme gradient-boosted tree framework (XGBoost) optimized via multi-class log-loss. 

In higher-education retention contexts, the cost of an error is highly asymmetric. A **False Negative** (failing to identify an endangered student who drops out or fails placement) represents a catastrophic institutional failure. Conversely, a **False Positive** (generating a minor alert for a stable student) incurs only a negligible operational review cost for a faculty advisor. 

To align with this design constraint, the decision boundaries are calibrated using custom probability tuning to prioritize **Sensitivity (Recall)**. At runtime, prediction margins are normalized into a discrete probability distribution across $K=4$ classes (Critical, High, Medium, Low) using a multi-class Softmax layer:

$$P(y = k \mid \mathbf{x}) = \frac{e^{z_k}}{\sum_{j=1}^{K} e^{z_j}}$$

Where $z_k$ represents the raw marginal score output for a given class $k$.

---

## 📊 Empirical Evaluation Metrics

Model performance was validated over a 30% held-out test split using an institutional tracking index of 30,000 comprehensive student records:

| Evaluation Metric | Measured Pipeline Value (%) |
| :--- | :--- |
| **Recall Priority (Sensitivity)** | 95.8% |
| **Classification Accuracy** | 94.6% |
| **Precision Score** | 92.1% |
| **F1-Measure** | 93.9% |

---

## 🛡️ Production Safety & Environment Pathing

To handle environment-agnostic deployment patterns seamlessly, the service implements a dynamic path inspection script within `config.py`. 

When moving from a deeply nested local development directory structure (e.g., Windows paths like `/services/risk-engine/notebooks/`) to a flat cloud-hosted container environment (e.g., Docker workspaces on Render located at `/app`), the service programmatically shifts its asset paths. This eliminates hardcoded path failures and prevents environment crashes:

```python
import os
from pathlib import Path

# Resolve current script location dynamically
HERE = Path(__file__).resolve().parent

# Programmatic verification for production workspace or flat local directory presence
if os.path.exists("/app") or (HERE / "xgboost_academic_risk_pipeline.pkl").exists():
    PROJECT_ROOT = HERE
    MODEL_PATH   = HERE / "xgboost_academic_risk_pipeline.pkl"
    ENCODER_PATH = HERE / "label_encoder_academic_risk.pkl"
    DATASET_PATH = HERE / "student_success_dataset_30000.csv"
else:
    # Fallback to local deep nested development directory frameworks
    PROJECT_ROOT = HERE.parents[1]
    NOTEBOOK_DIR = PROJECT_ROOT / "notebooks"
    MODEL_PATH   = NOTEBOOK_DIR / "xgboost_academic_risk_pipeline.pkl"
    ENCODER_PATH = NOTEBOOK_DIR / "label_encoder_academic_risk.pkl"
    DATASET_PATH = HERE.parents[2] / "datasets" / "student_success_dataset_30000.csv"


##📂 Directory Structure
    services/risk-engine/
├── api/
│   ├── config.py                      # Dynamic path mapping utility
│   ├── main.py                        # FastAPI microservice routes
│   ├── predictor.py                   # XGBoost inference matrix setup
│   ├── xgboost_academic_risk_pipeline.pkl
│   └── label_encoder_academic_risk.pkl
├── notebooks/                         # Exploratory training logs & SHAP analyses
└── README.md                          # This documentation file

⚡ Setup & Execution Guide
1. Installation
Navigate to your API sub-directory and install the baseline requirements:

Bash
cd api
pip install -r requirements.txt
2. Launching the Microservice
Initialize the ASGI web server engine:

Bash
uvicorn main:app --reload --port 8000
Once initialized, the microservice hosts interactive OpenAPI documentation. You can test routes, inspect the data contract schemas, and review inference parameters live by navigating your browser to: http://localhost:8000/docs.