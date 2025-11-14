# /analyze-trade - Trade Signal Analysis (Stocks & Crypto)

Analyze a potential trade setup and provide entry/exit recommendations with risk assessment.

## Objective

Evaluate a specific asset (stock or crypto) for trade entry using technical analysis, risk metrics, and portfolio context.

## Usage

```bash
/analyze-trade SYMBOL [--asset-type {stock|crypto}] [--entry-price PRICE] [--stop-loss PRICE] [--target PRICE]
```

**Parameters:**
- `SYMBOL`: Symbol to analyze (e.g., AAPL for stocks, BTC/USD for crypto)
- `--asset-type`: Asset type (default: auto-detect from symbol format)
  - `stock`: Stock analysis (market hours, 2% risk tolerance)
  - `crypto`: Crypto analysis (24/7, 5% risk tolerance)
- `--entry-price`: Proposed entry price (optional)
- `--stop-loss`: Proposed stop loss price (optional)
- `--target`: Proposed target price (optional)

## Process

1. **Validate Symbol**
   - Use `get_quote` to fetch current price and volume
   - Check if market is open (use `get_market_status`)
   - Verify minimum volume (>500K shares/day)

2. **Technical Analysis**
   - Use `calculate_indicators` to get:
     - RSI (14-period)
     - MACD (12, 26, 9)
     - ATR (14-period)
     - SMA 20, SMA 50
     - EMA 12, EMA 26
   - Use `get_historical` (30 days, 1 day interval) for:
     - Support/resistance levels
     - Trend direction
     - Volume profile

3. **Entry Signal Evaluation**

   **For Stocks:**
   - **Bullish Setup Criteria:**
     - RSI: 45-70 (momentum without overbought)
     - MACD: Histogram positive and increasing
     - Price above SMA 20 (short-term uptrend)
     - Volume: Above 20-day average
     - ATR: >= 0.5 (sufficient volatility)
   - **Pattern Recognition:**
     - Bull flag / pennant
     - Breakout above resistance
     - Higher lows forming
     - Golden cross (EMA 12 > EMA 26)

   **For Crypto:**
   - **Bullish Setup Criteria:**
     - RSI: 30-75 (wider range due to volatility)
     - MACD: Histogram positive OR recent bullish crossover
     - Price above EMA 20 (short-term momentum)
     - 24h Volume: >= 150% of 7-day average
     - ATR: Any (crypto always volatile)
   - **Pattern Recognition:**
     - Ascending triangle
     - Breakout with volume spike
     - Bullish divergence (price down, RSI up)
     - EMA 12/26 bullish alignment

4. **Risk Assessment**

   **For Stocks:**
   - Calculate stop loss (if not provided):
     - Technical: Support level or price - (2 * ATR)
     - Maximum: -3% from entry
   - Calculate position size:
     - Use `get_buying_power` to check available capital
     - Use `calculate_max_position_size` with entry and stop
     - Ensure risk per trade <= 2% of portfolio
   - Use `check_trade_rules` to validate against risk limits

   **For Crypto:**
   - Calculate stop loss (if not provided):
     - Technical: Support level or price - (2 * ATR)
     - Maximum: -5% from entry (wider for crypto volatility)
   - Calculate position size:
     - Fixed $100 USD positions (fractional trading)
     - Or use `calculate_max_position_size` for dynamic sizing
     - Ensure risk per trade <= 5% of crypto allocation
   - Skip portfolio exposure checks (crypto tracked separately)

5. **Portfolio Context**
   - Use `get_positions` to check existing holdings
   - Use `get_portfolio_exposure` to check sector concentration
   - Verify this trade won't create over-concentration (>15% in any position)

6. **Generate Recommendation**
   - Return JSON with detailed analysis:
   ```json
   {
     "symbol": "AAPL",
     "timestamp": "ISO timestamp",
     "market_status": "open",
     "current_price": 150.50,
     "analysis": {
       "signal": "STRONG_BUY|BUY|HOLD|AVOID",
       "confidence": 85,
       "technical_score": 78,
       "risk_score": 65,
       "rationale": "Breaking above resistance with strong volume and positive MACD divergence"
     },
     "indicators": {
       "rsi": 62,
       "macd": {"line": 1.25, "signal": 0.85, "histogram": 0.40},
       "atr": 2.15,
       "sma_20": 148.20,
       "sma_50": 145.10,
       "trend": "UPTREND"
     },
     "recommendation": {
       "action": "BUY",
       "entry_price": 150.50,
       "stop_loss": 146.20,
       "target_1": 154.30,
       "target_2": 157.80,
       "position_size_shares": 50,
       "position_size_usd": 7525.00,
       "risk_amount": 215.00,
       "risk_pct": 1.2,
       "reward_risk_ratio": 2.8
     },
     "warnings": [
       "Market volatility is elevated (VIX > 20)",
       "Approaching overbought on RSI - watch for reversal"
     ]
   }
   ```

## Signal Strength Levels

- **STRONG_BUY** (80-100): All criteria met, high confidence
- **BUY** (60-79): Most criteria met, moderate confidence
- **HOLD** (40-59): Mixed signals, wait for better setup
- **AVOID** (0-39): Bearish signals or high risk

## Risk Filters

Automatically **AVOID** if:
- RSI > 75 (overbought)
- MACD histogram negative and declining
- Price below SMA 50 (downtrend)
- Volume < 50% of average (low liquidity)
- Would create position > 15% of portfolio
- Risk per trade > 2% of portfolio
- Sector exposure > 30% after trade

## Output Format

Return structured JSON with:
- Signal strength and confidence
- Technical indicators
- Entry/exit prices
- Position sizing
- Risk metrics
- Warnings (if any)

## Example Invocation

**Stock Analysis:**
```python
# From Python
result = manager.invoke("/analyze-trade AAPL --entry-price 150.50")

# From CLI
claude -p "/analyze-trade TSLA" --model haiku --output-format json
```

**Crypto Analysis:**
```python
# From Python (auto-detect from symbol)
result = manager.invoke("/analyze-trade BTC/USD")

# Explicit asset type
result = manager.invoke("/analyze-trade ETH/USD --asset-type crypto --entry-price 2500")

# From CLI
claude -p "/analyze-trade BTC/USD --asset-type crypto" --model haiku --output-format json
```

## Error Handling

- If symbol not found, return error
- If market closed (stocks only), analyze but note prices are stale
- If insufficient data, return partial analysis with warning
- If crypto exchange offline, return error with retry suggestion

## Performance Target

- Complete analysis in < 5 seconds
- Use indicator caching (5-minute TTL)
- Cost: ~$0.0005 per execution

## Notes

**General:**
- This command **does not execute trades** - only provides analysis
- Respects existing risk management rules
- Always check portfolio context before recommendations

**Stocks:**
- Designed for **intraday momentum trading** (7am-10am EST window)
- 2% max risk per trade
- Position sizing based on buying power

**Crypto:**
- 24/7 analysis (no market hours restriction)
- 5% max risk per trade (wider tolerance for volatility)
- Fixed $100 positions or dynamic sizing
- Crypto tracked separately from stock portfolio
