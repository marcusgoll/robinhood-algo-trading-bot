# Phase 4: Feature Engineering - Execution Plan

**Previous Phase**: Phase 3 achieved 59.65% accuracy with Attention-LSTM @ 78-bar horizon
**Current Objective**: Improve to 60-61% accuracy through enhanced feature engineering
**Status**: Planning

---

## Executive Summary

Phase 3 identified the optimal model architecture (Attention-LSTM) and prediction horizon (78 bars / 6.5 hours). Phase 4 will test enhanced feature sets while keeping the winning architecture fixed.

**Target**: 60-61% directional accuracy (0.35-1.35% improvement)
**Approach**: Systematic feature ablation study
**Duration**: ~50 experiments (2-3 hours with 4 workers)

---

## Winning Configuration (Fixed)

```python
Model: AttentionLSTM
  - Hidden dim: 64
  - Num layers: 2
  - Dropout: 0.3

Prediction: 78 bars (6.5 hours ahead)
Data: SPY 5-minute bars, 6 months
Hyperparameters:
  - Batch size: 32
  - Learning rate: 0.0001
  - Weight decay: 0.001
  - Max epochs: 30 (early stopping patience=5)
```

**Baseline Feature Set** (52 technical + 5 microstructure):
- Returns (1, 3, 6, 12, 24 bars)
- Moving averages (SMA 5, 10, 20, 50, 200)
- Bollinger Bands
- RSI, MACD, Stochastic
- ATR, ADX
- Volume indicators (OBV, VWAP)
- Microstructure (bid-ask spread, order imbalance)

---

## Feature Sets to Test

### Set 1: Multi-Timeframe (HIGH PRIORITY)

**Hypothesis**: Aligning multiple timeframes provides richer context.

**Features to add**:
- **1-minute bars**: High-frequency microstructure
  - Last 5 returns
  - Volume spikes
  - Bid-ask spread volatility

- **15-minute bars**: Intraday trend
  - SMA 10, 20
  - RSI, MACD
  - Volume profile

- **1-hour bars**: Daily pattern
  - SMA 5, 10, 20
  - Bollinger Bands
  - ATR

- **4-hour bars**: Swing trend
  - SMA 5, 10
  - Trend strength (ADX)

**Total new features**: ~25
**Expected gain**: +0.5-1.0%

**Implementation**:
```python
# Fetch aligned data
bars_1min = fetch_data("SPY", "1Min", days=180)
bars_5min = fetch_data("SPY", "5Min", days=180)  # Existing
bars_15min = fetch_data("SPY", "15Min", days=180)
bars_1hr = fetch_data("SPY", "1H", days=180)
bars_4hr = fetch_data("SPY", "4H", days=180)

# Align timestamps and merge
aligned_df = align_multi_timeframe([bars_1min, bars_5min, bars_15min, bars_1hr, bars_4hr])
```

### Set 2: Sentiment Analysis (MEDIUM PRIORITY)

**Hypothesis**: News sentiment influences multi-hour moves.

**Data sources**:
1. **FinBERT** (free, Hugging Face)
   - Sentiment scores (-1 to +1)
   - Run on news headlines for SPY/market

2. **Twitter/X sentiment** (if available)
   - StockTwits API
   - Sentiment aggregation

3. **VIX (Fear index)**
   - Current VIX level
   - VIX changes
   - VIX term structure

**Total new features**: ~5-10
**Expected gain**: +0.3-0.7%

**Implementation**:
```python
from transformers import pipeline
sentiment_analyzer = pipeline("sentiment-analysis", model="ProsusAI/finbert")

# Fetch news for current timestamp
news = fetch_news("SPY", timestamp)
sentiments = [sentiment_analyzer(headline)[0]['score'] for headline in news]
avg_sentiment = np.mean(sentiments)
```

### Set 3: Options Data (MEDIUM PRIORITY)

**Hypothesis**: Options market reflects informed trader expectations.

**Features to add**:
- **Implied Volatility (IV)**
  - ATM IV
  - IV rank (percentile)
  - IV skew (put/call IV difference)

- **Put/Call Ratio**
  - Volume-based
  - Open interest-based

