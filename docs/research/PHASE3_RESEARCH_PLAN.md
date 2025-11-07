# Phase 3: Systematic Ensemble Research - Execution Plan

**Status**: Quick Validation Running (10 experiments)
**Date**: November 4, 2025
**Objective**: Find optimal ML architecture and hyperparameters for 60-minute stock return prediction

---

## Executive Summary

We've built a comprehensive experimental framework to systematically test **1,620 model configurations** across:
- **9 architectures**: LSTM, GRU, Transformer, CNN-LSTM, Multi-Task, Attention-LSTM, MoE, TFT
- **5 prediction horizons**: 15min, 30min, 60min, 2hr, 1day
- **Multiple hyperparameters**: Batch size, learning rate, weight decay
- **3 data periods**: 3mo, 6mo, 1yr

**Current Baseline**: 55.50% directional accuracy (LSTM, 60-min horizon)
**Target**: 57-60% with optimal configuration

---

## Infrastructure Built

### 1. Core Files

| File | Lines | Purpose |
|------|-------|---------|
| `experiment_config.yaml` | 270 | Configuration for all experiment combinations |
| `experiment_tracker.py` | 396 | SQLite database tracking all results |
| `models_v2.py` | 522 | All Tier 1-3 model architectures |
| `experiment_runner.py` | 438 | Parallel execution engine |
| `test_experiment_framework.py` | 233 | Validation suite |

### 2. Model Architectures Implemented

**Baseline Models** (Tier 1):
- `RegressionLSTM` - 64K params, 2-layer LSTM
- `RegressionGRU` - 64K params, 2-layer GRU
- `RegressionTransformer` - 65K params, multi-head attention

**Advanced Models** (Tier 2):
- `CNN_LSTM` - 76K params, 1D conv + LSTM hybrid
- `MultiTaskLSTM` - 65K params, predicts 4 horizons simultaneously
- `AttentionLSTM` - 66K params, self-attention mechanism

**Cutting-Edge** (Tier 3):
- `MixtureOfExperts` - 193K params, gating network routes to specialists
- `TemporalFusionTransformer` - 143K params, SOTA temporal attention

### 3. Database Schema

**Experiments Table** tracks:
- Configuration hash (deterministic experiment ID)
- Data config (symbol, period, timeframe, samples)
- Model config (type, params)
- Training config (batch size, LR, epochs)
- Performance metrics (directional accuracy, MSE, RMSE, MAE, R²)
- Timing (duration, timestamps)

**Ensemble Experiments Table** tracks:
- Base model combinations
- Ensemble method (averaging, weighted, stacking, voting)
- Performance vs best base model

---

## Experimental Design

### Phase 1A: Quick Validation (CURRENT)
**Status**: Running (Process 3811ea)
**Experiments**: 10
**Duration**: ~20 minutes
**Purpose**: Verify end-to-end pipeline (data fetch, training, metrics, database)

### Phase 1B: Full Baseline Sweep
**Experiments**: 1,620
**Duration**: ~13.5 hours (4 parallel workers)
**Coverage**:
- All 9 model architectures
- All 5 prediction horizons
- All hyperparameter combinations
- 3 data periods (3mo, 6mo, 1yr)

**Optimization Grid**:
```
Models (9) × Horizons (5) × Periods (3) × Batch (2) × LR (3) × WD (2)
= 9 × 5 × 3 × 2 × 3 × 2 = 1,620 experiments
```

### Phase 2: Feature Engineering (Post Phase 1)
**Experiments**: ~50
**Purpose**: Test top 10 models with enhanced features
- Multi-timeframe features (1min + 5min + 15min)
- News sentiment (if available)
- Options flow (if available)

### Phase 3: Ensemble Methods (Final)
**Experiments**: ~30
**Purpose**: Combine top models with intelligent ensembling
- Simple averaging
- Weighted by performance
- Selective thresholding (exclude <52% models)
- XGBoost stacking
- Hard/soft voting

---

## Success Criteria

### Minimum Viable (Phase 1B)
- ✅ Pipeline runs without errors
- ✅ Database tracks all experiments
- ✅ Find config with >56% directional accuracy

### Target (Phase 2)
- 🎯 57-58% directional accuracy with feature engineering
- 🎯 Positive R² score (explain variance)
- 🎯 RMSE < 0.18% for 60-min predictions

### Stretch (Phase 3)
- 🌟 59-60% directional accuracy with ensemble
- 🌟 Consistent performance across walk-forward CV
- 🌟 Ensemble beats all individual models

---

## Analysis Plan

### Immediate (After Phase 1A)
1. Check top 3 performing configs
2. Verify data fetch and feature extraction work
3. Confirm training metrics make sense

