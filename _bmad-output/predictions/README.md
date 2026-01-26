# BMAD Agent Memory - Prediction System

## Overview

The prediction system provides ML-driven forecasting for agent learning patterns, knowledge transfer effectiveness, and system performance trends. Predictions guide automated decision-making in pattern promotion, insight generation, and resource allocation.

## Prediction Domains

### 1. Pattern Effectiveness Prediction
**Purpose:** Forecast which patterns will succeed in future implementations  
**Model:** Gradient Boosting Classifier  
**Inputs:** Pattern usage history, agent success rates, domain similarity  
**Output:** Success probability (0.0 - 1.0) + confidence interval  
**Update Frequency:** Daily at 2:15 AM (after InsightGeneratorEngine)  
**Target Metric:** >85% accuracy (NFR12)

### 2. Agent Learning Velocity Forecasting
**Purpose:** Predict weekly insight generation rate per agent  
**Model:** Time-series ARIMA  
**Inputs:** Historical event counts, outcome success rates, pattern reuse  
**Output:** Expected insights/week per agent  
**Update Frequency:** Weekly on Sundays 11 PM  
**Target Metric:** 15+ insights/week (NFR10)

### 3. Cross-Agent Knowledge Transfer Prediction
**Purpose:** Identify optimal knowledge sharing opportunities  
**Model:** Graph Neural Network (GNN)  
**Inputs:** Agent collaboration graph, domain expertise overlap  
**Output:** Transfer probability matrix (9x9 agents)  
**Update Frequency:** Monthly on 1st at midnight  
**Target Metric:** 5+ insights/month (NFR11)

### 4. System Performance Degradation Detection
**Purpose:** Forecast query latency increases before SLA breach  
**Model:** Anomaly Detection (Isolation Forest)  
**Inputs:** P95 query times, event log growth rate, index fragmentation  
**Output:** Risk score (0-100) + days until breach  
**Update Frequency:** Hourly  
**Target Metric:** <100ms agent lookups (NFR1)

### 5. Insight Confidence Score Prediction
**Purpose:** Pre-compute confidence for insight candidates  
**Model:** Random Forest Regressor  
**Inputs:** Outcome count, success ratio, domain consistency  
**Output:** Predicted confidence (0.0 - 1.0)  
**Update Frequency:** Real-time during insight generation  
**Target Metric:** Correlation >0.90 with actual scores

### 6. Pattern Promotion Candidate Ranking
**Purpose:** Recommend local patterns ready for global promotion  
**Model:** Ranking SVM  
**Inputs:** Cross-project usage, success rate, agent diversity  
**Output:** Ranked list with promotion readiness score  
**Update Frequency:** Daily at 2:20 AM  
**Target Metric:** >60% pattern reuse (NFR9)

## Data Pipeline

```
[Neo4j Graph]
      ↓
[Feature Extraction Service] ← scripts/extract_prediction_features.py
      ↓
[Model Training Pipeline] ← src/predictions/train_models.py
      ↓
[Prediction Engine] ← src/predictions/predict.py
      ↓
[Validation & Monitoring] ← src/predictions/validate_predictions.py
      ↓
[Forecast Storage] → _bmad-output/predictions/forecasts/
```

## Model Training Schedule

| Model | Training Frequency | Training Data Window | Validation Split |
|-------|-------------------|---------------------|------------------|
| Pattern Effectiveness | Weekly | Last 90 days | 80/20 time-series |
| Learning Velocity | Monthly | Last 6 months | 70/30 |
| Knowledge Transfer | Quarterly | All-time | K-fold cross-validation |
| Performance Degradation | Weekly | Last 30 days | 75/25 |
| Confidence Score | Daily | Last 60 days | 80/20 |
| Promotion Ranking | Bi-weekly | Last 120 days | 80/20 |

## Prediction Accuracy Monitoring

All predictions are validated against actual outcomes. Accuracy metrics are logged to:
- **CSV Log:** `_bmad-output/predictions/validation/model_performance_log.csv`
- **Grafana Dashboard:** Panel "Prediction Accuracy Trends" (port 3000)

### Accuracy Thresholds

| Model | Acceptable | Target | Retraining Trigger |
|-------|-----------|--------|-------------------|
| Pattern Effectiveness | >80% | >85% | <75% for 3 days |
| Learning Velocity | MAE <3 insights | MAE <2 | MAE >5 for 2 weeks |
| Knowledge Transfer | Precision >70% | Precision >80% | Precision <65% |
| Performance Degradation | AUC >0.85 | AUC >0.90 | AUC <0.80 |
| Confidence Score | R² >0.85 | R² >0.90 | R² <0.80 for 7 days |
| Promotion Ranking | NDCG >0.75 | NDCG >0.85 | NDCG <0.70 |

## Integration Points

