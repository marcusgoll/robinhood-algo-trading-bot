# ML-Based Trading Strategy Generator

Automated trading strategy generation and execution using machine learning.

## Overview

This module provides a complete pipeline for generating, validating, and deploying ML-based trading strategies:

1. **Feature Extraction** - Convert market data into 55-dimensional feature vectors
2. **Strategy Generation** - Generate strategies using GP, RL, and LLM approaches
3. **Validation** - Backtest with walk-forward optimization to prevent overfitting
4. **Selection** - Select best strategies using Pareto optimization or diversity methods
5. **Ensemble** - Combine strategies with optimal weighting (Kelly, risk parity, etc.)
6. **Execution** - Deploy strategies to live trading

## Quick Start

```python
from trading_bot.ml.config import MLConfig
from trading_bot.ml.features import FeatureExtractor
from trading_bot.ml.generators import GeneticProgrammingGenerator, LLMGuidedGenerator
from trading_bot.ml.backtesting import StrategyValidator
from trading_bot.ml.selection import StrategySelector, EnsembleBuilder

# 1. Load configuration
config = MLConfig()

# 2. Extract features
extractor = FeatureExtractor()
features = extractor.extract(ohlcv_data, symbol="AAPL")

# 3. Generate strategies
gp_gen = GeneticProgrammingGenerator(config.gp_config)
strategies = gp_gen.generate(num_strategies=100, historical_data=data, config={})

# 4. Validate
validator = StrategyValidator(config.backtest_config)
results = validator.batch_validate(strategies, data)
passed = [r.strategy for r in results if r.passed]

# 5. Select & ensemble
selector = StrategySelector(config.selection_config)
selection = selector.select(passed)

builder = EnsembleBuilder(config.selection_config)
ensemble = builder.create_ensemble(selection.selected_strategies)

print(f"Ensemble Sharpe: {ensemble.metrics.sharpe_ratio:.2f}")
```

## Architecture

```
ml/
├── models.py              # Data models (MLStrategy, FeatureSet, etc.)
├── config.py              # Configuration classes
├── features/              # Feature extraction
│   ├── extractor.py       # Main orchestrator (55 features)
│   ├── technical.py       # Technical indicators
│   ├── patterns.py        # Chart patterns
│   ├── sentiment.py       # Sentiment analysis
│   └── microstructure.py  # Order flow features
├── generators/            # Strategy generators
│   ├── genetic_programming.py  # GP-based evolution
│   ├── reinforcement_learning.py  # RL agents (PPO)
│   └── llm_guided.py      # LLM-generated rules
├── backtesting/           # Validation
│   ├── walk_forward.py    # Walk-forward optimizer
│   └── validator.py       # Strategy validator
└── selection/             # Portfolio construction
    ├── selector.py        # Strategy selection
    └── ensemble.py        # Ensemble creation
```

## Feature Extraction

### 55-Dimensional Feature Vector

**Price Features (10)**
- Returns (1d, 5d, 20d)
- Volatility (20d realized)
- Volume ratio vs average
- Intraday range metrics
- Price vs moving averages (SMA20, SMA50)
- Price vs VWAP

**Technical Indicators (15)**
- RSI (14)
- MACD (12, 26, 9)
- Stochastic (14, 3)
- ATR (14)
- ADX (14)
- CCI (20)
- Williams %R
- ROC (10)
- Momentum (20)
- Bollinger Bands position
- Keltner Channel position
- Donchian Channel position

**Market Microstructure (5)**
- Bid-ask spread
- Order imbalance
- Tick direction
- VWAP distance
- Volume profile rank

**Sentiment (3)**
- News sentiment (FinBERT)
- Social media sentiment (Twitter/Reddit)
- Options sentiment (put/call ratio)

**Time Features (4)**
- Hour of day
- Day of week
- Days to earnings
- Days from earnings

**Pattern Features (8)**
- Support/resistance distance
- Trend indicators (uptrend/downtrend)
- Bull/bear flag scores
- Breakout/reversal signals

### Usage

```python
from trading_bot.ml.features import FeatureExtractor

extractor = FeatureExtractor()

# Extract features for all bars
feature_sets = extractor.extract(ohlcv_df, symbol="AAPL")

# Extract latest only (more efficient)
latest = extractor.extract_latest(ohlcv_df, symbol="AAPL")

# Convert to numpy array for ML models
X = latest.to_array()  # Shape: (55,)
```

## Strategy Generation

### Genetic Programming

Evolves trading rules as syntax trees:

```python
from trading_bot.ml.generators import GeneticProgrammingGenerator
from trading_bot.ml.config import GeneticProgrammingConfig

config = GeneticProgrammingConfig(
    population_size=2000,
    num_generations=50,
    tournament_size=20,
    mutation_rate=0.15,
    crossover_rate=0.75,
)

generator = GeneticProgrammingGenerator(config)
strategies = generator.generate(
    num_strategies=20,
    historical_data=data,
    config={}
)
```

**Example evolved rule:**
```
(and (gt (div close (sma close 20)) 1.02) (gt rsi 30))
→ Buy when price > SMA(20) * 1.02 AND RSI > 30
```

