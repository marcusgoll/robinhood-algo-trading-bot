# Quickstart: Position Scaling & Phase Progression

## Scenario 1: Initial Setup (Development)

### Prerequisites
- Python 3.11+ installed
- Trading bot repository cloned
- Virtual environment activated

### Setup Steps
```bash
# Install dependencies (if not already done)
pip install -r requirements.txt

# Verify phase configuration exists
cat config.json | jq '.phase_progression'
# Should show: {"current_phase": "experience"}

# Create phase logs directory
mkdir -p logs/phase

# Run validation tests
pytest tests/phase/ -v

# Verify performance tracking works
python -m trading_bot.performance generate --window daily
```

**Expected State**:
- config.json has `phase_progression.current_phase = "experience"`
- logs/phase/ directory exists
- All tests pass
- Performance summary generates without errors

---

## Scenario 2: Phase Transition Validation (Manual Testing)

### Experience → Proof of Concept

```bash
# Check current phase
python -c "from trading_bot.config import Config; c=Config.from_env_and_json(); print(f'Current phase: {c.current_phase}')"

# Simulate 20 profitable paper trading sessions
python -m trading_bot.phase simulate-sessions --count 20 --win-rate 0.65 --avg-rr 1.6

# Validate transition criteria
python -m trading_bot.phase validate-transition --to proof
# Expected output:
# ✅ Session count: 20/20 (met)
# ✅ Win rate: 0.65 (≥0.60 required)
# ✅ Avg R:R: 1.6 (≥1.5 required)
# ✅ Ready to advance to Proof of Concept

# Advance phase (requires validation pass)
python -m trading_bot.phase advance --to proof
# Expected: Phase transition logged to logs/phase/phase-history.jsonl

# Verify mode switcher allows live trading
python -c "from trading_bot.config import Config; from trading_bot.mode_switcher import ModeSwitcher; \
c=Config.from_env_and_json(); ms=ModeSwitcher(c); \
status=ms.get_status(); print(f'Can switch to live: {status.can_switch_to_live}')"
# Expected: True (PoC allows live trading)
```

### Proof of Concept Daily Trade Limit

```bash
# Place first trade of day (should succeed)
python -m trading_bot.bot execute-trade --symbol AAPL --action buy --shares 10
# Expected: Trade executed successfully

# Attempt second trade (should block)
python -m trading_bot.bot execute-trade --symbol TSLA --action buy --shares 5
# Expected error:
# ❌ Trade limit exceeded: 1/1 trades today (Proof of Concept phase)
# Next trade allowed at: 2025-10-22 07:00:00 EST

# Verify override log
tail -1 logs/phase/phase-overrides.jsonl
# Should show blocked attempt
```

### Automatic Downgrade Trigger

```bash
# Simulate 3 consecutive losses
python -m trading_bot.phase simulate-trades --outcomes loss,loss,loss

# Check phase status (should auto-downgrade)
python -c "from trading_bot.config import Config; c=Config.from_env_and_json(); print(f'Phase after losses: {c.current_phase}')"
# Expected: "experience" (downgraded from "proof")

# Check circuit breaker status
python -c "from trading_bot.error_handling import circuit_breaker; print(f'Should trip: {circuit_breaker.should_trip()}')"
# Expected: True (manual restart required)

# Verify phase-history.jsonl logged downgrade
tail -1 logs/phase/phase-history.jsonl | jq '.trigger, .from_phase, .to_phase'
# Expected: "auto", "proof", "experience"
```

---

## Scenario 3: Validation (Automated Testing)

### Run Unit Tests
```bash
# All phase module tests
pytest tests/phase/ -v --cov=src/trading_bot/phase --cov-report=term-missing

# Specific test categories
pytest tests/phase/test_validators.py -v  # Phase transition validation
pytest tests/phase/test_trade_limiter.py -v  # Daily trade limits
pytest tests/phase/test_manager.py -v  # PhaseManager orchestration
pytest tests/phase/test_models.py -v  # Data model validation

# Expected: 90%+ coverage, all tests pass
```

### Run Integration Tests
```bash
# Phase transition workflow
pytest tests/phase/test_phase_workflow.py::test_full_phase_progression -v
# Tests: Experience → PoC → Trial → Scaling with real metrics

# Downgrade scenarios
pytest tests/phase/test_phase_workflow.py::test_automatic_downgrade_triggers -v
# Tests: Consecutive losses, win rate drop, daily loss triggers

# Trade limit enforcement
pytest tests/phase/test_integration.py::test_poc_trade_limit_enforcement -v
# Tests: 1 trade/day limit, emergency exit override

# Expected: All integration tests pass
```

### Type Checking & Linting
```bash
# Type checking
mypy src/trading_bot/phase/

# Linting
ruff check src/trading_bot/phase/

# Security scan
bandit -r src/trading_bot/phase/

# Expected: No errors, no high-severity issues
```

---

## Scenario 4: Manual Testing (Paper Trading Validation)

