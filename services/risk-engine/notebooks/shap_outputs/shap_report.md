# SHAP Explainability Report
## Academic Risk Band Prediction — Student Success & Retention Platform
 
*Generated: 2026-07-03 11:08 UTC*
 
---
 
## 1. Purpose
 
This report documents the SHAP (SHapley Additive exPlanations) analysis applied to
the trained XGBoost academic risk prediction model.
 
The goal is to make the model's predictions **interpretable and actionable** for:
- Faculty mentors reviewing at-risk student cases
- The Mentor Agent (Person B) generating intervention recommendations
- The Faculty Dashboard (Person C) displaying per-student explanations
- Institutional leadership evaluating model fairness and bias
 
---
 
## 2. Dataset
 
| Property | Value |
| --- | --- |
| Total students | 30,000 |
| Features used | 58 (after leakage removal) |
| Target variable | `academic_risk_band` |
| Classes | Critical / High / Medium / Low |
| Class distribution | Low ≈ 81% · Medium ≈ 12.5% · High ≈ 5.6% · Critical ≈ 0.55% |
 
---
 
## 3. Model Used
 
| Property | Value |
| --- | --- |
| Algorithm | XGBoost (`XGBClassifier`) |
| Objective | `multi:softprob` |
| Imbalance handling | `compute_sample_weight("balanced")` |
| Explainability | `shap.TreeExplainer` (exact Shapley values) |
| Pipeline | sklearn `Pipeline` (OrdinalEncoder → XGBClassifier) |
 
The model was trained in `model_v2_xgboost_final.py` and loaded here from
`models/xgboost_academic_risk_pipeline.pkl` — **no retraining was performed**.
 
---
 
## 4. Top 20 Features by SHAP Importance
 
Mean absolute SHAP value aggregated across all 30,000 students and all 4 classes.
 
| Rank | Feature | Mean |SHAP| | % of Total |
| --- | --- | --- | --- |
| 1 | `backlog_count` | 3.671915 | 60.05% |
| 2 | `stress_score` | 0.275805 | 4.51% |
| 3 | `attendance_percentage` | 0.209621 | 3.43% |
| 4 | `internal_marks_avg` | 0.192421 | 3.15% |
| 5 | `assignment_submission_rate` | 0.152584 | 2.50% |
| 6 | `course_completion_rate` | 0.143660 | 2.35% |
| 7 | `financial_stress_score` | 0.136717 | 2.24% |
| 8 | `time_management_score` | 0.093537 | 1.53% |
| 9 | `mentor_feedback_score` | 0.070937 | 1.16% |
| 10 | `video_watch_percentage` | 0.062251 | 1.02% |
| 11 | `cgpa` | 0.054791 | 0.90% |
| 12 | `semester_gpa` | 0.053669 | 0.88% |
| 13 | `cybersecurity_score` | 0.047638 | 0.78% |
| 14 | `mock_interview_score` | 0.047069 | 0.77% |
| 15 | `aptitude_score` | 0.045010 | 0.74% |
| 16 | `motivation_score` | 0.041022 | 0.67% |
| 17 | `lab_performance_score` | 0.040644 | 0.66% |
| 18 | `lms_login_frequency` | 0.036098 | 0.59% |
| 19 | `leadership_score` | 0.033461 | 0.55% |
| 20 | `consistency_score` | 0.032164 | 0.53% |
 
---
 
## 5. Most Important Features (Summary)
 
1. **`backlog_count`** — mean |SHAP| = 3.6719
2. **`stress_score`** — mean |SHAP| = 0.2758
3. **`attendance_percentage`** — mean |SHAP| = 0.2096
4. **`internal_marks_avg`** — mean |SHAP| = 0.1924
5. **`assignment_submission_rate`** — mean |SHAP| = 0.1526
 
---
 
## 6. How SHAP Works
 
SHAP assigns each feature a **contribution score** for every individual prediction.
 
- A **positive SHAP value** pushes the model toward predicting the student is in
  that risk class.
- A **negative SHAP value** pushes the model away from that class.
- The scores are mathematically guaranteed to sum to the difference between the
  model's output and the average output (the baseline / expected value).
 