### LLM-Guided

Uses GPT-4 to generate interpretable strategies:

```python
from trading_bot.ml.generators import LLMGuidedGenerator
from trading_bot.ml.config import LLMConfig

config = LLMConfig(
    model="gpt-4",
    temperature=0.7,
    num_strategies_per_prompt=10,
)

generator = LLMGuidedGenerator(config)
strategies = generator.generate(
    num_strategies=10,
    historical_data=data,
    config={}
)
```

**Example LLM output:**
```json
{
  "name": "RSI Mean Reversion",
  "entry_conditions": [
    "RSI < 30",
    "Price below SMA(20)",
    "Volume > 1.5x average"
  ],
  "exit_conditions": [
    "RSI > 70",
    "Profit >= 2%",
    "Stop loss >= 3%"
  ]
}
```

### Reinforcement Learning

(Coming soon - PPO-based trading agent)

## Validation

### Walk-Forward Optimization

Prevents overfitting by testing on unseen data:

```python
from trading_bot.ml.backtesting import WalkForwardOptimizer
from trading_bot.ml.config import BacktestConfig

config = BacktestConfig(
    train_test_split=0.75,
    walk_forward_windows=10,
)

optimizer = WalkForwardOptimizer(config)
result = optimizer.validate(strategy, historical_data)

if result.is_overfit:
    print("Strategy appears overfit!")
    print(f"Train Sharpe: {result.avg_train_sharpe:.2f}")
    print(f"Test Sharpe: {result.avg_test_sharpe:.2f}")
    print(f"Degradation: {result.avg_degradation_pct:.1f}%")
```

### Strategy Validator

Complete validation pipeline:

```python
from trading_bot.ml.backtesting import StrategyValidator

validator = StrategyValidator(config.backtest_config)

# Validate single strategy
result = validator.validate(strategy, historical_data)

if result.passed:
    print(f"Strategy passed! Sharpe: {result.backtest_metrics.sharpe_ratio:.2f}")
else:
    print(f"Strategy failed: {result.failure_reasons}")

# Batch validate
results = validator.batch_validate(strategies, historical_data)
passed_strategies = [r.strategy for r in results if r.passed]
```

## Strategy Selection

### Selection Methods

**Top-N**: Select N best by fitness score
```python
selector = StrategySelector(config)
result = selector.select_top_n(strategies)
```

**Threshold**: Select all above threshold
```python
config.min_fitness_threshold = 60.0
result = selector.select_by_threshold(strategies)
```

**Pareto Frontier**: Multi-objective optimization
```python
result = selector.select_pareto_frontier(strategies)
```

**Diversity**: Maximize diversity while maintaining quality
```python
config.max_correlation = 0.7
result = selector.select_diverse(strategies, correlation_matrix)
```

### Full Selection

```python
from trading_bot.ml.selection import StrategySelector
from trading_bot.ml.config import SelectionConfig

config = SelectionConfig(
    selection_method="pareto",  # or "top_n", "threshold", "diversity"
    num_strategies_to_select=10,
    min_fitness_threshold=60.0,
    max_correlation=0.7,
)

selector = StrategySelector(config)
result = selector.select(validated_strategies, correlation_matrix=None)

print(f"Selected: {len(result.selected_strategies)}")
print(f"Rejected: {len(result.rejected_strategies)}")
```

## Ensemble Creation

### Weighting Methods

**Equal**: 1/N for each strategy
```python
ensemble = builder.create_ensemble(strategies, method="equal")
```

**Performance**: Weight by Sharpe ratio
```python
ensemble = builder.create_ensemble(strategies, method="performance")
```

**Kelly Criterion**: Optimal fractional Kelly
```python
ensemble = builder.create_ensemble(strategies, method="kelly")
```

**Inverse Volatility**: Weight by inverse volatility
```python
ensemble = builder.create_ensemble(strategies, method="inverse_volatility")
```

**Risk Parity**: Equal risk contribution
```python
ensemble = builder.create_ensemble(strategies, method="risk_parity")
```

### Full Ensemble

```python
from trading_bot.ml.selection import EnsembleBuilder

builder = EnsembleBuilder(config.selection_config)

ensemble = builder.create_ensemble(
    strategies=selected_strategies,
    name="ML_Portfolio_v1",
    method="kelly",
    correlation_matrix=corr_matrix,
)

print(f"Ensemble: {ensemble.name}")
print(f"Strategies: {len(ensemble.strategies)}")
print(f"Weights: {ensemble.weights}")
print(f"Expected Sharpe: {ensemble.metrics.sharpe_ratio:.2f}")
print(f"Expected MaxDD: {ensemble.metrics.max_drawdown:.1%}")
```

## Configuration

### ML Config

```python
from trading_bot.ml.config import MLConfig

config = MLConfig()

# Genetic Programming
config.gp_config.population_size = 2000
config.gp_config.num_generations = 50

# Backtesting
config.backtest_config.initial_capital = 100_000.0
config.backtest_config.walk_forward_windows = 10

# Selection
config.selection_config.selection_method = "pareto"
config.selection_config.num_strategies_to_select = 10

# Save config
config_dict = config.to_dict()
```

