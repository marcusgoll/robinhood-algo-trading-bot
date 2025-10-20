# Quickstart: backtesting-engine

## Scenario 1: Initial Setup

```bash
# Install dependencies (if not already installed)
pip install -e ".[backtest]"

# Or for development
pip install -e ".[dev,backtest]"

# Set up environment variables
cat >> .env <<EOF
BACKTEST_DATA_SOURCE=alpaca
BACKTEST_CACHE_DIR=.backtest_cache/
YAHOO_FINANCE_ENABLED=true

# Alpaca credentials (required for historical data)
ALPACA_API_KEY=your_api_key_here
ALPACA_SECRET_KEY=your_secret_key_here
ALPACA_PAPER=true  # Use paper trading endpoint
EOF

# Create cache directory
mkdir -p .backtest_cache

# Verify installation
python -c "from trading_bot.backtest import BacktestEngine; print('Backtest module loaded successfully')"
```

## Scenario 2: Run Simple Backtest

```python
# examples/simple_backtest.py
from trading_bot.backtest import BacktestEngine, BacktestConfig
from trading_bot.strategies import BuyAndHoldStrategy  # Example strategy
from datetime import datetime, UTC

# Configure backtest
config = BacktestConfig(
    strategy_class=BuyAndHoldStrategy,
    symbols=["AAPL"],
    start_date=datetime(2023, 1, 1, tzinfo=UTC),
    end_date=datetime(2024, 1, 1, tzinfo=UTC),
    initial_capital=100000.0,
    commission=0.0,  # Robinhood has no commission
    slippage_pct=0.001  # 0.1% slippage
)

# Run backtest
engine = BacktestEngine(config)
result = engine.run()

# Print summary
print(f"\n=== Backtest Results ===")
print(f"Total Trades: {result.metrics.total_trades}")
print(f"Win Rate: {result.metrics.win_rate:.2%}")
print(f"Total Return: {result.metrics.total_return:.2%}")
print(f"CAGR: {result.metrics.cagr:.2%}")
print(f"Sharpe Ratio: {result.metrics.sharpe_ratio:.2f}")
print(f"Max Drawdown: {result.metrics.max_drawdown:.2%}")
print(f"Profit Factor: {result.metrics.profit_factor:.2f}")
print(f"Execution Time: {result.execution_time_seconds:.2f}s")

# Generate markdown report
from trading_bot.backtest import ReportGenerator
generator = ReportGenerator()
generator.generate_markdown(result, "specs/001-backtesting-engine/backtest-report.md")
print(f"\nReport saved to: specs/001-backtesting-engine/backtest-report.md")
```

Run the backtest:
```bash
python examples/simple_backtest.py
```

## Scenario 3: Implement Custom Strategy

```python
# trading_bot/strategies/momentum_strategy.py
from typing import Protocol
from decimal import Decimal
from trading_bot.backtest.models import HistoricalDataBar, Position

class MomentumStrategy:
    """Simple momentum strategy based on 20-day moving average."""

    def __init__(self, lookback_days: int = 20):
        self.lookback_days = lookback_days
        self.price_history = []

    def should_enter(self, symbol: str, bar: HistoricalDataBar, cash: Decimal) -> bool:
        """Enter when price crosses above 20-day MA."""
        self.price_history.append(float(bar.close))

        # Need at least lookback_days of history
        if len(self.price_history) < self.lookback_days:
            return False

        # Keep only last N days
        self.price_history = self.price_history[-self.lookback_days:]

        # Calculate moving average
        ma = sum(self.price_history) / len(self.price_history)

        # Enter if price > MA and have sufficient cash
        min_position_size = 100  # $100 minimum
        return float(bar.close) > ma and cash >= min_position_size

    def should_exit(self, position: Position, bar: HistoricalDataBar) -> bool:
        """Exit when price crosses below 20-day MA."""
        if len(self.price_history) < self.lookback_days:
            return False

        ma = sum(self.price_history) / len(self.price_history)

        # Exit if price < MA
        return float(bar.close) < ma
```

Test the custom strategy:
```python
from trading_bot.backtest import BacktestEngine, BacktestConfig
from trading_bot.strategies import MomentumStrategy

config = BacktestConfig(
    strategy_class=MomentumStrategy,
    symbols=["AAPL"],
    start_date=datetime(2023, 1, 1, tzinfo=UTC),
    end_date=datetime(2024, 1, 1, tzinfo=UTC)
)

engine = BacktestEngine(config)
result = engine.run()
```