`shap.TreeExplainer` computes **exact** Shapley values by traversing the XGBoost
tree structure — no sampling or approximation is used.
 
For a multiclass model with 4 classes, each prediction produces 4 sets of SHAP
values (one per class). The class with the highest predicted probability determines
the final `risk_band` label, and the corresponding SHAP set is used to explain it.
 
---
 
## 7. Business Interpretation
 
| SHAP Value | Meaning |
| --- | --- |
| Large positive | Feature strongly increases predicted risk |
| Large negative | Feature strongly decreases predicted risk |
| Near zero | Feature had little influence on this prediction |
 
**Example interpretation:**  
A student predicted as *High* risk with SHAP values of  
`attendance_percentage: −0.72`, `backlog_count: +0.65`, `fee_delay_days: +0.48`  
should be read as:  
*"Low attendance is the strongest signal. The student's backlog count and fee payment
delays are both worsening the prediction. Good performance elsewhere is not enough
to offset these risk factors."*
 
---
 
## 8. How the Dashboard Team (Person C) Can Use SHAP
 
The artefacts produced by this notebook enable the Faculty Dashboard to:
 
1. **Student detail view** — Load `shap_values.pkl` and display the top-3 SHAP bars
   per student alongside the risk band badge.
2. **Sortable student list** — Sort students by any SHAP feature contribution to
   identify cohort-level patterns (e.g., "all High-risk students with high fee delay").
3. **Audit trail** — Store `student_explanation.json` in the `mentoring_workflow`
   table so mentors can see which factors triggered the flag at the time of review.
 
**Integration pattern:**
```python
import joblib, numpy as np
shap_bundle = joblib.load("shap_outputs/shap_values.pkl")
shap_vals   = shap_bundle["shap_values"]        # list[ndarray]
feat_names  = shap_bundle["feature_names"]      # list[str]
 
# Top 3 factors for student at row index i, predicted class c
student_shap = shap_vals[c][i]
top3_idx = np.argsort(np.abs(student_shap))[::-1][:3]
top3 = [(feat_names[j], round(float(student_shap[j]), 4)) for j in top3_idx]
```
 
---
 
## 9. How the Mentor Agent (Person B) Can Use SHAP
 
Person B's `draft_intervention_plan` tool should receive the `top_factors` list from
`student_explanation.json`.  The branching logic can use SHAP values to:
 
- **Route by dominant factor**: If the top SHAP feature involves `fee_delay_days`
  or `financial_stress_score`, trigger `check_scholarship_eligibility` first.
- **Personalise the plan**: Reference the actual SHAP-identified factors in the
  generated text rather than generic advice.
- **Threshold escalation**: If any SHAP value for the Critical class exceeds 0.3,
  flag for immediate escalation regardless of the predicted band.
 
**The contract field `top_factors` already uses SHAP values:**
```json
{
  "student_id": "S1001",
  "risk_band": "High",
  "top_factors": [
    {"feature": "attendance_drop",  "value": -18, "shap_contribution": 0.31},
    {"feature": "backlog_count",    "value": 2,   "shap_contribution": 0.24},
    {"feature": "fee_delay",        "value": 45,  "shap_contribution": 0.19}
  ]
}
```
 
---
 
## 10. Limitations
 
| Limitation | Detail |
| --- | --- |
| Synthetic dataset | The model was trained on generated data. SHAP rankings reflect synthetic patterns and must be validated against real institutional data before deployment. |
| Class imbalance | Critical class (0.55 %) may have less reliable SHAP explanations due to low sample count. |
| SHAP ≠ causation | A high SHAP value for `backlog_count` means the model uses it heavily — not that reducing backlogs will guarantee lower risk. |
| Static explanations | `shap_values.pkl` reflects the dataset at training time. Re-run this notebook when the model is retrained. |
| Ordinal encoding | Categorical features are ordinally encoded before SHAP sees them. Feature values in waterfall plots are encoded integers, not original labels. |
 
---
 
*End of report — 2026-07-03 11:08 UTC*
