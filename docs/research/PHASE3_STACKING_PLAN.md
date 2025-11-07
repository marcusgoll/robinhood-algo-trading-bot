# Phase 3: Hierarchical Signal Stacking - Implementation Plan

## Overview

**Goal**: Combine multiple diverse base models using XGBoost meta-learning for 15-25% performance improvement

**Status**: 🚧 In Progress

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Enhanced Features (52D)                    │
│  Phase 1: Multi-timeframe + Phase 2: MAML + S/R Enhanced   │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│                    BASE MODELS (Layer 1)                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ LSTM Model   │  │  GRU Model   │  │ Transformer  │     │
│  │ - Temporal   │  │ - Efficient  │  │ - Attention  │     │
│  │ - 2 layers   │  │ - 2 layers   │  │ - 4 heads    │     │
│  │ - 128 hidden │  │ - 128 hidden │  │ - 128 dim    │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│                                                              │
│  ┌──────────────────────────────────────┐                  │
│  │  HierarchicalTimeframeNet (Phase 1)  │                  │
│  │  - Multi-scale temporal fusion       │                  │
│  │  - Cross-timeframe attention         │                  │
│  └──────────────────────────────────────┘                  │
└──────────────────────┬──────────────────────────────────────┘
                       ↓ (4 prediction vectors)
┌─────────────────────────────────────────────────────────────┐
│                 XGBOOST META-LEARNER (Layer 2)               │
│  Input: Concatenated base model predictions                 │
│  - 4 models × 3 classes = 12 features                       │
│  - Non-linear combination learning                          │
│  - Feature importance for model selection                   │
│  - Automatic weighting                                      │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
               Final Prediction
            (BUY / HOLD / SELL)
```

---

## Components

### 1. Base Models (`base_models.py`)

**Interface**:
```python
class BaseModel(nn.Module):
    def forward(X) → logits (batch, 3)
    def predict_proba(X) → probabilities (batch, 3)
```

**Implementations**:
- **LSTMModel**: 2-layer LSTM with dropout
- **GRUModel**: 2-layer GRU with dropout
- **TransformerModel**: Multi-head self-attention encoder
- **HierarchicalTimeframeNet**: From Phase 1 (reuse)

**Design Principles**:
- Diverse architectures for uncorrelated errors
- Same input features (52D)
- Same output (3-class classification)
- Different inductive biases

### 2. Meta-Learner (`meta_learner.py`)

**XGBoost Configuration**:
```python
xgb.XGBClassifier(
    n_estimators=100,
    max_depth=5,
    learning_rate=0.1,
    objective='multi:softprob',
    eval_metric='mlogloss'
)
```

**Input Features** (12D):
- LSTM predictions (3)
- GRU predictions (3)
- Transformer predictions (3)
- HierarchicalTimeframeNet predictions (3)

**Output**: Final 3-class probabilities

### 3. Stacking Ensemble (`meta_learner.py`)

**Training Process**:
1. Train base models on train set
2. Generate predictions on validation set (out-of-fold)
3. Train meta-learner on validation predictions
4. Final ensemble ready for test set

**Key Features**:
- Cross-validation for meta-features
- Prevents overfitting
- Automatic model weighting
- Feature importance analysis

### 4. Training Pipeline (`training.py`)

**EnsembleTrainer**:
```python
trainer = EnsembleTrainer(
    base_models=[lstm, gru, transformer, htfn],
    meta_learner=xgboost,
    n_folds=5
)

