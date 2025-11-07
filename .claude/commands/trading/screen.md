# /screen - Pre-Market Stock Screening

Scan for high-momentum trading opportunities using real-time market data.

## Objective

Use MCP tools to identify stocks with strong momentum, volume, and technical setups suitable for day trading during the 7am-10am EST window.

## Process

1. **Check Market Status**
   - Use `get_market_status` to verify market is open or pre-market
   - If closed, inform user when market opens next

2. **Run Momentum Scan**
   - Use `scan_momentum` with these criteria:
     - min_volume: 1,000,000 shares
     - min_price: $5.00
     - max_price: $500.00
     - limit: 15 results
   - Sort results by momentum_score (highest first)

3. **Enrich Top Candidates**
   - For top 5 results, gather additional data:
     - Use `get_quote` for current price and volume
     - Use `calculate_indicators` for RSI, MACD, ATR
     - Use `get_historical` (7 days, 1 day interval) for trend context

4. **Apply Filters**
   - RSI: 45-70 (bullish momentum, not overbought)
   - MACD: Histogram positive (bullish)
   - ATR: >= 0.5 (sufficient volatility)
   - Price trend: Upward over last 5 days

5. **Risk Assessment**
   - For each candidate, use `calculate_position_risk`:
     - Assume 100 share position
     - entry_price: current price
     - stop_loss: price - (2 * ATR)
   - Filter out any with risk_pct > 2%

6. **Generate Watchlist**
   - Return JSON with top 3-5 symbols:
   ```json
   {
     "timestamp": "ISO timestamp",
     "market_status": "pre-market|open|closed",
     "scan_criteria": {...},
     "watchlist": [
       {
         "symbol": "AAPL",
         "price": 150.50,
         "momentum_score": 85,
         "indicators": {
           "rsi": 62,
           "macd_histogram": 0.45,
           "atr": 2.15
         },
         "risk_assessment": {
           "entry_price": 150.50,
           "stop_loss": 146.20,
           "risk_pct": 1.2,
           "risk_rating": "LOW"
         },
         "rationale": "Strong momentum with healthy RSI, positive MACD, breaking above resistance"
       }
     ],
     "filtered_out": 10,
     "total_scanned": 15
   }
   ```

## Output Format

Return structured JSON (as shown above) with:
- Market status
- Scan criteria used
- Watchlist (3-5 symbols max)
- Brief rationale for each pick
- Count of filtered candidates

## Error Handling

- If MCP tools fail, return error with fallback suggestion
- If no symbols meet criteria, return empty watchlist with explanation
- If market closed, show next open time

## Performance Target

- Complete scan in < 10 seconds
- Use caching where possible (market status, historical data)
- Minimize API calls by batching tool requests

## Example Invocation

From Python orchestrator:
```python
manager = ClaudeCodeManager(config)
result = manager.invoke("/screen")
```

From CLI:
```bash
claude -p "/screen" --model haiku --output-format json
```

## Notes

- This command is designed for **pre-market** and **market open** use
- Results are time-sensitive - cache for max 60 seconds
- Always check buying_power before recommending positions
- Respect $5/day budget - this command costs ~$0.0003 per execution