- **Options Flow**
  - Unusual activity (large trades)
  - Call premium vs put premium

**Total new features**: ~8
**Expected gain**: +0.2-0.5%

**Data source**: Alpaca options API or CBOE

### Set 4: Market Microstructure (LOW PRIORITY)

**Hypothesis**: Order flow provides edge for short-term moves.

**Features to add**:
- **Order book imbalance** (if available)
  - Bid size / Ask size ratio
  - Depth at 5 levels

- **Trade flow**
  - Buyer/seller initiated volume
  - Large trade frequency

- **Quote changes**
  - Spread changes
  - Quote updates per minute

**Total new features**: ~10
**Expected gain**: +0.1-0.3%

**Note**: Requires Level 2 data (may not be available via Alpaca)

### Set 5: Macroeconomic Indicators (LOW PRIORITY)

**Hypothesis**: Macro trends influence daily moves.

**Features to add**:
- **Interest rates**
  - 10-year Treasury yield
  - Fed funds rate
  - Yield curve slope

- **Currency**
  - DXY (dollar index)

- **Commodities**
  - Gold (GLD)
  - Oil (USO)

**Total new features**: ~6
**Expected gain**: +0.1-0.2%

**Update frequency**: Daily (slow-moving)

---

## Experimental Design

### Phase 4A: Multi-Timeframe (Priority 1)

**Experiments**: 20 configurations
- Test each timeframe individually (1min, 15min, 1hr, 4hr)
- Test pairwise combinations (5min+1hr, 5min+15min, etc.)
- Test all timeframes combined
- Vary feature subset sizes

**Expected duration**: 1 hour (4 workers)

### Phase 4B: Sentiment + Options (Priority 2)

**Experiments**: 15 configurations
- Baseline + sentiment
- Baseline + options
- Baseline + both
- Multi-timeframe + sentiment
- Multi-timeframe + options
- All combined

**Expected duration**: 45 min (4 workers)

### Phase 4C: Full Feature Set (Priority 3)

**Experiments**: 10 configurations
- All features combined
- Feature selection (remove low-correlation features)
- Feature importance analysis
- Hyperparameter tuning on best feature set

**Expected duration**: 30 min (4 workers)

### Phase 4D: Validation

**Walk-forward test**:
- Train on months 1-5
- Test on month 6
- Compare to baseline (59.65%)

**Out-of-sample test**:
- Fetch most recent month (not in training)
- Evaluate performance
- Check for overfitting

---

## Success Criteria

| Tier | Accuracy | Status |
|------|----------|--------|
| Minimum | 60.00% | +0.35% gain |
| Target | 60.50% | +0.85% gain |
| Stretch | 61.00% | +1.35% gain |

**Additional metrics**:
- Sharpe ratio > 1.5
- Win rate > 55%
- Max drawdown < 15%
- Consistency across walk-forward folds

---

## Implementation Steps

### Step 1: Multi-Timeframe Data Pipeline

```python
# Create multi_timeframe_features.py

def fetch_aligned_multi_timeframe(symbol, timeframes, days=180):
    """Fetch and align multiple timeframes."""
    dfs = {}
    for tf in timeframes:
        dfs[tf] = fetch_data(symbol, tf, days=days)

    # Align to 5min bars (base timeframe)
    base_df = dfs['5Min']

    for tf, df in dfs.items():
        if tf == '5Min':
            continue
        # Resample and forward-fill to 5min
        aligned = df.resample('5Min').ffill()
        # Add suffix to columns
        aligned.columns = [f"{col}_{tf}" for col in aligned.columns]
        base_df = base_df.join(aligned, how='left')

    return base_df

def extract_multi_tf_features(df):
    """Extract features from multi-timeframe data."""
    features = []

    # 1min features (if available)
    if '1Min' in df.columns:
        features.append(df['returns_1Min'].rolling(5).mean())  # Recent 1min trend
        features.append(df['volume_1Min'].rolling(5).std())   # 1min vol volatility

    # 15min features
    if '15Min' in df.columns:
        features.append(calculate_rsi(df['close_15Min'], 14))
        features.append(calculate_sma(df['close_15Min'], 10))

    # 1hr features
    if '1H' in df.columns:
        features.append(calculate_bollinger_bands(df['close_1H'], 20))
        features.append(calculate_atr(df['high_1H'], df['low_1H'], df['close_1H'], 14))

    # 4hr features
    if '4H' in df.columns:
        features.append(calculate_adx(df['high_4H'], df['low_4H'], df['close_4H'], 14))

    return pd.concat(features, axis=1)
```

