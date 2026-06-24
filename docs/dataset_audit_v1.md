# Dataset Audit Report V1

## Dataset Overview

* Dataset Name: Student Success and Retention Dataset
* Total Records: 30,000
* Total Features: 70
* Source: Synthetic Data Generator
* Audit Date: June 2026

## Structural Validation

### Checks Performed

* Row count validation
* Column count validation
* Data type validation
* Missing value validation

### Results

* Rows: 30,000
* Columns: 70
* Missing Values: 0
* Duplicate Student IDs: 0

Conclusion:
Dataset passed structural validation.

---

## Statistical Summary

### Key Variables

CGPA

* Mean: 8.31
* Std: 0.78

Attendance Percentage

* Mean: 86.88
* Std: 6.79

Backlog Count

* Mean: 0.56

Coding Score

* Mean: 68.92

Stress Score

* Mean: 48.24

Placement Probability

* Mean: 47.13

Conclusion:
Distributions appear realistic for an engineering student population.

---

## Correlation Validation

### Expected Relationships

Attendance → CGPA

* Correlation: 0.756

Backlogs → Placement Probability

* Correlation: -0.381

Stress → CGPA

* Correlation: -0.241

Stress → Placement Probability

* Correlation: -0.272

Coding Score → Career Readiness

* Correlation: 0.364

Conclusion:
Generated data preserves expected academic and behavioral relationships.

---

## Class Distribution Analysis

### Academic Risk Band

Low: 24,390
Medium: 3,754
High: 1,691
Critical: 165

### Dropout Risk Band

Low: 24,157
Medium: 5,042
High: 789
Critical: 12

### Placement Risk Band

Low: 7,667
Medium: 7,125
High: 14,012
Critical: 1,196

Observation:
Risk classes are imbalanced, which reflects realistic student populations.

---

## Data Leakage Analysis

### Academic Risk

Finding:
academic_risk_score directly determines academic_risk_band.

Action:
academic_risk_score removed from model training.

### Placement Risk

Finding:
placement_probability directly determines placement_risk_band.

Action:
placement_probability removed from model training.

Conclusion:
Leakage features identified and excluded from machine learning pipelines.

---

## Overall Assessment

Strengths:

* Large sample size
* Realistic correlations
* Consistent structure
* Useful for prototype development

Limitations:

* Synthetic data source
* Limited missing-value behavior
* Extreme risk classes are highly imbalanced

Recommendation:
Suitable for model development, experimentation, explainability analysis, and prototype deployment.