### Config File

Create `ml_config.json`:

```json
{
  "gp_config": {
    "population_size": 2000,
    "num_generations": 50,
    "mutation_rate": 0.15
  },
  "backtest_config": {
    "initial_capital": 100000,
    "walk_forward_windows": 10
  },
  "selection_config": {
    "selection_method": "pareto",
    "num_strategies_to_select": 10
  }
}
```

Load:
```python
import json
config = MLConfig.from_dict(json.load(open("ml_config.json")))
```

## Performance Metrics

### Strategy Metrics

All strategies tracked with:
- **Sharpe ratio**: Risk-adjusted returns (target: >1.5)
- **Max drawdown**: Peak-to-trough decline (target: <20%)
- **Win rate**: % profitable trades (target: >55%)
- **Profit factor**: Gross profit / gross loss (target: >1.5)
- **Avg win/loss ratio**: Average win / average loss (target: >1.5)
- **Recovery factor**: Total return / max drawdown
- **Sortino ratio**: Downside risk-adjusted
- **Calmar ratio**: Annual return / max drawdown

### Production Readiness

Strategies must pass:
```python
strategy.backtest_metrics.is_production_ready()
```

Criteria:
- Sharpe ratio >= 1.5
- Max drawdown <= 20%
- Win rate >= 50%
- Profit factor >= 1.5
- Num trades >= 30
- Consecutive losses <= 5

## Example Scripts

### Complete Pipeline

See `examples/ml_strategy_generation.py`:

```bash
python examples/ml_strategy_generation.py
```

### Custom Pipeline

```python
import pandas as pd
from trading_bot.ml.config import MLConfig
from trading_bot.ml.features import FeatureExtractor
from trading_bot.ml.generators import GeneticProgrammingGenerator
from trading_bot.ml.backtesting import StrategyValidator
from trading_bot.ml.selection import StrategySelector, EnsembleBuilder

# Load data
data = pd.read_csv("historical_data.csv", index_col=0, parse_dates=True)

# Configure
config = MLConfig()

# Generate
generator = GeneticProgrammingGenerator(config.gp_config)
strategies = generator.generate(100, data, {})

# Validate
validator = StrategyValidator(config.backtest_config)
results = validator.batch_validate(strategies, data)
passed = [r.strategy for r in results if r.passed]

# Select
selector = StrategySelector(config.selection_config)
selection = selector.select(passed)

# Ensemble
builder = EnsembleBuilder(config.selection_config)
ensemble = builder.create_ensemble(
    selection.selected_strategies,
    method="kelly"
)

print(f"Final ensemble Sharpe: {ensemble.metrics.sharpe_ratio:.2f}")
```

## Integration with Existing Bot

### Option 1: Replace Strategy

```python
from trading_bot.bot import TradingBot
from trading_bot.ml.models import StrategyEnsemble

bot = TradingBot()

# Load ML ensemble
ensemble = load_ensemble("ml_strategies/production/ensemble_v1.pkl")

# Use ensemble for signals
signal = ensemble.predict_signal(current_features)

if signal > 0.5:
    bot.enter_position("BUY")
elif signal < -0.5:
    bot.enter_position("SELL")
```

### Option 2: Parallel Execution

Run multiple strategies in parallel and aggregate signals.

## Best Practices

1. **Start Small**: Begin with 100-500 strategies, increase gradually
2. **Validate Rigorously**: Always use walk-forward optimization
3. **Diversify**: Select strategies with low correlation
4. **Monitor Degradation**: Track live vs backtest performance
5. **Retrain Regularly**: Regenerate strategies weekly/monthly
6. **Paper Trade First**: Test ensemble in paper trading for 30+ days
7. **Use Fractional Kelly**: Apply 25% Kelly for safety
8. **Cap Weights**: Max 30% per strategy for diversification

## Troubleshooting

### No Strategies Pass Validation

- Lower `min_fitness_threshold`
- Increase `population_size` or `num_generations`
- Reduce `min_trades_required`
- Check data quality

### All Strategies Overfit

- Increase `walk_forward_windows`
- Reduce strategy complexity (`max_tree_depth`)
- Add more training data
- Increase `parsimony_coefficient`

### Low Ensemble Sharpe

- Use better selection method (`pareto` or `diversity`)
- Increase `num_strategies_to_select`
- Adjust weighting method (`kelly` often best)
- Ensure low correlation between strategies

## TODO

- [ ] Integrate RL generator (stable-baselines3)
- [ ] Add pattern feature calculations
- [ ] Integrate sentiment from existing module
- [ ] Add database persistence for strategies
- [ ] Create API endpoints for ML management
- [ ] Add real-time performance monitoring
- [ ] Implement adaptive retraining
- [ ] Add multi-timeframe features

## References

- Genetic Programming: "A Field Guide to Genetic Programming" (Poli et al.)
- Walk-Forward: "Evidence-Based Technical Analysis" (Aronson)
- Kelly Criterion: "The Kelly Capital Growth Investment Criterion" (Thorp)
- Risk Parity: "Risk Parity Portfolios" (Maillard et al.)

## License

Same as parent project.
