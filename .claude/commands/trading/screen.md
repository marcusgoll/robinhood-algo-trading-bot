# /screen - Market Screening (Stocks & Crypto)

Scan for high-momentum trading opportunities using real-time market data.

## Objective

Use MCP tools to identify assets (stocks or crypto) with strong momentum, volume, and technical setups.
- **Stocks:** Day trading during 7am-10am EST window
- **Crypto:** 24/7 screening for BTC, ETH, and top altcoins

## Usage

```bash
/screen [--asset-type {stock|crypto}] [--symbols SYMBOL1,SYMBOL2,...]
```

**Parameters:**
- `--asset-type`: Asset type to screen (default: stock)
  - `stock`: Screen stocks during market hours
  - `crypto`: Screen crypto symbols 24/7
- `--symbols`: Override default symbols (crypto only)

## Process

### For Stocks (--asset-type stock)

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

4. **Apply Stock Filters**
   - RSI: 45-70 (bullish momentum, not overbought)
   - MACD: Histogram positive (bullish)
   - ATR: >= 0.5 (sufficient volatility)
   - Price trend: Upward over last 5 days

### For Crypto (--asset-type crypto)

1. **Market is Always Open** (24/7)
   - Skip market status check
   - Note: Crypto markets never close

2. **Get Symbols List**
   - Default: BTC/USD, ETH/USD, LTC/USD, BCH/USD, LINK/USD, UNI/USD, AVAX/USD, MATIC/USD
   - Or use `--symbols` parameter to override

3. **Fetch Crypto Data**
   - For each symbol:
     - Use `get_crypto_quote` for current bid/ask, volume
     - Use `get_crypto_bars` (24 hours, 1 hour interval) for trend
     - Use `calculate_indicators` for RSI, MACD, ATR

4. **Apply Crypto Filters** (More permissive due to volatility)
   - RSI: 30-75 (wider range for crypto volatility)
   - MACD: Histogram positive OR recent bullish crossover
   - 24h Volume: >= 150% of 7-day average (high activity)
   - Price trend: Upward over last 12 hours
   - ATR: No minimum (crypto naturally volatile)

5. **Risk Assessment**

   **For Stocks:**
   - Use `calculate_position_risk`:
     - Assume 100 share position
     - entry_price: current price
     - stop_loss: price - (2 * ATR)
   - Filter out any with risk_pct > 2%

   **For Crypto:**
   - Use `calculate_position_risk`:
     - Assume $100 USD position (fractional crypto)
     - entry_price: current mid-price (bid+ask)/2
     - stop_loss: price - (2 * ATR) OR -5% (whichever is wider)
   - Filter out any with risk_pct > 5% (wider tolerance for crypto)

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

**Stock Screening (Default):**
```python
# From Python orchestrator
manager = ClaudeCodeManager(config)
result = manager.invoke("/screen")

# From CLI
claude -p "/screen" --model haiku --output-format json
```

**Crypto Screening:**
```python
# From Python orchestrator (default symbols)
result = manager.invoke("/screen --asset-type crypto")

# Custom symbols
result = manager.invoke("/screen --asset-type crypto --symbols BTC/USD,ETH/USD,SOL/USD")

# From CLI
claude -p "/screen --asset-type crypto" --model haiku --output-format json
```

## Notes

**For Stocks:**
- Designed for **pre-market** and **market open** use (7am-10am EST)
- Results are time-sensitive - cache for max 60 seconds
- Always check buying_power before recommending positions

**For Crypto:**
- Runs 24/7 (no market hours restriction)
- Higher volatility tolerance (wider RSI range, larger stops)
- Default 8 symbols: BTC/USD, ETH/USD, LTC/USD, BCH/USD, LINK/USD, UNI/USD, AVAX/USD, MATIC/USD
- Results cache for 120 seconds (crypto moves faster)

**Cost:**
- Stocks: ~$0.0003 per execution (15 candidates)
- Crypto: ~$0.0002 per execution (8 symbols fixed)