### Step 2: Sentiment Pipeline (Optional)

```python
# Create sentiment_features.py

from transformers import pipeline
import requests

def fetch_news_sentiment(symbol, timestamp):
    """Fetch news sentiment for a given timestamp."""
    # Use NewsAPI or similar
    news = fetch_news_headlines(symbol, timestamp)

    # FinBERT sentiment
    sentiment_model = pipeline("sentiment-analysis", model="ProsusAI/finbert")
    sentiments = [sentiment_model(headline)[0] for headline in news]

    # Aggregate
    avg_score = np.mean([s['score'] if s['label']=='positive' else -s['score'] for s in sentiments])

    return avg_score

def add_vix_features(df):
    """Add VIX (volatility index) features."""
    vix_data = fetch_data("VIX", "5Min", days=180)
    df['vix'] = vix_data['close']
    df['vix_change'] = df['vix'].pct_change()
    return df
```

### Step 3: Feature Engineering Config

```yaml
# phase4_feature_config.yaml

feature_sets:
  baseline:
    name: "baseline"
    description: "Phase 3 features (52 technical + 5 microstructure)"
    enabled: true

  multi_tf_1min:
    name: "multi_tf_1min"
    description: "Baseline + 1-minute bars"
    timeframes: ["1Min", "5Min"]
    enabled: true

  multi_tf_15min:
    name: "multi_tf_15min"
    description: "Baseline + 15-minute bars"
    timeframes: ["5Min", "15Min"]
    enabled: true

  multi_tf_1hr:
    name: "multi_tf_1hr"
    description: "Baseline + 1-hour bars"
    timeframes: ["5Min", "1H"]
    enabled: true

  multi_tf_all:
    name: "multi_tf_all"
    description: "All timeframes (1min, 5min, 15min, 1hr, 4hr)"
    timeframes: ["1Min", "5Min", "15Min", "1H", "4H"]
    enabled: true

  sentiment:
    name: "sentiment"
    description: "Baseline + news sentiment + VIX"
    add_sentiment: true
    add_vix: true
    enabled: false  # Requires API access

  options:
    name: "options"
    description: "Baseline + IV + put/call ratio"
    add_iv: true
    add_put_call: true
    enabled: false  # Requires options data

model:
  name: "attention_lstm"
  type: "attention_lstm"
  params:
    input_dim: auto  # Will be calculated based on features
    hidden_dim: 64
    num_layers: 2
    dropout: 0.3

training:
  horizon_bars: 78  # Fixed from Phase 3
  batch_size: 32
  learning_rate: 0.0001
  weight_decay: 0.001
  max_epochs: 30
  patience: 5

execution:
  max_parallel: 4
  device: "cpu"
```

### Step 4: Create Feature Engineering Runner

