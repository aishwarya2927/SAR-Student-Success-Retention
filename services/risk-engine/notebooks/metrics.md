# Model Metrics — Academic Risk Band Prediction

**Model**: XGBoost (v2, production)  
**Test set size**: 6000 rows (20 % stratified hold-out)  

## Overall

| Metric | Score |
| --- | --- |
| Accuracy | 0.9583 |
| Weighted F1 | 0.9598 |
| Macro F1 | 0.8920 |

## Per-Class

| Class | Precision | Recall | F1 | Support |
| --- | --- | --- | --- | --- |
| Critical | 0.7105 | 0.8182 | 0.7606 | 33 |
| High | 0.9790 | 0.9675 | 0.9732 | 338 |
| Low | 0.9909 | 0.9613 | 0.9759 | 4878 |
| Medium | 0.7891 | 0.9414 | 0.8585 | 751 |

## Why Recall Matters More Than Accuracy

The dataset is heavily skewed (Low ≈ 81 %).  A naïve model that predicts
*Low* for every student would achieve ~81 % accuracy while missing every
High/Critical student.  We therefore optimise for **recall on High and Critical**
classes — missing an at-risk student is far costlier than a false alarm.

## Model Comparison vs Logistic Regression Baseline

| Model | Accuracy | Weighted F1 | Macro F1 |
| --- | --- | --- | --- |
| Logistic Regression | 0.9465 | 0.9498 | 0.8275 |
| XGBoost (v2)        | 0.9583 | 0.9598 | 0.8920 |

## Why XGBoost + Balanced Weights

- XGBoost handles the mix of numeric and ordinal-encoded categorical features
  without requiring feature scaling, which Logistic Regression needs.
- Gain-based feature importance is available natively and feeds the SHAP
  explainability layer (Week 3).
- `compute_sample_weight('balanced')` up-weights the minority Critical / High
  classes during training, raising their recall without discarding data.
- Early stopping on a validation hold-out prevents overfitting to the dominant
  Low class.