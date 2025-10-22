# Quickstart: daily-profit-goal-ma

## Scenario 1: Initial Setup

```bash
# Navigate to project root
cd D:/Coding/Stocks

# Configure profit target (optional - feature disabled by default)
# Option A: Environment variable
export PROFIT_TARGET_DAILY=500.00
export PROFIT_GIVEBACK_THRESHOLD=0.50

# Option B: Add to .env file
echo "PROFIT_TARGET_DAILY=500.00" >> .env
echo "PROFIT_GIVEBACK_THRESHOLD=0.50" >> .env

# Option C: Add to config.json
# (see contracts/config-schema.json for structure)

# No migrations needed (file-based persistence)
# No dependencies needed (uses existing packages)

# Start bot (feature auto-initializes)
python -m trading_bot.bot
```

## Scenario 2: Validation

```bash
# Run unit tests
pytest tests/unit/profit_goal/ -v --cov=src/trading_bot/profit_goal --cov-report=term-missing

# Check type safety
mypy src/trading_bot/profit_goal/ --strict

# Verify configuration loading
python -c "from trading_bot.profit_goal.config import load_profit_goal_config; print(load_profit_goal_config())"

# Check state file after first trade
cat logs/profit-goal-state.json
```

## Scenario 3: Manual Testing

### Test Case 1: Profit protection trigger
1. **Setup**: Configure target=$500, threshold=50%
2. **Action**: Execute trades to reach $600 daily profit (peak)
3. **Trigger**: Execute losing trade(s) to drop P&L to $300
4. **Verify**:
   - Check `logs/profit-goal-state.json` → `protection_active: true`
   - Check `logs/profit-protection/YYYY-MM-DD.jsonl` → Event logged
   - Attempt new buy order → Should be blocked by SafetyChecks

### Test Case 2: Trade blocking during protection
1. **Prerequisite**: Protection active (from Test Case 1)
2. **Action**: Attempt to enter new position
   ```python
   from trading_bot.safety_checks import SafetyChecks
   from trading_bot.config import Config

   config = Config.from_env_and_json()
   safety = SafetyChecks(config)
   result = safety.validate_trade("AAPL", "BUY", 100, 150.00, 10000.00)

   print(result.is_safe)  # Expected: False
   print(result.reason)   # Expected: "Profit protection active - new entries blocked"
   ```
3. **Verify**: Trade blocked with profit protection reason

### Test Case 3: Daily reset at market open
1. **Setup**: Bot running overnight with protection active
2. **Time**: Wait until 4:00 AM EST (or simulate by modifying state file timestamp)
3. **Action**: Bot detects new market day, triggers reset
4. **Verify**:
   - Check `logs/profit-goal-state.json`:
     - `session_date` updated to new date
     - `daily_pnl`, `realized_pnl`, `unrealized_pnl` reset to 0
     - `peak_profit` reset to 0
     - `protection_active` reset to False
     - `last_reset` timestamp updated

### Test Case 4: Manual override (exit during protection)
1. **Prerequisite**: Protection active, open positions exist
2. **Action**: Manually exit position (SELL order)
3. **Verify**:
   - Exit allowed (protection only blocks new entries, not exits per FR-007)
   - Trade logged to `logs/trades/YYYY-MM-DD.jsonl`
   - State updated with new P&L values

## Scenario 4: Monitoring

```bash
# Check current profit goal status
python -c "
from trading_bot.profit_goal.tracker import DailyProfitTracker
tracker = DailyProfitTracker()
state = tracker.get_current_state()
print(f'Daily P&L: ${state.daily_pnl}')
print(f'Peak: ${state.peak_profit}')
print(f'Protection: {state.protection_active}')
"

# Query protection events
grep '"event":"protection_triggered"' logs/profit-protection/*.jsonl | jq .

# Calculate protection trigger rate
grep '"event":"protection_triggered"' logs/profit-protection/*.jsonl | wc -l

# Check average profit saved by protection
grep '"event":"protection_triggered"' logs/profit-protection/*.jsonl | jq '{peak, current, saved: (.peak - .current)}' | jq -s 'map(.saved) | add / length'
```

## Scenario 5: Troubleshooting

### Issue: Protection not triggering when expected
```bash
# Check configuration loaded correctly
python -c "from trading_bot.profit_goal.config import load_profit_goal_config; config=load_profit_goal_config(); print(f'Target: {config.target}, Threshold: {config.threshold}, Enabled: {config.enabled}')"

# Verify state file accuracy
cat logs/profit-goal-state.json | jq '{daily_pnl, peak_profit, protection_active}'

# Check P&L calculation
python -c "
from trading_bot.performance.tracker import PerformanceTracker
tracker = PerformanceTracker()
summary = tracker.get_summary('daily')
print(f'Realized: {summary.realized_pnl}')
print(f'Unrealized: {summary.unrealized_pnl}')
"
```

### Issue: State file corrupt after bot crash
```bash
# Check state file validity
cat logs/profit-goal-state.json | jq . > /dev/null 2>&1 && echo "Valid JSON" || echo "Corrupt JSON"

# Manual state reset (emergency only)
cp logs/profit-goal-state.json logs/profit-goal-state.json.backup
echo '{"session_date": "2025-10-21", "daily_pnl": "0.00", "realized_pnl": "0.00", "unrealized_pnl": "0.00", "peak_profit": "0.00", "protection_active": false, "last_reset": "2025-10-21T09:00:00Z", "last_updated": "2025-10-21T09:00:00Z"}' > logs/profit-goal-state.json
```