```python
# phase4_feature_runner.py

import yaml
from experiment_tracker import ExperimentTracker
from models_v2 import create_model
from multi_timeframe_features import fetch_aligned_multi_timeframe, extract_multi_tf_features

def run_feature_experiment(config, db_path="experiments.db"):
    """Run single feature engineering experiment."""
    tracker = ExperimentTracker(db_path)

    # Check if already run
    existing = tracker.get_experiment_by_config(config)
    if existing:
        print(f"[CACHED] {config['feature_set']}")
        tracker.close()
        return existing

    exp_id = tracker.start_experiment(config)
    print(f"[START] {exp_id}: {config['feature_set']}")

    try:
        # Fetch data based on feature set
        if 'timeframes' in config:
            df = fetch_aligned_multi_timeframe("SPY", config['timeframes'], days=180)
            X, y = extract_multi_tf_features(df, horizon=78)
        else:
            # Baseline features
            df = fetch_data("SPY", "5Min", days=180)
            X, y = extract_features_and_targets(df, horizon=78)

        # Create model (architecture fixed)
        model = create_model(config['model'])

        # Train
        train_model(model, X_train, y_train, X_val, y_val, **config['training'])

        # Evaluate
        metrics = evaluate_model(model, X_test, y_test)

        # Record results
        results = {**config, **metrics, 'num_samples': len(X), 'num_features': X.shape[1]}
        tracker.complete_experiment(exp_id, results, status="completed")

        print(f"[DONE] {exp_id}: Acc={metrics['directional_accuracy']:.2%}, Features={X.shape[1]}")

        tracker.close()
        return results

    except Exception as e:
        print(f"[FAIL] {exp_id}: {str(e)}")
        tracker.complete_experiment(exp_id, {"error_message": str(e)}, status="failed")
        tracker.close()
        return {"status": "failed", "error": str(e)}

def main():
    # Load config
    with open("phase4_feature_config.yaml") as f:
        config = yaml.safe_load(f)

    # Generate experiment configs
    experiments = []
    for fs_name, fs_config in config['feature_sets'].items():
        if not fs_config.get('enabled', True):
            continue

        exp_config = {
            'feature_set': fs_name,
            **fs_config,
            'model': config['model'],
            'training': config['training']
        }
        experiments.append(exp_config)

    print(f"\n{'='*80}")
    print(f"PHASE 4: FEATURE ENGINEERING - {len(experiments)} EXPERIMENTS")
    print(f"{'='*80}\n")

    # Run experiments
    results = []
    for exp_config in experiments:
        result = run_feature_experiment(exp_config)
        results.append(result)

    # Summary
    print(f"\n{'='*80}")
    print(f"COMPLETED {len(results)} EXPERIMENTS")
    print(f"{'='*80}\n")

    # Leaderboard
    successful = [r for r in results if r.get('directional_accuracy')]
    successful.sort(key=lambda x: x['directional_accuracy'], reverse=True)

    print("TOP 5 FEATURE SETS:")
    for i, result in enumerate(successful[:5], 1):
        print(f"{i}. {result['feature_set']}: {result['directional_accuracy']:.4%} ({result['num_features']} features)")

    # Export
    tracker = ExperimentTracker()
    tracker.export_to_csv('phase4_feature_results.csv')
    tracker.close()

if __name__ == "__main__":
    main()
```

---

## Risk Mitigation

### Potential Issues

1. **Data alignment errors** (multi-timeframe)
   - Mitigation: Robust timestamp alignment with forward-fill
   - Validation: Check for NaN values before training

2. **Feature explosion** (too many features)
   - Mitigation: Start with selective features, not all combinations
   - Feature selection: Remove low-correlation features

3. **Overfitting** (more features = more risk)
   - Mitigation: Walk-forward validation
   - Regularization: Keep dropout=0.3, weight_decay=0.001

4. **API limitations** (sentiment, options data)
   - Mitigation: Start with free sources (VIX, multi-timeframe)
   - Fallback: Skip premium features if unavailable

---

## Timeline

| Phase | Duration | Experiments | Deliverable |
|-------|----------|-------------|-------------|
| 4A: Multi-TF | 1 hour | 20 | Best timeframe combo |
| 4B: Sentiment/Options | 45 min | 15 | Best premium features |
| 4C: Full combo | 30 min | 10 | Final feature set |
| 4D: Validation | 30 min | 5 | Walk-forward results |
| **Total** | **3 hours** | **50** | **Phase 4 Report** |

---

## Next Steps (Immediate)

1. Create `multi_timeframe_features.py` - Data pipeline
2. Create `phase4_feature_config.yaml` - Configuration
3. Create `phase4_feature_runner.py` - Experiment runner
4. Run Phase 4A (multi-timeframe experiments)
5. Analyze results and select best feature set
6. Run walk-forward validation
7. Generate Phase 4 report

---

**Status**: Ready to implement
**Expected Outcome**: 60-61% accuracy with enhanced features
**Next Milestone**: Phase 4A completion (multi-timeframe experiments)
