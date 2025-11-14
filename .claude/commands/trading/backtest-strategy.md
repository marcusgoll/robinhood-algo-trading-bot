# /backtest-strategy - Strategy Backtesting

Run comprehensive backtests on trading strategies with historical data and parameter optimization.

## Objective

Validate trading strategies using historical data, calculate performance metrics, test parameter sensitivity, and provide data-driven recommendations for strategy refinement.

## Usage

```bash
/backtest-strategy SYMBOL --start-date YYYY-MM-DD --end-date YYYY-MM-DD [--initial-capital AMOUNT] [--optimize PARAM]
```

**Options:**
- `SYMBOL`: Stock symbol to backtest (required)
- `--start-date`: Backtest start date (required)
- `--end-date`: Backtest end date (required)
- `--initial-capital`: Starting capital (default: 10000)
- `--optimize PARAM`: Run parameter sensitivity test (e.g., "rsi_oversold", "stop_loss_pct")

## Process

1. **Validate Inputs**
   - Check symbol exists via `get_quote`
   - Verify date range is valid (not future dates)
   - Ensure sufficient historical data available via `get_historical`
   - Validate capital amount > 0

2. **Run Base Backtest**
   - Use `run_backtest` with default strategy parameters:
     - RSI oversold: 30, overbought: 70
     - MACD: 12, 26, 9
     - Stop loss: 2% below entry
     - Take profit: 3% above entry (1.5:1 R:R)
     - Max position size: 100 shares
     - Risk per trade: 2% of capital
   - Collect all trade results and equity curve

3. **Calculate Performance Metrics**
   - Use `calculate_metrics` to compute:
     - Total return and annualized return
     - Sharpe ratio and Sortino ratio
     - Max drawdown and drawdown duration
     - Win rate and profit factor
     - Average win/loss and largest win/loss
     - Total trades and trade frequency
     - Risk-adjusted metrics

4. **Generate Trade Analysis**
   - Best/worst trades
   - Win/loss streaks
   - Time-based performance (day of week, hour of day)
   - Holding period analysis
   - Drawdown periods

5. **Parameter Optimization (if --optimize specified)**
   - Use `test_parameter_sensitivity` to test variations:
     - RSI oversold: [25, 30, 35, 40]
     - RSI overbought: [60, 65, 70, 75]
     - Stop loss %: [1.5, 2.0, 2.5, 3.0]
     - Take profit %: [2.0, 3.0, 4.0, 5.0]
     - Position size: [50, 100, 150, 200]
   - Identify optimal parameter value based on Sharpe ratio
   - Compare optimal vs default performance

6. **Risk Analysis**
   - Validate strategy follows risk rules:
     - Max drawdown < 20%
     - Win rate > 40%
     - Profit factor > 1.3
     - Average loss < 2.5% of capital
   - Check for edge (positive expected value)

7. **Return JSON Report**