### With InsightGeneratorEngine
- **Trigger:** After insight generation completes (2:00 AM)
- **Action:** Predict confidence scores for newly generated insights
- **Output:** Updates `(:Insight).predicted_confidence` property

### With RelevanceScoringService
- **Trigger:** After relevance scoring completes (2:10 AM)
- **Action:** Identify pattern promotion candidates
- **Output:** Creates `(:PromotionCandidate)` nodes with ranking scores

### With HealthCheckService
- **Trigger:** Weekly health check (Sundays 1 AM)
- **Action:** Validate prediction accuracy, retrain if needed
- **Output:** Updates `model_performance_log.csv`

## Schema Integration

### New Neo4j Node Labels

```cypher
// Prediction metadata node
(:PredictionRun {
  run_id: "pred_20260126_0215",
  model_name: "pattern_effectiveness_v1",
  timestamp: datetime(),
  accuracy: 0.87,
  sample_size: 452
})

// Promotion candidate tracking
(:PromotionCandidate {
  pattern_id: "pattern_123",
  rank: 1,
  promotion_score: 0.94,
  predicted_global_success_rate: 0.89,
  supporting_agents: ["Brooks", "Winston", "Jay"],
  generated_at: datetime()
})
```

### Query Examples

```cypher
// Get top 5 promotion candidates
MATCH (pc:PromotionCandidate)
WHERE pc.generated_at > datetime() - duration({days: 1})
RETURN pc.pattern_id, pc.promotion_score, pc.predicted_global_success_rate
ORDER BY pc.rank ASC
LIMIT 5;

// Check prediction accuracy trends
MATCH (pr:PredictionRun)
WHERE pr.model_name = "pattern_effectiveness_v1"
  AND pr.timestamp > datetime() - duration({days: 30})
RETURN pr.timestamp, pr.accuracy
ORDER BY pr.timestamp DESC;
```

## Directory Structure

```
predictions/
├── README.md (this file)
├── models/
│   ├── pattern_success_predictor.pkl          # Trained scikit-learn model
│   ├── learning_velocity_model.json           # ARIMA coefficients
│   ├── knowledge_transfer_gnn.pt              # PyTorch GNN weights
│   ├── performance_degradation_detector.pkl   # Isolation Forest
│   ├── confidence_score_rf.pkl                # Random Forest
│   ├── promotion_ranking_svm.pkl              # Ranking SVM
│   └── model_registry.yaml                    # Version tracking
├── forecasts/
│   ├── daily/
│   │   ├── 2026-01-26_predictions.json       # All daily predictions
│   │   └── 2026-01-26_confidence_scores.json # Insight confidence forecasts
│   └── weekly/
│       └── week_05_2026_forecast.json        # Learning velocity forecasts
├── validation/
│   ├── model_performance_log.csv             # Timestamp, model, metric, value
│   └── prediction_vs_actual.json             # Ground truth comparisons
└── analysis/
    ├── pattern_promotion_candidates.md       # Human-readable recommendations
    └── agent_learning_trends.md              # Velocity analysis & insights
```

## Developer Quick Start

### 1. Train Initial Models

```bash
# Extract features from Neo4j
python scripts/extract_prediction_features.py --output-dir data/features/

# Train all prediction models
python src/predictions/train_models.py --config config/prediction_models.yaml

# Validate model performance
python src/predictions/validate_predictions.py --test-data data/features/test_set.csv
```

### 2. Generate Predictions

```bash
# Daily prediction run (manual trigger for testing)
python src/predictions/predict.py --model pattern_effectiveness --date 2026-01-26

# Scheduled production run (via APScheduler)
# See: src/tasks/prediction_scheduler.py
```

### 3. Monitor Accuracy

```bash
# View prediction accuracy summary
python src/predictions/accuracy_report.py --days 30

# Compare predictions to actual outcomes
python src/predictions/compare_predictions.py --run-id pred_20260126_0215
```

## Dependencies

Add to `requirements.txt`:

```
# Prediction System
scikit-learn==1.3.2
statsmodels==0.14.0       # ARIMA
torch==2.1.0              # GNN
torch-geometric==2.4.0    # Graph neural networks
pandas==2.1.3
numpy==1.26.2
joblib==1.3.2             # Model serialization
shap==0.43.0              # Model explainability
```

## Maintenance

- **Model Retraining:** Automated weekly (Sundays 11 PM) if accuracy drops below threshold
- **Feature Engineering:** Review quarterly for new graph patterns
- **Hyperparameter Tuning:** Bi-annually using Optuna
- **Model Archival:** Store previous model versions in `models/archive/` for rollback

---

**Status:** ✅ Ready for Implementation  
**Owner:** Winston (Architect) + Brooks (Implementation)  
**Last Updated:** 2026-01-26  
**Version:** 1.0.0