### After Phase 1B Completion
1. **Leaderboard Analysis**:
   ```sql
   SELECT model_name, horizon_name,
          AVG(directional_accuracy) as avg_acc,
          MAX(directional_accuracy) as max_acc
   FROM experiments
   WHERE status='completed'
   GROUP BY model_name, horizon_name
   ORDER BY avg_acc DESC;
   ```

2. **Hyperparameter Sensitivity**:
   - Which LR works best? (0.0001 vs 0.0005 vs 0.001)
   - Does batch size matter? (32 vs 64)
   - Weight decay impact? (0.001 vs 0.01)

3. **Architecture Comparison**:
   - Do advanced models beat baseline LSTM?
   - Is CNN-LSTM worth the complexity?
   - Does Multi-Task help vs single-task?

4. **Horizon Analysis**:
   - Best prediction horizon? (15min, 30min, 60min, 2hr, 1day)
   - Trade-off: accuracy vs actionability

5. **Data Period Impact**:
   - More data = better? (3mo vs 6mo vs 1yr)
   - Diminishing returns?

### Visualizations to Create
1. Heatmap: Model × Horizon performance grid
2. Box plots: Directional accuracy distribution per model
3. Scatter: RMSE vs Directional Accuracy
4. Learning curves: Best models' validation curves
5. Feature importance: Top 10 features per model

---

## Current Status (Phase 1A)

### Running Experiments
```
Process ID: 3811ea
Command: python experiment_runner.py --limit 10 --max-workers 4
Log File: phase3_quick_validation.log
Status: RUNNING
```

### Expected Timeline
- **Phase 1A**: 20 minutes (10 experiments)
- **Phase 1B**: 13.5 hours (1,620 experiments)
- **Analysis**: 1-2 hours
- **Phase 2**: 2-3 hours (50 experiments with enhanced features)
- **Phase 3**: 1 hour (30 ensemble experiments)

**Total Research Time**: ~18 hours

---

## Next Steps

### Immediate (After Phase 1A Completes)
1. ✅ Verify 10 experiments completed successfully
2. ✅ Check database has 10 entries
3. ✅ Review top performer metrics
4. ✅ Confirm no errors in logs

### If Phase 1A Succeeds
5. 🚀 Launch Phase 1B (full 1,620 experiments)
6. 📊 Set up monitoring dashboard
7. ⏰ Schedule analysis for completion (~13.5 hours)

### If Phase 1A Has Issues
5. 🔧 Debug and fix errors
6. 🧪 Re-run Phase 1A
7. 📝 Update experiment configs as needed

---

## Commands Reference

### Check Experiment Status
```bash
# Check running experiments
sqlite3 experiments.db "SELECT status, COUNT(*) FROM experiments GROUP BY status"

# Top 10 performers
sqlite3 experiments.db "SELECT model_name, horizon_name, directional_accuracy FROM experiments WHERE status='completed' ORDER BY directional_accuracy DESC LIMIT 10"

# Check specific experiment
python -c "from experiment_tracker import ExperimentTracker; t = ExperimentTracker(); print(t.get_statistics())"
```

### Launch Full Research
```bash
# Full sweep (after Phase 1A validates)
python experiment_runner.py --max-workers 4

# Monitor progress
watch -n 60 'sqlite3 experiments.db "SELECT status, COUNT(*) FROM experiments GROUP BY status"'

# Export results
python -c "from experiment_tracker import ExperimentTracker; ExperimentTracker().export_to_csv('results.csv')"
```

---

## Risk Mitigation

### Potential Issues
1. **Data fetch failures**: Alpaca API rate limits
   - Mitigation: Retry logic implemented, caching

2. **Training failures**: OOM, convergence issues
   - Mitigation: Experiment isolation, error tracking in DB

3. **Time overrun**: 13.5 hours might be optimistic
   - Mitigation: Can pause/resume (experiment caching)

4. **Disk space**: 1,620 experiments = large database
   - Mitigation: Not saving model weights, only metrics

### Contingency Plans
- If >10% experiments fail: Debug common failure mode
- If accuracy plateaus <56%: Add feature engineering earlier
- If time exceeds 20 hours: Reduce hyperparameter grid

---

## Documentation

All results will be documented in:
1. **experiments.db** - SQLite database (queryable)
2. **experiment_results.csv** - Flat file export
3. **phase3_research_report.md** - Final findings (generated post-completion)
4. **Leaderboard visualizations** - Top 20 configs

---

## Research Questions We'll Answer

1. **Architecture**: Which model type works best for stock prediction?
2. **Horizon**: What's the optimal prediction timeframe?
3. **Hyperparameters**: Which settings matter most?
4. **Data**: How much history do we need?
5. **Ensemble**: Can combining models beat individuals?
6. **Feature Engineering**: Do complex features help or hurt?
7. **Stability**: Are results consistent across periods?

---

**Framework Status**: ✅ READY
**Phase 1A Status**: 🟡 RUNNING
**Next Milestone**: Phase 1B full sweep launch
