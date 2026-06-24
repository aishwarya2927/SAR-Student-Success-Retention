# Baseline Model Results

## Dataset

* Dataset Size: 30,000 Students
* Features Before Cleanup: 70
* Features Used For Training: 62
* Missing Values: 0

## Leakage Features Removed

* academic_risk_score
* placement_probability
* academic_risk_band (target)
* dropout_risk_band
* placement_risk_band
* placement_readiness_score
* career_readiness_score

## Model

* Algorithm: Logistic Regression
* Train Samples: 24,000
* Test Samples: 6,000
* Class Weight: Balanced

## Results

* Accuracy: 95%
* Macro F1: 0.83
* Weighted F1: 0.95

### Class-wise F1

* Critical: 0.56
* High: 0.94
* Medium: 0.84
* Low: 0.97

## Observations

* Strong performance on Low and High risk classes.
* Critical class remains challenging due to severe class imbalance.
* Most errors occur between adjacent risk bands.
* No evidence of severe misclassification.
* Dataset appears suitable for advanced models such as XGBoost.

## Date

* Initial Baseline Experiment