## Scenario 4: Validation and Testing

```bash
# Run unit tests for backtest module
pytest tests/backtest/ -v

# Run tests with coverage
pytest tests/backtest/ --cov=src/trading_bot/backtest --cov-report=html

# Check types
mypy src/trading_bot/backtest/

# Lint code
ruff check src/trading_bot/backtest/

# Security check
bandit -r src/trading_bot/backtest/

# Run all quality checks (matches constitution requirements)
pytest tests/backtest/ --cov=src/trading_bot/backtest --cov-fail-under=90 && \
  mypy src/trading_bot/backtest/ && \
  ruff check src/trading_bot/backtest/ && \
  bandit -r src/trading_bot/backtest/
```

## Scenario 5: Compare Multiple Strategies

```python
# examples/strategy_comparison.py
from trading_bot.backtest import BacktestEngine, BacktestConfig
from trading_bot.strategies import BuyAndHoldStrategy, MomentumStrategy
from datetime import datetime, UTC

strategies = [
    ("Buy and Hold", BuyAndHoldStrategy),
    ("Momentum (20-day)", MomentumStrategy),
]

results = {}

for name, strategy_class in strategies:
    config = BacktestConfig(
        strategy_class=strategy_class,
        symbols=["AAPL"],
        start_date=datetime(2023, 1, 1, tzinfo=UTC),
        end_date=datetime(2024, 1, 1, tzinfo=UTC),
    )

    engine = BacktestEngine(config)
    result = engine.run()
    results[name] = result

# Compare results
print("\n=== Strategy Comparison ===")
print(f"{'Strategy':<20} {'Total Return':<15} {'Sharpe Ratio':<15} {'Max DD':<15}")
print("-" * 70)

for name, result in results.items():
    print(f"{name:<20} {result.metrics.total_return:>13.2%} "
          f"{result.metrics.sharpe_ratio:>14.2f} "
          f"{result.metrics.max_drawdown:>13.2%}")
```

## Scenario 6: Manual Testing Checklist

After implementing backtest module, validate manually:

1. **Data Loading**
   - [ ] Run backtest for AAPL from 2023-01-01 to 2024-01-01
   - [ ] Verify cache directory `.backtest_cache/` is created
   - [ ] Check parquet file exists: `.backtest_cache/AAPL_2023-01-01_2024-01-01.parquet`
   - [ ] Re-run same backtest, verify it uses cached data (faster)

2. **Strategy Execution**
   - [ ] Implement simple buy-and-hold strategy
   - [ ] Verify it enters on first bar
   - [ ] Verify it holds until last bar
   - [ ] Check final P&L matches: (last_price - first_price) / first_price

3. **Performance Metrics**
   - [ ] Win rate is between 0 and 1
   - [ ] Total trades count matches number of Trade objects
   - [ ] Sharpe ratio is calculated (not NaN)
   - [ ] Max drawdown is between 0 and 1

4. **Report Generation**
   - [ ] Markdown report generated at `specs/001-backtesting-engine/backtest-report.md`
   - [ ] Report includes all sections from template
   - [ ] Trade list is complete and chronological
   - [ ] Equity curve data is present

5. **Data Quality**
   - [ ] Run backtest with missing data period (e.g., market holiday)
   - [ ] Verify warning appears in `result.data_warnings`
   - [ ] Check backtest handles gap gracefully (skips period)

6. **Error Handling**
   - [ ] Try backtest with invalid symbol (e.g., "INVALID")
   - [ ] Verify error message is clear
   - [ ] Try backtest with end_date < start_date
   - [ ] Verify validation error is raised

7. **Performance**
   - [ ] Run backtest for 1 year (252 trading days)
   - [ ] Verify completion time < 30 seconds (NFR-001)
   - [ ] Check memory usage is reasonable (< 500MB for 1 year)

8. **Constitution Compliance**
   - [ ] Run test coverage: `pytest --cov=src/trading_bot/backtest --cov-report=term`
   - [ ] Verify coverage >= 90% (§Pre_Deploy quality gate)
   - [ ] Run mypy: `mypy src/trading_bot/backtest/`
   - [ ] Verify no type errors (§Code_Quality)
   - [ ] Check all API keys loaded from env vars (§Security)
