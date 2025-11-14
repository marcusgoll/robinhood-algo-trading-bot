# Quickstart: strategy-orchestrato

## Scenario 1: Initial Setup & Basic Usage

```bash
# Prerequisites: Existing backtest engine already functional
# No new dependencies required for MVP

# Verify existing backtest works
cd D:\Coding\Stocks
pytest tests/backtest/test_engine.py -v

# Create sample strategies for testing (if not exists)
# BuyAndHoldStrategy, MomentumStrategy already exist in test fixtures
```

**Python usage example**:
```python
from decimal import Decimal
from datetime import datetime, UTC
from trading_bot.backtest.orchestrator import StrategyOrchestrator
from trading_bot.backtest.models import OrchestratorConfig
from trading_bot.strategies.buy_and_hold import BuyAndHoldStrategy
from trading_bot.strategies.momentum import MomentumStrategy

# Setup orchestrator with 2 strategies (50/50 allocation)
orchestrator = StrategyOrchestrator(
    strategies=[
        (BuyAndHoldStrategy(), Decimal("0.50")),
        (MomentumStrategy(), Decimal("0.50"))
    ],
    config=OrchestratorConfig(logging_level="INFO")
)

# Load historical data (reuse existing HistoricalDataManager)
from trading_bot.backtest.historical_data_manager import HistoricalDataManager
data_manager = HistoricalDataManager()
bars = data_manager.load_data(
    symbols=["AAPL"],
    start_date=datetime(2023, 1, 1, tzinfo=UTC),
    end_date=datetime(2023, 12, 31, tzinfo=UTC)
)

# Run multi-strategy backtest
result = orchestrator.run(
    historical_data=bars,
    initial_capital=Decimal("100000.0")
)

# Access results
print(f"Portfolio Return: {result.aggregate_metrics.total_return:.2%}")
print(f"Portfolio Sharpe: {result.aggregate_metrics.sharpe_ratio:.2f}")

# Per-strategy breakdown
for strategy_id, strat_result in result.strategy_results.items():
    print(f"\n{strategy_id}:")
    print(f"  Return: {strat_result.metrics.total_return:.2%}")
    print(f"  Sharpe: {strat_result.metrics.sharpe_ratio:.2f}")
    print(f"  Trades: {strat_result.metrics.total_trades}")
```

---

## Scenario 2: Validation & Testing

```bash
# Run orchestrator unit tests
pytest tests/backtest/test_orchestrator.py -v

# Test specific user stories
pytest tests/backtest/test_orchestrator.py::test_us1_fixed_allocation -v
pytest tests/backtest/test_orchestrator.py::test_us2_independent_tracking -v
pytest tests/backtest/test_orchestrator.py::test_us3_capital_limits -v

# Run integration tests (full workflow)
pytest tests/backtest/test_orchestrator_integration.py -v

# Check test coverage (target: ≥90%)
pytest --cov=trading_bot.backtest.orchestrator --cov-report=term tests/backtest/test_orchestrator.py

# Type checking
cd src && mypy trading_bot/backtest/orchestrator.py

# Linting
ruff check src/trading_bot/backtest/orchestrator.py
```

---

## Scenario 3: Manual Testing - Capital Limits

**Setup**: Create scenario where one strategy hits capital limit

```python
from decimal import Decimal
from trading_bot.backtest.orchestrator import StrategyOrchestrator

# Aggressive strategy that trades frequently
class AggressiveStrategy:
    def should_enter(self, bars):
        return True  # Always wants to enter

    def should_exit(self, position, bars):
        return False  # Holds forever

# Conservative strategy
class ConservativeStrategy:
    def should_enter(self, bars):
        return len(bars) == 50  # Only enters once

    def should_exit(self, position, bars):
        return False

# Allocate 30% to aggressive, 70% to conservative
orchestrator = StrategyOrchestrator(
    strategies=[
        (AggressiveStrategy(), Decimal("0.30")),
        (ConservativeStrategy(), Decimal("0.70"))
    ]
)

result = orchestrator.run(
    historical_data=bars,
    initial_capital=Decimal("100000.0")
)

# Verify aggressive strategy blocked after using 30% capital
assert result.capital_limit_blocks > 0, "Expected capital limit blocks"
print(f"Capital limit blocks: {result.capital_limit_blocks}")

# Check logs for capital limit warnings
# logs/backtest/*.jsonl should contain orchestrator.capital_limit_hit events
```

---

## Scenario 4: Performance Comparison Report