trainer.train(X_train, y_train, X_val, y_val)
ensemble = trainer.get_ensemble()
```

**Features**:
- K-fold cross-validation
- Early stopping
- Model checkpointing
- Performance tracking
- Feature importance logging

---

## Expected Performance

### Individual Base Models
| Model | Expected Accuracy |
|-------|------------------|
| LSTM | 58-62% |
| GRU | 57-61% |
| Transformer | 59-63% |
| HierarchicalTimeframeNet | 60-64% |

### Ensemble (Stacked)
| Metric | Expected Value |
|--------|----------------|
| **Accuracy** | **65-70%** (+15-25% improvement) |
| Sharpe Ratio | 2.0-2.5 |
| Max Drawdown | <15% |
| Win Rate | 60-65% |

---

## Implementation Steps

### Phase 3.1: Base Models ✅
- [x] Create module structure
- [ ] Implement BaseModel interface
- [ ] Implement LSTMModel
- [ ] Implement GRUModel
- [ ] Implement TransformerModel
- [ ] Unit tests for each model

### Phase 3.2: Meta-Learner
- [ ] Implement MetaLearner class
- [ ] Implement StackingEnsemble
- [ ] Cross-validation logic
- [ ] Feature importance analysis
- [ ] Unit tests

### Phase 3.3: Training Pipeline
- [ ] Implement EnsembleTrainer
- [ ] K-fold cross-validation
- [ ] Early stopping
- [ ] Model checkpointing
- [ ] Performance metrics

### Phase 3.4: Validation
- [ ] Create validation script
- [ ] Test on SPY data
- [ ] Compare vs individual models
- [ ] Measure improvement
- [ ] Generate performance report

### Phase 3.5: Documentation
- [ ] Architecture document
- [ ] Usage examples
- [ ] Performance benchmarks
- [ ] Integration guide

---

## Research Background

### Why Hierarchical Stacking Works

**Diversity**: Different models capture different patterns
- LSTM: Long-term temporal dependencies
- GRU: Efficient short-term patterns
- Transformer: Multi-scale attention
- HTF-Net: Cross-timeframe relationships

**Non-linear Blending**: XGBoost learns optimal combination
- Not simple averaging
- Context-dependent weighting
- Handles model correlations
- Reduces overfitting

**Research Support**:
- Ensemble methods: 10-30% improvement (Wolpert, 1992)
- Stacking specifically: 15-25% improvement (Breiman, 1996)
- Financial ML: Outperforms single models (Jiang et al., 2021)

---

## Technical Details

### Input Processing
```python
# Same features for all base models
X = feature_extractor.extract(df, symbol)  # shape: (n, 52)

# Base model predictions
lstm_pred = lstm_model.predict_proba(X)      # (n, 3)
gru_pred = gru_model.predict_proba(X)        # (n, 3)
trans_pred = transformer.predict_proba(X)    # (n, 3)
htfn_pred = htfn.predict_proba(X)           # (n, 3)

# Meta-features (concatenate)
meta_X = np.hstack([lstm_pred, gru_pred, trans_pred, htfn_pred])  # (n, 12)

# Meta-learner prediction
final_pred = xgboost.predict_proba(meta_X)  # (n, 3)
```

### Loss Functions
- **Base models**: CrossEntropyLoss
- **Meta-learner**: Multi-class log loss (mlogloss)

### Regularization
- Dropout in base models (0.3)
- L2 regularization in XGBoost
- Early stopping
- Cross-validation

---

## Dependencies

### New
- `xgboost>=2.0.0` - Meta-learner

### Existing
- `torch>=2.0.0` - Base models
- `numpy>=1.24.0` - Array operations
- `pandas>=2.0.0` - Data handling
- `scikit-learn>=1.3.0` - CV and metrics

---

## File Structure

```
src/trading_bot/ml/ensemble/
├── __init__.py                  # Module exports
├── base_models.py               # LSTM, GRU, Transformer implementations
├── meta_learner.py              # XGBoost meta-learner + StackingEnsemble
└── training.py                  # EnsembleTrainer

validate_ensemble_spy.py         # Validation script
PHASE3_STACKING_SUMMARY.md       # Results document (after validation)
```

---

## Next Steps

1. ✅ Create module structure
2. 🚧 Implement base models
3. ⏳ Implement meta-learner
4. ⏳ Implement training pipeline
5. ⏳ Validation on SPY
6. ⏳ Performance comparison
7. ⏳ Documentation

---

## Success Criteria

- [  ] All base models train successfully
- [  ] Meta-learner achieves <15% validation loss
- [  ] Ensemble accuracy: 65-70% (vs 55-60% baseline)
- [  ] Sharpe ratio: >2.0
- [  ] Feature importance analysis complete
- [  ] Validated on 2+ years of SPY data

---

## Notes

- Focus on diversity: Different architectures = uncorrelated errors
- XGBoost handles correlations between base models automatically
- Use out-of-fold predictions to prevent overfitting
- Feature importance shows which models are most valuable
- Can add/remove base models without retraining all