```json
{
  "symbol": "AAPL",
  "backtest_period": "2023-01-01 to 2024-01-01",
  "initial_capital": 10000,
  "final_capital": 11847.50,
  "base_strategy": {
    "parameters": {
      "rsi_oversold": 30,
      "rsi_overbought": 70,
      "stop_loss_pct": 2.0,
      "take_profit_pct": 3.0,
      "max_position_size": 100
    },
    "performance": {
      "total_return": 1847.50,
      "total_return_pct": 18.48,
      "annualized_return_pct": 18.48,
      "sharpe_ratio": 1.65,
      "sortino_ratio": 2.12,
      "max_drawdown": -487.30,
      "max_drawdown_pct": -4.87,
      "drawdown_duration_days": 12,
      "volatility": 0.12
    },
    "trades": {
      "total_trades": 42,
      "winning_trades": 26,
      "losing_trades": 16,
      "win_rate": 61.9,
      "profit_factor": 2.18,
      "avg_win": 125.40,
      "avg_loss": -68.20,
      "largest_win": 385.50,
      "largest_loss": -145.30,
      "avg_holding_period_hours": 18.5,
      "max_consecutive_wins": 6,
      "max_consecutive_losses": 3
    }
  },
  "optimization": {
    "parameter": "stop_loss_pct",
    "tested_values": [1.5, 2.0, 2.5, 3.0],
    "results": [
      {"value": 1.5, "sharpe": 1.42, "return_pct": 15.2, "win_rate": 58.3},
      {"value": 2.0, "sharpe": 1.65, "return_pct": 18.5, "win_rate": 61.9},
      {"value": 2.5, "sharpe": 1.58, "return_pct": 17.8, "win_rate": 64.2},
      {"value": 3.0, "sharpe": 1.38, "return_pct": 16.1, "win_rate": 66.7}
    ],
    "optimal_value": 2.0,
    "improvement_vs_default": 0.0
  },
  "risk_assessment": {
    "passes_risk_rules": true,
    "edge_detected": true,
    "expected_value_per_trade": 43.98,
    "risk_of_ruin": 0.02,
    "kelly_criterion": 0.24,
    "flags": []
  },
  "trade_examples": {
    "best_trade": {
      "entry_date": "2023-03-15",
      "entry_price": 148.50,
      "exit_date": "2023-03-16",
      "exit_price": 154.35,
      "pnl": 385.50,
      "return_pct": 3.94,
      "reason": "Strong momentum breakout"
    },
    "worst_trade": {
      "entry_date": "2023-08-22",
      "entry_price": 175.20,
      "exit_date": "2023-08-22",
      "exit_price": 171.68,
      "pnl": -145.30,
      "return_pct": -2.01,
      "reason": "Hit stop loss on earnings miss"
    }
  },
  "recommendations": [
    "Strategy shows positive edge with 61.9% win rate",
    "Sharpe ratio of 1.65 indicates good risk-adjusted returns",
    "Stop loss at 2.0% appears optimal for this strategy",
    "Max drawdown of 4.87% is well within acceptable limits",
    "Consider reducing position size to 75 shares for lower volatility"
  ],
  "warnings": []
}
```

## Optimization Modes

When `--optimize` is specified, test these parameters:

- **rsi_oversold**: Test [25, 30, 35, 40] to find optimal entry threshold
- **rsi_overbought**: Test [60, 65, 70, 75] to find optimal exit threshold
- **stop_loss_pct**: Test [1.5, 2.0, 2.5, 3.0] to balance risk/reward
- **take_profit_pct**: Test [2.0, 3.0, 4.0, 5.0] to optimize exit timing
- **position_size**: Test [50, 100, 150, 200] to find optimal sizing

## Risk Rules

Strategy FAILS if:
- Max drawdown > 20%
- Win rate < 40%
- Profit factor < 1.3
- Sharpe ratio < 0.5
- Expected value per trade < 0

## Output Format

Return structured JSON with:
- Base strategy performance
- Parameter optimization results (if requested)
- Risk assessment with pass/fail
- Example trades (best/worst)
- Actionable recommendations

## Visualization Data

Include equity curve data for charting:
```json
"equity_curve": [
  {"date": "2023-01-01", "equity": 10000, "drawdown_pct": 0},
  {"date": "2023-01-02", "equity": 10125, "drawdown_pct": 0},
  {"date": "2023-01-03", "equity": 10087, "drawdown_pct": -0.38}
]
```

## Error Handling

- If symbol not found, return error with suggestion
- If insufficient historical data, return error with min required period
- If backtest fails, return partial results with warning
- If parameter optimization takes > 30s, return base results only

## Performance Target

- Base backtest: < 10 seconds
- With optimization: < 30 seconds
- Cache historical data (24 hour TTL)
- Cost: ~$0.0008 per execution (base), ~$0.0015 with optimization

## Notes

- This command **does not execute trades** - backtest only
- Results are based on historical data - past performance doesn't guarantee future results
- Strategy uses simple momentum indicators - may need customization per symbol
- Backtests assume no slippage or commission (adjust expectations accordingly)
- Designed for **strategy validation before live deployment**

## Example Invocations

From Python:
```python
# Base backtest
result = manager.invoke("/backtest-strategy AAPL --start-date 2023-01-01 --end-date 2024-01-01")

# With optimization
result = manager.invoke("/backtest-strategy TSLA --start-date 2023-06-01 --end-date 2024-06-01 --optimize stop_loss_pct")
```

From CLI:
```bash
# Base backtest
claude -p "/backtest-strategy SPY --start-date 2023-01-01 --end-date 2024-01-01" --model haiku --output-format json

# Year-long backtest with capital
claude -p "/backtest-strategy QQQ --start-date 2023-01-01 --end-date 2024-01-01 --initial-capital 25000" --model haiku --output-format json
```

## Integration with /review-performance

Use this command to validate strategies before deployment, then use `/review-performance` to track live performance. Compare backtest metrics to live metrics to detect strategy degradation.
