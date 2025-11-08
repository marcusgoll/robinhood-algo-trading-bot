# /optimize-entry - Position Optimization (Stocks & Crypto)

Optimize entry price, position size, and stop/target levels for an existing or proposed trade.

## Usage
```bash
/optimize-entry SYMBOL --entry PRICE [--asset-type {stock|crypto}] [--current-position SHARES|USD]
```

**Parameters:**
- `SYMBOL`: Symbol to optimize (e.g., AAPL for stocks, BTC/USD for crypto)
- `--entry`: Proposed entry price
- `--asset-type`: Asset type (default: auto-detect from symbol)
- `--current-position`: Existing position (shares for stocks, USD for crypto)

## Process

1. **Get Current State**
   - `get_quote` for real-time price
   - `get_position_details` if existing position
   - `calculate_indicators` for ATR, support/resistance

2. **Calculate Optimal Entry**
   - If not in position: Wait for pullback to SMA 20 or support
   - If in position: Calculate average-down opportunity
   - Consider: Volume profile, order book depth, spread

3. **Optimize Position Size**
   - `calculate_max_position_size` with 2% risk rule
   - `get_buying_power` to verify capital available
   - Adjust for existing exposure (`get_portfolio_exposure`)

4. **Set Stop/Target Levels**
   - Stop Loss: Support level or entry - (2 * ATR)
   - Target 1: Resistance or entry + (3 * ATR) [R:R 1.5:1]
   - Target 2: Next resistance or entry + (5 * ATR) [R:R 2.5:1]

5. **Return JSON**
   ```json
   {
     "symbol": "AAPL",
     "optimization": {
       "recommended_entry": 149.80,
       "current_price": 150.50,
       "entry_discount_pct": 0.47,
       "position_size": 65,
       "position_value": 9737.00,
       "stop_loss": 145.60,
       "target_1": 154.20,
       "target_2": 157.90,
       "risk_reward": 2.4
     },
     "scaling_plan": {
       "entry_1": {"price": 149.80, "shares": 40, "reason": "Initial entry at support"},
       "entry_2": {"price": 148.50, "shares": 25, "reason": "Add on pullback to SMA 20"}
     }
   }
   ```

## Cost: ~$0.0004 per execution
