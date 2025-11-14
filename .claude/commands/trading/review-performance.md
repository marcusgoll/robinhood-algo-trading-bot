# /review-performance - Trading Performance Review

Analyze trading performance metrics and generate actionable insights for improvement.

## Objective

Review recent trading activity, calculate performance metrics, identify patterns in wins/losses, and provide recommendations for strategy refinement.

## Usage

```bash
/review-performance [--period DAYS] [--detailed]
```

**Options:**
- `--period DAYS`: Number of days to review (default: 7)
- `--detailed`: Include individual trade analysis

## Process

1. **Fetch Trade History**
   - Use `get_trade_history` with period parameter
   - Group trades by day and by symbol
   - Calculate time-weighted metrics

2. **Calculate Performance Metrics**
   - Use `calculate_metrics` from backtest MCP server:
     - Total P&L and P&L %
     - Win rate and profit factor
     - Average win vs average loss
     - Sharpe ratio (if sufficient data)
     - Max drawdown
     - Largest win/loss
   - Daily breakdown with cumulative equity curve

3. **Analyze Risk Adherence**
   - Use `get_risk_metrics` to check:
     - Average risk per trade vs 2% rule
     - Maximum position size violations
     - Sector concentration breaches
   - Flag any risk rule violations

4. **Pattern Recognition**
   - Identify winning patterns:
     - Best performing entry times
     - Most profitable symbols/sectors
     - Optimal hold times
     - Common indicators in winning trades
   - Identify losing patterns:
     - Worst entry times
     - Symbols with consistent losses
     - Emotional trades (deviation from plan)
     - Common mistakes

5. **Generate Recommendations**
   - Based on analysis, provide:
     - Strategy adjustments (if win rate < 45%)
     - Risk management improvements
     - Entry/exit timing refinements
     - Symbols to avoid/focus on
     - Psychological insights (overtrading, revenge trading, etc.)

6. **Return JSON Report**

```json
{
  "period": "2024-01-15 to 2024-01-22",
  "summary": {
    "total_trades": 28,
    "winning_trades": 15,
    "losing_trades": 13,
    "win_rate": 53.6,
    "total_pnl": 487.32,
    "total_pnl_pct": 4.87,
    "avg_win": 52.40,
    "avg_loss": -28.15,
    "profit_factor": 1.86,
    "largest_win": 125.50,
    "largest_loss": -62.30,
    "sharpe_ratio": 1.42,
    "max_drawdown": -156.20,
    "max_drawdown_pct": -1.56
  },
  "daily_breakdown": [
    {
      "date": "2024-01-15",
      "trades": 4,
      "pnl": 85.20,
      "pnl_pct": 0.85,
      "win_rate": 75.0
    }
  ],
  "risk_adherence": {
    "avg_risk_per_trade_pct": 1.8,
    "max_position_size_breaches": 0,
    "sector_concentration_breaches": 1,
    "violations": [
      "Tech sector reached 32% on 2024-01-18 (limit: 30%)"
    ]
  },
  "patterns": {
    "winning": [
      "78% win rate when entering 9:35-9:50 AM",
      "AAPL trades: 6/7 wins (85.7%)",
      "Trades with RSI 50-65: 83% win rate"
    ],
    "losing": [
      "5/5 losses when entering after 10:30 AM",
      "TSLA trades: 1/4 wins (25%)",
      "Trades ignoring stop loss: 4/4 losses"
    ]
  },
  "recommendations": [
    "Focus entries between 9:35-9:50 AM - highest win rate window",
    "Consider avoiding TSLA - consistent underperformance",
    "Strictly enforce stop losses - all violations resulted in losses",
    "Reduce tech exposure to stay within 30% sector limit",
    "Win rate above 50% is healthy - continue current strategy"
  ],
  "psychological_notes": [
    "No revenge trading detected",
    "Position sizing discipline maintained",
    "1 stop loss violation on 2024-01-18 - review emotional state"
  ]
}
```

## Visualization Suggestions

If detailed mode enabled, include:
- Equity curve chart data (daily cumulative P&L)
- Drawdown chart data
- Win/loss distribution histogram
- Hourly performance heatmap
- Symbol performance comparison

## Signal Thresholds

- **Excellent**: Win rate > 55%, Profit factor > 2.0, Sharpe > 1.5
- **Good**: Win rate 50-55%, Profit factor 1.5-2.0, Sharpe 1.0-1.5
- **Acceptable**: Win rate 45-50%, Profit factor 1.2-1.5, Sharpe 0.5-1.0
- **Needs Improvement**: Win rate < 45%, Profit factor < 1.2, Sharpe < 0.5

## Output Format

Return structured JSON with:
- Summary metrics (P&L, win rate, Sharpe, drawdown)
- Daily breakdown
- Risk adherence report
- Pattern analysis (winning/losing)
- Actionable recommendations
- Psychological insights

## Error Handling

- If no trades in period, return message: "No trades found in period"
- If insufficient data for Sharpe ratio, omit it with note
- If trade history API fails, return cached/partial data with warning

## Performance Target

- Complete analysis in < 8 seconds
- Cache daily metrics (refresh every 4 hours)
- Cost: ~$0.0006 per execution

## Notes

- This command **analyzes past performance only** - does not execute trades
- Recommendations are based on historical patterns - not guarantees
- Always validate against portfolio context and risk rules
- Review should inform strategy adjustments, not override risk management
- Designed for **end-of-day or weekly review** (best after 4pm EST)

## Example Invocation

From Python:
```python
result = manager.invoke("/review-performance --period 7")
```

From CLI:
```bash
claude -p "/review-performance --period 14 --detailed" --model haiku --output-format json
```
