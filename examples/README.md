# Examples Directory

This directory contains example scripts to help you get started with the trading bot's features.

---

## Table of Contents

- [Quick Start](#quick-start)
- [Backtesting Examples](#backtesting-examples)
- [Strategy Examples](#strategy-examples)
- [Dashboard Example](#dashboard-example)
- [Running Examples](#running-examples)
- [Example Output](#example-output)

---

## Quick Start

### Prerequisites

```bash
# Ensure you're in the project root
cd robinhood-algo-trading-bot

# Activate virtual environment
source venv/bin/activate  # Mac/Linux
venv\Scripts\activate      # Windows

# Install dependencies
pip install -r requirements.txt
```

---

## Backtesting Examples

### simple_backtest.py

**Purpose**: Run a backtest with a simple momentum strategy on historical data.

**What it does**:
- Fetches 1 year of historical OHLCV data for AAPL
- Applies a momentum strategy (10/30 MA crossover)
- Simulates trades with $100,000 starting capital
- Calculates performance metrics (total return, win rate, Sharpe ratio, max drawdown)

**Usage**:
```bash
python examples/simple_backtest.py
```

**Example Output**:
```
=== Backtest Results ===
Symbol: AAPL
Period: 2023-01-01 to 2023-12-31
Starting Capital: $100,000.00

Performance Metrics:
- Total Return: 23.45%
- Win Rate: 58.33%
- Total Trades: 24
- Winning Trades: 14
- Losing Trades: 10
- Sharpe Ratio: 1.52
- Max Drawdown: -8.23%
- Average Trade: +$976.25
- Largest Win: +$3,245.00
- Largest Loss: -$1,234.00

Recommendation: ✅ Strategy passes quality gates
```

**Customization**:

```python
# Edit simple_backtest.py

# Change symbol
config = BacktestConfig(
    symbol="TSLA",  # Try different stocks
    # ...
)

# Change date range
config = BacktestConfig(
    start_date=datetime(2022, 1, 1, tzinfo=timezone.utc),
    end_date=datetime(2022, 12, 31, tzinfo=timezone.utc),
    # ...
)

# Change initial capital
config = BacktestConfig(
    initial_capital=Decimal("50000")  # $50k
)
```

---

### strategy_comparison.py

**Purpose**: Compare multiple trading strategies side-by-side.

**What it does**:
- Runs backtests for multiple strategies on the same data
- Compares performance metrics
- Identifies the best strategy for the given period
- Generates comparison report

**Strategies compared**:
1. **Momentum Strategy**: 10/30 MA crossover
2. **VWAP Strategy**: Mean reversion around VWAP
3. **Support/Resistance**: Buy at support, sell at resistance

**Usage**:
```bash
python examples/strategy_comparison.py
```

**Example Output**:
```
=== Strategy Comparison Results ===

Testing period: 2023-01-01 to 2023-12-31
Symbol: AAPL
Starting capital: $100,000

Strategy              | Total Return | Win Rate | Sharpe | Max DD  | Trades
--------------------- | ------------ | -------- | ------ | ------- | ------
Momentum (10/30)      |    23.45%    |  58.33%  |  1.52  |  -8.23% |   24
VWAP Mean Reversion   |    18.67%    |  62.50%  |  1.34  |  -6.12% |   32
Support/Resistance    |    31.23%    |  55.00%  |  1.78  |  -9.45% |   20

🏆 Best Strategy: Support/Resistance (31.23% return, 1.78 Sharpe)

Recommendation: Use Support/Resistance strategy for AAPL in similar market conditions.
```

**Customization**:

```python
# Add your own strategy
from src.trading_bot.strategies import MyCustomStrategy

strategies = [
    ("Momentum", MomentumStrategy(short_window=10, long_window=30)),
    ("VWAP", VWAPStrategy()),
    ("My Strategy", MyCustomStrategy()),
]
```

---

## Strategy Examples

### sample_strategies.py

**Purpose**: Collection of pre-built trading strategies you can use as templates.

**Strategies included**:
1. **MomentumStrategy**: Moving average crossover
2. **BullFlagStrategy**: Identifies bull flag breakout patterns
3. **VWAPMeanReversionStrategy**: Trades around VWAP

**Usage as templates**:

```python
# Import from examples
from examples.sample_strategies import MomentumStrategy

# Create instance
strategy = MomentumStrategy(
    short_window=10,
    long_window=30
)

# Use in bot
bot.add_strategy(strategy)
```

**Code structure**:

```python
from src.trading_bot.strategies.base import Strategy

class MomentumStrategy(Strategy):
    def __init__(self, short_window: int, long_window: int):
        self.short_window = short_window
        self.long_window = long_window

    def should_enter(self, symbol: str, data: MarketData) -> bool:
        """Entry logic: Buy when short MA crosses above long MA."""
        # Calculate moving averages
        short_ma = data.calculate_sma(self.short_window)
        long_ma = data.calculate_sma(self.long_window)

        # Entry condition
        return short_ma > long_ma and self._was_below_recently(data)

    def should_exit(self, symbol: str, position: Position) -> bool:
        """Exit logic: Sell when short MA crosses below long MA."""
        # Similar logic for exits
        pass
```

---

### custom_strategy_example.py

**Purpose**: Complete example of how to create your own custom strategy from scratch.

**What's included**:
- Full strategy class implementation
- Entry/exit logic
- Risk management integration
- Backtest validation
- Usage examples

**Key sections**:

```python
# 1. Strategy definition
class CustomStrategy(Strategy):
    """Your custom trading logic."""
    pass

# 2. Entry conditions
def should_enter(self, symbol: str, data: MarketData) -> bool:
    # Your entry logic
    return condition_met

# 3. Exit conditions
def should_exit(self, symbol: str, position: Position) -> bool:
    # Your exit logic
    return should_close

# 4. Backtest validation
result = backtest_strategy(CustomStrategy(), "AAPL")
if result.sharpe_ratio >= 1.0:
    print("✅ Strategy validated")

# 5. Live usage
bot.add_strategy(CustomStrategy())
```

**Usage**:

```bash
# Run the example (includes backtest)
python examples/custom_strategy_example.py

# Use in your bot
from examples.custom_strategy_example import CustomStrategy
bot.add_strategy(CustomStrategy(param1=value1))
```

---

## Dashboard Example

### run_dashboard.py

**Purpose**: Launch a simple dashboard for monitoring bot performance.

**Features**:
- Real-time performance metrics
- Position tracking
- Trade history
- P&L chart
- Win rate visualization

**Usage**:

```bash
# Start dashboard
python examples/run_dashboard.py
```

**Access**: Opens browser to `http://localhost:3000`

**Requirements**:
```bash
# Additional dependencies for dashboard
pip install flask plotly pandas
```

**Dashboard sections**:
1. **Overview**: Health status, daily P&L, positions
2. **Performance**: Win rate, Sharpe ratio, drawdown chart
3. **Trades**: Recent trade history with details
4. **Charts**: P&L over time, cumulative returns

---

## Running Examples

### Method 1: Direct Execution

```bash
# From project root
python examples/simple_backtest.py
python examples/strategy_comparison.py
python examples/custom_strategy_example.py
```

### Method 2: As Module

```bash
# From project root
python -m examples.simple_backtest
python -m examples.strategy_comparison
```

### Method 3: Interactive (Python REPL)

```python
# Start Python
python

# Import and run
from examples.simple_backtest import run_backtest
result = run_backtest("AAPL", "2023-01-01", "2023-12-31")
print(f"Total Return: {result.metrics.total_return:.2%}")
```

---

## Example Output

### Successful Backtest

```
=== Backtest Results ===

Symbol: AAPL
Period: 2023-01-01 to 2023-12-31 (252 trading days)
Starting Capital: $100,000.00
Ending Capital: $123,450.00

Performance Metrics:
- Total Return: 23.45%
- Annualized Return: 23.45%
- Win Rate: 58.33% (14 wins / 24 trades)
- Average Win: $1,523.50
- Average Loss: -$823.25
- Risk/Reward Ratio: 1.85
- Sharpe Ratio: 1.52
- Max Drawdown: -8.23%
- Recovery Time: 15 days
- Total Trades: 24
- Profitable Months: 9/12 (75%)

Trade Details:
- Largest Win: $3,245.00 (AAPL on 2023-03-15)
- Largest Loss: -$1,234.00 (AAPL on 2023-06-22)
- Average Trade Duration: 3.2 days
- Win Streak (best): 5 trades
- Loss Streak (worst): 3 trades

Quality Gates:
✅ Sharpe Ratio ≥ 1.0 (1.52)
✅ Win Rate ≥ 55% (58.33%)
✅ Max Drawdown < 15% (-8.23%)
✅ Risk/Reward ≥ 1.5 (1.85)

Recommendation: Strategy passes all quality gates. Proceed to paper trading.
```

### Failed Backtest

```
=== Backtest Results ===

Symbol: TSLA
Period: 2023-01-01 to 2023-12-31
Starting Capital: $100,000.00
Ending Capital: $87,234.00

Performance Metrics:
- Total Return: -12.77%
- Win Rate: 42.31% (11 wins / 26 trades)
- Sharpe Ratio: 0.34
- Max Drawdown: -23.45%

Quality Gates:
❌ Sharpe Ratio < 1.0 (0.34)
❌ Win Rate < 55% (42.31%)
❌ Max Drawdown > 15% (-23.45%)

Recommendation: Strategy does NOT pass quality gates. Do not use in production.
Consider:
1. Adjusting strategy parameters
2. Testing on different symbols
3. Adding additional filters
```

---

## Modifying Examples

### Change Backtest Period

```python
# In simple_backtest.py
config = BacktestConfig(
    symbol="AAPL",
    start_date=datetime(2022, 1, 1, tzinfo=timezone.utc),  # Change year
    end_date=datetime(2022, 12, 31, tzinfo=timezone.utc),
    initial_capital=Decimal("100000")
)
```

### Change Strategy Parameters

```python
# In sample_strategies.py
strategy = MomentumStrategy(
    short_window=5,   # Faster response (was 10)
    long_window=20    # Shorter lookback (was 30)
)
```

### Test Multiple Symbols

```python
# Add loop to strategy_comparison.py
symbols = ["AAPL", "TSLA", "MSFT", "GOOGL"]

for symbol in symbols:
    result = run_comparison(symbol)
    print(f"{symbol}: {result.best_strategy} ({result.best_return:.2%})")
```

---

## Creating Your Own Example

### Template

Create `examples/my_example.py`:

```python
"""
My Example: Brief description
"""

from datetime import datetime, timezone
from decimal import Decimal

from src.trading_bot.backtest import BacktestEngine, BacktestConfig
from src.trading_bot.strategies import MyStrategy

def main():
    """Main function."""
    # 1. Configure backtest
    config = BacktestConfig(
        symbol="AAPL",
        start_date=datetime(2023, 1, 1, tzinfo=timezone.utc),
        end_date=datetime(2023, 12, 31, tzinfo=timezone.utc),
        initial_capital=Decimal("100000")
    )

    # 2. Create strategy
    strategy = MyStrategy()

    # 3. Run backtest
    engine = BacktestEngine(config)
    result = engine.run(strategy)

    # 4. Display results
    print(f"Total Return: {result.metrics.total_return:.2%}")
    print(f"Win Rate: {result.metrics.win_rate:.2%}")

if __name__ == "__main__":
    main()
```

---

## Best Practices

### Before Running Examples

1. **Test in paper trading first**: Never go straight to live trading
2. **Validate with backtests**: Ensure Sharpe ≥1.0, Win Rate ≥55%
3. **Test multiple periods**: Don't rely on single backtest
4. **Consider market conditions**: Bull vs. bear markets

### When Modifying Examples

1. **Make small changes**: Test one parameter at a time
2. **Document changes**: Add comments explaining modifications
3. **Keep original**: Save modified version with new name
4. **Version control**: Commit working versions

### Quality Gates

Before using a strategy in production:
- [ ] Backtest Sharpe Ratio ≥ 1.0
- [ ] Win Rate ≥ 55%
- [ ] Max Drawdown < 15%
- [ ] Risk/Reward ≥ 1.5
- [ ] Tested on multiple symbols
- [ ] Tested across multiple time periods
- [ ] Paper trading validation (1-2 weeks)

---

## Troubleshooting

### "No module named 'examples'"

**Solution**:
```bash
# Ensure you're in project root
cd robinhood-algo-trading-bot

# Run with python (not python3)
python examples/simple_backtest.py
```

### "Historical data fetch failed"

**Cause**: Network issue or API rate limiting

**Solution**:
```bash
# Retry after a few seconds
python examples/simple_backtest.py

# Or use cached data (if available)
```

### "Backtest taking too long"

**Cause**: Large date range or high-frequency data

**Solution**:
```python
# Reduce date range
config = BacktestConfig(
    start_date=datetime(2023, 6, 1),  # 6 months instead of 1 year
    end_date=datetime(2023, 12, 31),
)
```

---

## Next Steps

1. **Run simple_backtest.py** to understand backtest flow
2. **Try strategy_comparison.py** to compare strategies
3. **Study custom_strategy_example.py** to learn strategy structure
4. **Create your own strategy** using the template
5. **Validate with backtests** before paper trading
6. **Paper trade for 1-2 weeks** before live trading

---

## Additional Resources

- **Backtesting Docs**: `specs/001-backtesting-engine/spec.md`
- **Strategy Guide**: `specs/002-momentum-detection/spec.md`
- **Tutorial**: [docs/TUTORIAL.md](../docs/TUTORIAL.md)
- **API Documentation**: [docs/API.md](../docs/API.md)

---

**Last Updated**: 2025-10-26
**Examples**: 5 scripts (2 backtesting, 2 strategies, 1 dashboard)