```python
# Generate comparison report
from trading_bot.backtest.orchestrator import StrategyOrchestrator

orchestrator = StrategyOrchestrator(
    strategies=[
        (BuyAndHoldStrategy(), Decimal("0.25")),
        (MomentumStrategy(), Decimal("0.25")),
        (RSIStrategy(), Decimal("0.25")),
        (MeanReversionStrategy(), Decimal("0.25"))
    ]
)

result = orchestrator.run(historical_data=bars, initial_capital=Decimal("100000.0"))

# Access comparison table (FR-013)
comparison = result.comparison_table
# Example output:
# {
#   "BuyAndHoldStrategy_0": {
#     "total_return": 0.12,
#     "sharpe_ratio": 0.85,
#     "win_rate": 0.60,
#     "max_drawdown": -0.15
#   },
#   "MomentumStrategy_0": {
#     "total_return": 0.18,
#     "sharpe_ratio": 1.20,
#     "win_rate": 0.55,
#     "max_drawdown": -0.20
#   },
#   ...
# }

# Print formatted comparison
print("Strategy Comparison Report")
print("=" * 80)
print(f"{'Strategy':<30} {'Return':<10} {'Sharpe':<10} {'Win Rate':<10} {'Max DD':<10}")
print("-" * 80)
for strategy_id, metrics in comparison.items():
    print(f"{strategy_id:<30} "
          f"{metrics['total_return']:>9.2%} "
          f"{metrics['sharpe_ratio']:>9.2f} "
          f"{metrics['win_rate']:>9.2%} "
          f"{metrics['max_drawdown']:>9.2%}")
```

---

## Scenario 5: Debugging - Event Logs

**Check structured logs for orchestrator events**:

```bash
# View all orchestrator events
grep '"event":"orchestrator\.' logs/backtest/*.jsonl | jq .

# Check for backtest starts
grep '"event":"orchestrator.backtest_started"' logs/backtest/*.jsonl | jq .

# Find capital limit hits
grep '"event":"orchestrator.capital_limit_hit"' logs/backtest/*.jsonl | jq '{strategy_id, used_capital, allocation_limit, symbol}'

# Identify failed backtests
grep '"event":"orchestrator.backtest_failed"' logs/backtest/*.jsonl | jq '{error_type, error_message, strategy_id}'

# Calculate adoption rate
total_backtests=$(grep '"event":"backtest' logs/backtest/*.jsonl | wc -l)
orchestrator_backtests=$(grep '"event":"orchestrator.backtest' logs/backtest/*.jsonl | wc -l)
echo "Orchestrator adoption: $orchestrator_backtests / $total_backtests"
```

---

## Scenario 6: Migration from Single-Strategy

**Migrate existing single-strategy backtest to orchestrator**:

```python
# Before (single strategy)
from trading_bot.backtest.engine import BacktestEngine
from trading_bot.backtest.models import BacktestConfig

config = BacktestConfig(
    strategy_class=MomentumStrategy,
    symbols=["AAPL"],
    start_date=start,
    end_date=end,
    initial_capital=Decimal("100000.0")
)
engine = BacktestEngine(config)
result = engine.run(strategy=MomentumStrategy(), historical_data=bars)

# After (orchestrator with single strategy)
from trading_bot.backtest.orchestrator import StrategyOrchestrator

orchestrator = StrategyOrchestrator(
    strategies=[(MomentumStrategy(), Decimal("1.0"))]  # 100% allocation
)
result = orchestrator.run(
    historical_data=bars,
    initial_capital=Decimal("100000.0")
)

# Access results (same BacktestResult structure)
momentum_result = result.strategy_results["MomentumStrategy_0"]
print(f"Return: {momentum_result.metrics.total_return:.2%}")
```

---

## Common Workflows

### Add New Strategy to Portfolio
```python
# Step 1: Define strategy implementing IStrategy
class NewStrategy:
    def should_enter(self, bars): ...
    def should_exit(self, position, bars): ...

# Step 2: Add to orchestrator
orchestrator = StrategyOrchestrator(
    strategies=[
        (ExistingStrategy1(), Decimal("0.30")),
        (ExistingStrategy2(), Decimal("0.30")),
        (NewStrategy(), Decimal("0.40"))  # New strategy
    ]
)

# Step 3: Run and compare
result = orchestrator.run(historical_data=bars, initial_capital=Decimal("100000"))
new_strategy_metrics = result.strategy_results["NewStrategy_0"].metrics
```

### Optimize Strategy Weights
```python
# Test different weight combinations
weight_combos = [
    [Decimal("0.50"), Decimal("0.50")],
    [Decimal("0.70"), Decimal("0.30")],
    [Decimal("0.30"), Decimal("0.70")]
]

best_return = Decimal("-999")
best_weights = None

for weights in weight_combos:
    orchestrator = StrategyOrchestrator(
        strategies=[
            (Strategy1(), weights[0]),
            (Strategy2(), weights[1])
        ]
    )
    result = orchestrator.run(historical_data=bars, initial_capital=Decimal("100000"))
    if result.aggregate_metrics.total_return > best_return:
        best_return = result.aggregate_metrics.total_return
        best_weights = weights

print(f"Best weights: {best_weights}, Return: {best_return:.2%}")
```