### Day 1-20: Experience Phase
```bash
# Start bot in paper trading mode
python -m trading_bot.main --mode paper --phase experience

# Monitor trade execution
tail -f logs/trades-$(date +%Y-%m-%d).jsonl

# Check daily session metrics
python -m trading_bot.performance generate --window daily

# Review phase progression status
python -m trading_bot.phase status
# Expected output:
# Current Phase: Experience (Paper Trading)
# Sessions completed: 5/20
# Win rate: 0.58 (target: 0.60)
# Avg R:R: 1.4 (target: 1.5)
# Status: ⚠️  Not ready to advance (criteria not met)
```

### After Meeting Criteria
```bash
# Validate advancement
python -m trading_bot.phase validate-transition --to proof
# Expected: ✅ Ready to advance

# Advance to Proof of Concept
python -m trading_bot.phase advance --to proof --confirm
# Confirmation prompt: "Advancing to PoC allows live trading. Continue? (y/n)"

# Verify config updated
cat config.json | jq '.phase_progression.current_phase'
# Expected: "proof"

# Check phase history
python -m trading_bot.phase export --format json | jq '.transitions[-1]'
# Expected: Last transition to "proof" with metrics snapshot
```

---

## Scenario 5: Export & Reporting

### Export Phase History
```bash
# Export to CSV
python -m trading_bot.phase export --start 2025-10-01 --end 2025-10-31 --format csv --output phase-report-oct.csv

# CSV columns:
# date, phase, trades, wins, losses, win_rate, avg_rr, total_pnl, position_size, notes

# Export to JSON
python -m trading_bot.phase export --format json --output phase-history.json

# JSON structure:
# {
#   "current_phase": "proof",
#   "transitions": [...],
#   "sessions": [...],
#   "overrides": [...]
# }
```

### View Phase Progression Timeline
```bash
# Generate Markdown report
python -m trading_bot.phase report --output phase-report.md

# Report includes:
# - Phase timeline with dates
# - Session metrics per phase
# - Transition history
# - Profitability summary
# - Downgrade events (if any)
```

---

## Troubleshooting

### Phase Won't Advance
```bash
# Check validation details
python -m trading_bot.phase validate-transition --to <target_phase> --verbose

# Common issues:
# - Insufficient sessions: Wait for more trading days
# - Win rate too low: Review strategy performance
# - Missing data: Check logs/trades-*.jsonl files exist
```

### Trade Limit Not Resetting
```bash
# Check market open time
python -c "from trading_bot.config import Config; c=Config.from_env_and_json(); \
print(f'Trading hours: {c.trading_start_time} - {c.trading_end_time} {c.trading_timezone}')"

# Manually reset (for testing only)
python -m trading_bot.phase reset-trade-limit --date $(date +%Y-%m-%d)
```

### Circuit Breaker Stuck
```bash
# Check circuit breaker status
python -c "from trading_bot.error_handling import circuit_breaker; \
print(f'Failures: {len(circuit_breaker._failures)}')"

# Manual reset (after addressing errors)
python -m trading_bot.bot reset-circuit-breaker
```

---

## Configuration Reference

### Minimal config.json
```json
{
  "trading": {"mode": "paper"},
  "phase_progression": {
    "current_phase": "experience"
  }
}
```

### Full config.json (All Phases)
```json
{
  "trading": {"mode": "paper"},
  "phase_progression": {
    "current_phase": "experience",
    "experience": {
      "max_trades_per_day": 999,
      "advancement_criteria": {
        "min_sessions": 20,
        "min_win_rate": 0.60,
        "min_avg_rr": 1.5
      }
    },
    "proof": {
      "max_trades_per_day": 1,
      "position_size": 100,
      "advancement_criteria": {
        "min_sessions": 30,
        "min_trades": 50,
        "min_win_rate": 0.65,
        "min_avg_rr": 1.8
      },
      "downgrade_triggers": {
        "consecutive_losses": 3,
        "rolling_win_rate_min": 0.55,
        "max_daily_loss_pct": 5.0
      }
    },
    "trial": {
      "max_trades_per_day": 999,
      "position_size": 200,
      "advancement_criteria": {
        "min_sessions": 60,
        "min_trades": 100,
        "min_win_rate": 0.70,
        "min_avg_rr": 2.0,
        "max_drawdown_pct": 5.0
      },
      "downgrade_triggers": {
        "consecutive_losses": 3,
        "rolling_win_rate_min": 0.55,
        "max_daily_loss_pct": 5.0
      }
    },
    "scaling": {
      "max_trades_per_day": 999,
      "position_size_min": 200,
      "position_size_max": 2000,
      "maintain_criteria": {
        "min_win_rate": 0.70,
        "min_avg_rr": 2.0
      },
      "downgrade_triggers": {
        "consecutive_losses": 3,
        "rolling_win_rate_min": 0.55,
        "max_daily_loss_pct": 5.0
      }
    }
  }
}
```

---

## Next Steps

After completing quickstart scenarios:

1. **Production Deployment**: Update `.env` with ROBINHOOD credentials
2. **Phase Monitoring**: Set up daily cron job for session metrics
3. **Alert Configuration**: Configure phase downgrade notifications
4. **Backup Strategy**: Regular backups of phase-history.jsonl
