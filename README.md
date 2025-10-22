# Robinhood Trading Bot

A Python-based algorithmic trading bot using the `robin_stocks` library, built with safety and risk management as top priorities.

**⚠️ DISCLAIMER**: This bot is for **personal educational use only**. Not financial advice. You are responsible for all trading decisions and tax reporting.

---

## 🛡️ Constitution v1.0.0

This project follows strict development principles defined in [`.specify/memory/constitution.md`](.specify/memory/constitution.md):

- **§Safety_First**: Paper trading by default, circuit breakers, audit logging
- **§Code_Quality**: Type hints required, 90% test coverage, KISS/DRY principles
- **§Risk_Management**: Position limits, mandatory stop losses, input validation
- **§Security**: No credentials in code, encrypted API keys, minimal permissions
- **§Testing_Requirements**: Unit, integration, backtesting, and paper trading before real money

---

## 📊 Backtesting Engine

Validate trading strategies against historical market data before deploying to paper or live trading. The backtesting engine simulates strategy execution chronologically to ensure realistic performance evaluation.

### Quick Start

```python
from src.trading_bot.backtest import BacktestEngine, BacktestConfig, HistoricalDataManager
from examples.sample_strategies import MomentumStrategy
from datetime import datetime, timezone
from decimal import Decimal

# Configure backtest
config = BacktestConfig(
    symbol="AAPL",
    start_date=datetime(2023, 1, 1, tzinfo=timezone.utc),
    end_date=datetime(2023, 12, 31, tzinfo=timezone.utc),
    initial_capital=Decimal("100000")
)

# Fetch historical data
data_manager = HistoricalDataManager()
historical_data = data_manager.fetch_data(
    config.symbol, config.start_date, config.end_date
)

# Run backtest
strategy = MomentumStrategy(short_window=10, long_window=30)
engine = BacktestEngine(config)
result = engine.run(strategy, historical_data)

# View results
print(f"Total Return: {result.metrics.total_return:.2%}")
print(f"Win Rate: {result.metrics.win_rate:.2%}")
print(f"Sharpe Ratio: {result.metrics.sharpe_ratio:.2f}")
```

### Documentation

- [Feature Specification](specs/001-backtesting-engine/spec.md)
- [Implementation Plan](specs/001-backtesting-engine/plan.md)
- [Usage Examples](examples/)

### Example Strategies

- [Simple Backtest](examples/simple_backtest.py)
- [Strategy Comparison](examples/strategy_comparison.py)
- [Custom Strategy](examples/custom_strategy_example.py)

---

## 📍 Support/Resistance Zone Mapping

Identify key price levels where institutional and retail traders commonly place orders. Zone mapping improves entry timing, sets realistic profit targets, and helps avoid low-probability trades between zones.

### Quick Start

```python
from src.trading_bot.support_resistance import (
    ZoneDetector, ProximityChecker, ZoneDetectionConfig, Timeframe
)
from decimal import Decimal

# Configure zone detection
config = ZoneDetectionConfig.from_env()
detector = ZoneDetector(config, market_data_service)
checker = ProximityChecker(config)

# Detect zones from 60 days of daily data
zones = detector.detect_zones("AAPL", days=60, timeframe=Timeframe.DAILY)

# Check if current price is near any zones
current_price = Decimal("152.00")
alerts = checker.check_proximity("AAPL", current_price, zones)

# Review strongest zones
for zone in zones[:5]:  # Top 5 by strength
    print(f"{zone.zone_type.value} at ${zone.price_level}: strength {zone.strength_score}")
```

### Features

**Support/Resistance Zone Mapping**:
- **Swing Point Detection**: 5-bar lookback algorithm identifies swing highs/lows
- **Zone Clustering**: Groups nearby pivots within 1.5% tolerance
- **Strength Scoring**: Touch count + volume bonus (>1.5x average volume)
- **Proximity Alerts**: Automatic alerts when price within 2% of zones
- **Multi-Timeframe**: Daily (3+ touches) and 4-hour (2+ touches) support
- **Real-Time Integration**: Uses MarketDataService for OHLCV data from Robinhood API

**Zone Breakout Detection** (v1.4.0):
- **Automated Breakout Detection**: Identifies when price closes above resistance zones by >1% with volume >1.3x average
- **Zone Flipping**: Converts resistance zones to support zones upon confirmed breakouts with strength bonuses
- **Event Logging**: Structured JSONL logging of all breakout events with full context
- **Configurable Thresholds**: Price movement, volume confirmation, validation bars, and strength bonuses
- **High Performance**: 0.0155ms single check (12,903x faster than target)
- **Production Ready**: 84.68% test coverage, zero vulnerabilities, full type safety

### Configuration

Add to your `.env` file (optional overrides):

```bash
# Zone detection thresholds
ZONE_TOUCH_THRESHOLD=3           # Minimum touches for daily zones (default: 3)
ZONE_PRICE_TOLERANCE_PCT=1.5     # Price clustering tolerance (default: 1.5%)
ZONE_PROXIMITY_THRESHOLD_PCT=2.0 # Proximity alert threshold (default: 2%)
ZONE_VOLUME_THRESHOLD_MULT=1.5   # Volume bonus threshold (default: 1.5x)

# Breakout detection thresholds (v1.4.0)
BREAKOUT_PRICE_THRESHOLD_PCT=1.0 # Price movement threshold % (default: 1.0)
BREAKOUT_VOLUME_THRESHOLD=1.3    # Volume multiplier threshold (default: 1.3)
BREAKOUT_VALIDATION_BARS=5       # Whipsaw validation window (default: 5)
BREAKOUT_STRENGTH_BONUS=2.0      # Strength score bonus on flip (default: 2.0)
```

### Use Cases

1. **Entry Timing**: Wait for price to approach strong support zones before entering bull flag patterns
2. **Profit Targets**: Set exits near resistance zones instead of fixed R:R ratios
3. **Risk Management**: Place stop losses below strong support zones for logical protection
4. **Trade Filtering**: Avoid entries in "no-man's land" between major zones

### Documentation

- [Feature Specification](specs/023-support-resistance-mapping/spec.md)
- [Implementation Plan](specs/023-support-resistance-mapping/plan.md)
- [Deployment Guide](specs/023-support-resistance-mapping/deployment-finalization.md)

### Quality Metrics

- **Tests**: 69/69 passing (100%)
- **Coverage**: proximity_checker 97.5%, models 100%, logger 100%
- **Performance**: Zone detection <1s (90 days), Proximity check <1ms
- **Security**: 0 vulnerabilities (Bandit scan)

---

## 💰 Daily Profit Goal Management

Automated profit protection to prevent overtrading and profit giveback. Tracks daily P&L, detects when you've given back 50% of peak profit, and automatically blocks new entries while allowing exits to preserve gains.

### Quick Start

```python
from src.trading_bot.profit_goal import DailyProfitTracker, load_profit_goal_config

# Load configuration from environment variables
config = load_profit_goal_config()

# Initialize tracker with PerformanceTracker integration
tracker = DailyProfitTracker(
    config=config,
    performance_tracker=performance_tracker
)

# Update state after each trade
tracker.update_state()

# Check if protection is active
if tracker.is_protection_active():
    print("⚠️ Profit protection active - new entries blocked")
    print(f"Daily P&L: ${tracker.state.daily_pnl}")
    print(f"Peak Profit: ${tracker.state.peak_profit}")

# Get current state
state = tracker.get_current_state()
print(f"Today's P&L: ${state.daily_pnl}")
print(f"Peak: ${state.peak_profit}")
print(f"Protected: {state.protection_active}")
```

### Features

**Daily Profit Goal Management** (v1.5.0):
- **Configure Targets**: Set daily profit goals via environment variables ($0-$10,000)
- **P&L Tracking**: Automatic tracking of realized + unrealized daily P&L with peak profit high-water mark
- **Profit Protection**: Triggers protection mode on 50% profit giveback from daily peak
- **SafetyChecks Integration**: Automatically blocks new BUY orders when protected, allows SELL orders
- **Event Logging**: JSONL audit trail of all protection triggers with full context
- **State Persistence**: Atomic file writes with crash recovery and corrupted state handling
- **Daily Reset**: Automatic reset at 4:00 AM EST (market open)
- **High Performance**: 0.29ms P&L calculation (343x faster than target)
- **Production Ready**: 97.7% test coverage, zero vulnerabilities, 100% type safety

### Configuration

Add to your `.env` file (feature disabled by default):

```bash
# Daily profit goal settings (v1.5.0)
PROFIT_TARGET_DAILY="500.00"       # Daily profit target in dollars (default: "0" = disabled)
PROFIT_GIVEBACK_THRESHOLD="0.50"   # Protection threshold: 0.50 = 50% drawdown (default: 0.50)
```

**Configuration Ranges**:
- `PROFIT_TARGET_DAILY`: $0 to $10,000 (target = $0 disables feature)
- `PROFIT_GIVEBACK_THRESHOLD`: 0.10 to 0.90 (0.50 = 50%, 0.25 = 25%, etc.)

### How It Works

1. **Track Peak Profit**: Tracks highest daily P&L achieved (high-water mark)
2. **Detect Drawdown**: Monitors current P&L vs. peak profit continuously
3. **Trigger Protection**: When P&L drops 50% from peak, protection activates
4. **Block Entries**: SafetyChecks blocks new BUY orders while protection is active
5. **Allow Exits**: SELL orders always allowed to preserve gains
6. **Daily Reset**: Resets at 4:00 AM EST for new trading day

**Example**:
- Start of day: $0 P&L
- Mid-morning: Reach $400 P&L (peak = $400)
- Afternoon: Drop to $200 P&L (50% from peak)
- **Protection triggers**: No new BUY orders allowed
- Can still SELL to lock in gains

### Use Cases

1. **Prevent Overtrading**: Automatically stops new entries after giving back half your profits
2. **Preserve Gains**: Locks in at least 50% of daily peak profit
3. **Emotional Control**: Removes emotion from exit decisions with automated rules
4. **Risk Management**: Prevents "revenge trading" after profit drawdown

### Monitoring

```bash
# Check current state
cat logs/profit-protection/daily-profit-state.json | jq

# View protection events
tail -f logs/profit-protection/events-$(date +%Y-%m-%d).jsonl

# Check if protection is active
cat logs/profit-protection/daily-profit-state.json | jq '.protection_active'
```

### Documentation

- [Feature Specification](specs/026-daily-profit-goal-ma/spec.md)
- [Implementation Plan](specs/026-daily-profit-goal-ma/plan.md)
- [Ship Report](specs/026-daily-profit-goal-ma/ship-report.md)
- [Quickstart Guide](specs/026-daily-profit-goal-ma/quickstart.md)

### Quality Metrics

- **Tests**: 45/45 passing (100%)
- **Coverage**: 97.7% overall (tracker 95.96%, config 100%, models 100%)
- **Performance**: P&L calc 0.29ms, State persist 0.08ms, Event log 0.33ms
- **Security**: 0 vulnerabilities, Decimal precision, atomic writes

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11 or higher
- Robinhood account (enable 2FA recommended)
- Git

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/marcusgoll/robinhood-algo-trading-bot.git
   cd robinhood-algo-trading-bot
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure credentials** (.env file):
   ```bash
   cp .env.example .env
   # Edit .env with your Robinhood credentials:
   #   - ROBINHOOD_USERNAME (required)
   #   - ROBINHOOD_PASSWORD (required)
   #   - ROBINHOOD_MFA_SECRET (optional, for pyotp MFA)
   #   - ROBINHOOD_DEVICE_TOKEN (optional, for faster auth)
   ```

5. **Configure trading parameters** (config.json file):
   ```bash
   cp config.example.json config.json
 # Edit config.json to customize:
 #   - Trading hours (default: 7am-10am EST)
 #   - Position sizes
 #   - Risk limits
 #   - Phase progression settings
  #   - Order management offsets (global defaults + per-strategy overrides)
  ```

6. **Test configuration**:
   ```bash
   python test_config.py  # Verify config loads correctly
   ```

7. **Validate configuration (§Pre_Deploy)**:
   ```bash
   python validate_startup.py  # Run pre-deploy validation checks
   ```

8. **Verify installation**:
   ```bash
   pytest  # Run tests
   mypy src/  # Type checking
   ruff check src/  # Linting
   ```

---

## Usage

### Starting the Bot

Run the trading bot with the startup sequence:

```bash
# Normal startup - runs full startup sequence and enters trading loop
python -m src.trading_bot

# Dry run - validate configuration without starting trading loop
python -m src.trading_bot --dry-run

# JSON output - machine-readable output for automation
python -m src.trading_bot --json
```

### Startup Sequence

The bot follows a structured startup sequence that:
1. Displays startup banner with mode and phase information
2. Loads configuration from .env and config.json
3. Validates all configuration parameters
4. Initializes logging system (logs/startup.log)
5. Initializes mode switcher (paper/live mode management)
6. Initializes circuit breakers (risk management)
7. Initializes trading bot components
8. Verifies all components are ready
9. Displays startup summary or JSON output

If any step fails, the bot will exit with an appropriate error message and exit code.

### Exit Codes

- 0: Success (startup complete, ready for trading)
- 1: Configuration error (missing credentials, invalid config)
- 2: Validation error (phase-mode conflict, invalid settings)
- 3: Initialization failure (component setup failed)
- 130: Interrupted by user (Ctrl+C)

---

## Troubleshooting

### Common Startup Errors

#### Error: Missing .env file
**Symptom**: Bot fails with "Missing .env file" error

**Remediation**:
```bash
# Copy the example file and add your credentials
cp .env.example .env
# Edit .env and add:
# - ROBINHOOD_USERNAME=your_username
# - ROBINHOOD_PASSWORD=your_password
```

#### Error: Invalid config.json
**Symptom**: Bot fails with JSON parsing error or "Invalid configuration" error

**Remediation**:
```bash
# Validate JSON syntax
python -m json.tool config.json

# If invalid, copy from example and reconfigure
cp config.example.json config.json
# Edit config.json with valid values
```

#### Error: Phase-mode conflict
**Symptom**: "Cannot use live trading in 'experience' phase" error

**Remediation**:
Edit config.json and either:
- Change mode to paper: `"mode": "paper"`
- OR change phase to proof/trial/scaling: `"current_phase": "proof"`

#### Error: Filesystem permissions
**Symptom**: "Failed to create directories" or "Permission denied" error

**Remediation**:
```bash
# Check directory permissions
ls -la logs/ data/ backtests/

# Create directories manually with proper permissions
mkdir -p logs data backtests
chmod 755 logs data backtests
```

#### Error: Component initialization failure
**Symptom**: "Component X initialization failed" error

**Remediation**:
1. Check logs/startup.log for detailed error information
2. Verify all dependencies installed: `pip install -r requirements.txt`
3. Ensure .env and config.json are valid
4. Run dry run to isolate issue: `python -m src.trading_bot --dry-run`

### Debugging Tips

1. **Check startup log**: Always review `logs/startup.log` for detailed initialization steps
2. **Use dry run mode**: Test configuration without starting trading loop
3. **Validate configuration**: Run `python validate_startup.py` before starting bot
4. **Check exit codes**: Use exit code to identify error category (config vs validation vs initialization)

---

## 📁 Project Structure

```
Stocks/
├── src/trading_bot/          # Main source code
│   ├── __init__.py
│   ├── bot.py                # Core trading bot with circuit breakers
│   ├── config.py             # Configuration management
│   ├── error_handling/       # Centralized error handling framework
│   ├── strategies/           # Trading strategies
│   ├── utils/                # Utility functions
│   └── api/                  # Robinhood API wrapper
├── tests/                    # Test suite
│   ├── unit/                 # Unit tests
│   └── integration/          # Integration tests
├── backtests/                # Backtesting scripts and results
│   ├── results/              # Backtest outputs
│   └── logs/                 # Backtest logs
├── config/                   # Configuration files
├── logs/                     # Application logs
├── data/                     # Market data (gitignored)
├── .specify/                 # Project governance
│   ├── memory/               # Constitution, DONT_DO, changelog
│   └── templates/            # Spec and report templates
├── .env.example              # Environment template
├── requirements.txt          # Python dependencies
├── pyproject.toml            # Project config
└── README.md                 # This file
```

---

## ⚙️ Configuration System

**Dual Configuration (Constitution v1.0.0)**:

### 1. Credentials (.env file)
- **Purpose**: Sensitive authentication data (§Security)
- **Location**: `.env` (gitignored, never commit!)
- **Required**:
  - `ROBINHOOD_USERNAME` - Your Robinhood account email
  - `ROBINHOOD_PASSWORD` - Your Robinhood account password
- **Optional (Recommended)**:
  - `ROBINHOOD_MFA_SECRET` - Base32-encoded TOTP secret for automated MFA (16 characters, A-Z2-7)
  - `ROBINHOOD_DEVICE_TOKEN` - Device token for faster authentication (auto-populated after first login with MFA)

### Credentials Setup (T032)

**First-Time Setup**:
1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your credentials:
   ```bash
   ROBINHOOD_USERNAME=your_email@example.com
   ROBINHOOD_PASSWORD=your_secure_password
   ROBINHOOD_MFA_SECRET=ABCDEFGHIJKLMNOP  # Optional: 16-char base32 secret
   DEVICE_TOKEN=                           # Leave empty - auto-populated
   ```

3. **MFA Secret Setup** (Optional but recommended):
   - Enable 2FA in Robinhood app (Settings → Security → Two-Factor Authentication)
   - During setup, you'll see a QR code and a secret key
   - Copy the **secret key** (16 uppercase characters/numbers) into `ROBINHOOD_MFA_SECRET`
   - This allows the bot to generate MFA codes automatically using `pyotp`

**Device Token Auto-Population**:
- On first successful authentication with MFA, the bot automatically saves a device token to `.env`
- Device tokens allow faster authentication without MFA on subsequent logins
- If device token becomes invalid (e.g., after password change), the bot automatically falls back to MFA
- New device token is saved to `.env` after successful MFA fallback
- **Security**: Device tokens are stored with 600 permissions (owner read/write only)

**Credential Security**:
- Credentials are **never** logged in plaintext (§Security)
- Usernames masked in logs: `use***@example.com`
- Passwords/MFA secrets never logged (even masked)
- Device tokens partially masked: `1a2b3c4d***`
- All masking handled by `utils.security` module

### 2. Trading Parameters (config.json)
- **Purpose**: Trading strategy and risk settings
- **Location**: `config.json` (gitignored, user-specific)
- **Template**: `config.example.json` (committed, safe to share)
- **Contains**:
  - Trading hours (7am-10am EST default)
  - Position sizes, stop losses, risk limits
  - Phase progression settings
  - Strategy parameters (bull flag, VWAP, EMA, MACD)
  - Screening filters

### 3. Order management configuration
- **Purpose**: Control limit-order offsets and slippage guardrails for the live gateway
- **Location**: `config.json` → top-level `"order_management"` block
- **Fields**:
  - `offset_mode`: `"bps"` (basis points) or `"absolute"`
  - `buy_offset` / `sell_offset`: Adjust limit prices away from the reference quote
  - `max_slippage_pct`: Hard cap on allowable deviation from the reference price
  - `poll_interval_seconds`: Frequency for open-order synchronization
  - `strategy_overrides`: Optional per-strategy tweaks (inherit from globals by default)

```jsonc
"order_management": {
  "offset_mode": "bps",
  "buy_offset": 15.0,
  "sell_offset": 10.0,
  "max_slippage_pct": 0.5,
  "poll_interval_seconds": 15,
  "strategy_overrides": {
    "bull_flag_breakout": {
      "buy_offset": 20.0,
      "sell_offset": 8.0
    }
  }
}
```

> **Limit-only scope**: The live gateway currently accepts **limit orders only**. Any `market` or `stop` type request triggers an `UnsupportedOrderTypeError` and is logged for review. Update offsets instead of switching to a non-limit order type.

Order submissions are appended to `logs/orders.jsonl` for audit trails; rotate or archive that JSONL file with your existing log retention process.

### 4. ATR-based stop-loss configuration

**Purpose**: Enable volatility-based dynamic stop-loss calculation using Average True Range (ATR).

**Location**: `config.json` → `"risk_management"` → `"atr_*"` fields

ATR (Average True Range) is a volatility indicator that automatically adjusts stop distances based on market conditions:
- **Volatile markets**: Wider stops to avoid premature stop-outs
- **Calm markets**: Tighter stops for better capital protection

**Configuration Fields**:

```jsonc
"risk_management": {
  // ... existing risk management fields ...

  // ATR Configuration (optional, disabled by default)
  "atr_enabled": false,           // Enable ATR-based stop calculation
  "atr_period": 14,                // Wilder's standard 14-period lookback
  "atr_multiplier": 2.0,           // Stop distance = atr_value * 2.0
  "atr_recalc_threshold": 0.20     // Recalculate stop if ATR changes >20%
}
```

**Parameter Details**:

| Parameter | Type | Default | Valid Range | Description |
|-----------|------|---------|-------------|-------------|
| `atr_enabled` | boolean | `false` | true/false | Master switch for ATR feature (opt-in) |
| `atr_period` | integer | `14` | 1-50 | Lookback period for ATR calculation (Wilder's standard is 14) |
| `atr_multiplier` | float | `2.0` | 0.5-5.0 | Multiplier applied to ATR value for stop distance |
| `atr_recalc_threshold` | float | `0.20` | 0.10-1.0 | % ATR change that triggers dynamic stop adjustment |

**Example Configurations**:

**Conservative (Wider Stops)**:
```json
"atr_enabled": true,
"atr_period": 14,
"atr_multiplier": 3.0,      // 3x ATR for wider stops
"atr_recalc_threshold": 0.30 // Adjust only on significant volatility changes
```

**Aggressive (Tighter Stops)**:
```json
"atr_enabled": true,
"atr_period": 10,           // Shorter period = more responsive
"atr_multiplier": 1.5,      // 1.5x ATR for tighter stops
"atr_recalc_threshold": 0.15 // More frequent recalculation
```

**How ATR Works**:

1. **Initial Stop Calculation**:
   ```
   ATR = average_true_range(last_14_bars)
   stop_price = entry_price - (ATR * atr_multiplier)
   ```

2. **Dynamic Adjustment** (T019):
   - System monitors ATR continuously during position lifecycle
   - If ATR changes >20% (default threshold), stop is recalculated
   - Example: If volatility increases 30%, stop widens to avoid premature stop-out

3. **Validation**:
   - All ATR-calculated stops must fall within **0.7%-10%** distance from entry
   - If ATR stop violates bounds, system falls back to pullback/percentage stops

4. **Fallback Behavior**:
   - If ATR calculation fails (insufficient data, stale data), system automatically falls back to:
     1. Pullback-based stops (preferred)
     2. Percentage-based stops (default 2%)
   - All fallback events logged for investigation

**Enabling ATR**:

1. **Edit config.json**:
   ```bash
   vim config.json
   # Set "atr_enabled": true in the "risk_management" section
   ```

2. **Validate configuration**:
   ```bash
   python validate_startup.py
   # Should show: ✅ ATR configuration valid
   ```

3. **Start bot and verify**:
   ```bash
   python -m src.trading_bot
   # Check logs/trading_bot.log for "ATR enabled" message
   tail -f logs/trading_bot.log | grep ATR
   ```

**Monitoring ATR Performance**:

```bash
# View ATR-based position entries
grep '"pullback_source":"atr"' logs/trades.log | jq

# Monitor ATR recalculation events
grep "ATR recalculation" logs/trading_bot.log

# Check ATR calculation failures (should be <5%)
grep "ATRCalculationError" logs/errors.log | wc -l
```

**Troubleshooting**:

| Error | Cause | Solution |
|-------|-------|----------|
| "Insufficient data for ATR" | Not enough price history (need 15+ bars) | Wait for more data accumulation |
| "Stale data" | Price data >15 minutes old | Check market data feed connection |
| "Stop distance too tight" | ATR too small for symbol | Increase `atr_multiplier` to 3.0+ |
| "Stop distance exceeds 10%" | Extreme volatility | Reduce `atr_multiplier` to 1.5 or disable ATR temporarily |

**Performance Metrics**:
- ATR calculation: <1ms (50x faster than 50ms target)
- Test coverage: 14 tests (8 calculator + 3 integration + 3 smoke)
- Success rate target: >95% in production

**Related Documentation**:
- Error codes: `specs/atr-stop-adjustment/error-log.md`
- Rollback procedures: `specs/atr-stop-adjustment/NOTES.md`
- Smoke tests: `tests/smoke/test_atr_smoke.py`

### Why Two Files?
- **.env**: Secrets that **never** change (credentials)
- **config.json**: Parameters you **frequently adjust** (position size, hours, phase)
- Keeps sensitive data separate from trading strategy

---

## ✅ Configuration Validation

**Pre-Deploy Validation (Constitution §Pre_Deploy)**:

The `ConfigValidator` enforces all configuration requirements before the bot starts:

### Validation Checks

1. **Credentials Validation (§Security)**:
   - `.env` file exists
   - `ROBINHOOD_USERNAME` is set
   - `ROBINHOOD_PASSWORD` is set
   - Warnings for missing optional credentials (MFA secret, device token)

2. **Config Parameters (§Data_Integrity)**:
   - All percentage values are valid (0-100%)
   - Position sizes are positive
   - Trading hours are valid
   - Phase progression settings are correct

3. **Safety Checks (§Safety_First)**:
   - Warns if live trading is enabled
   - **Blocks** live trading in "experience" phase
   - Validates risk management parameters

4. **File Paths**:
   - Required directories exist or can be created

### Running Validation

```bash
# Validate before starting bot
python validate_startup.py

# Output:
# ✅ All checks passed - Ready to start bot!
# OR
# ❌ Startup blocked: Fix errors before running bot
```

The bot will **refuse to start** if validation fails (§Safety_First).

---

## 🩺 Session Health Monitoring

**SessionHealthMonitor (Constitution §Safety_First & §Audit_Everything)** keeps the Robinhood session alive and blocks trading if authentication fails.

- Runs automatically during startup and every 5 minutes while the bot is active
- Performs lightweight account probes with exponential backoff + automatic re-authentication
- Emits structured JSONL telemetry to `logs/health/health-checks.jsonl`
- Triggers the safety circuit breaker and halts trading if health verification fails

### Manual Health Check

```python
from src.trading_bot.health import SessionHealthMonitor
from src.trading_bot.auth import RobinhoodAuth
from src.trading_bot.config import Config

config = Config.from_env_and_json()
auth = RobinhoodAuth(config)
monitor = SessionHealthMonitor(auth=auth)

# Run on-demand check (e.g., before manual trades)
result = monitor.check_health(context="manual")
print(result.success, result.latency_ms, result.error_message)
```

### Inspecting Health Logs

```bash
# Tail structured logs (JSONL)
tail -f logs/health/health-checks.jsonl | jq

# Count reauthentication events
rg '"event":"health_check.reauth_' logs/health/health-checks.jsonl | wc -l
```

If a health check fails and re-authentication does not recover the session, the circuit breaker is tripped—restart the bot after resolving credentials.

---

## 🔄 Trading Mode (Paper vs Live)

**Mode Switcher (Constitution §Safety_First)**:

The bot supports two trading modes with strict safety controls:

### Paper Trading Mode (Default)
- **Simulation only** - No real money used
- Perfect for testing strategies and learning
- Real-time market data with simulated trades
- Identical analytics to live mode
- **Always safe** - Can't lose real money

### Live Trading Mode
- **Real money** - Trades execute with actual funds
- Requires phase progression validation
- **Blocked in "experience" phase** (§Safety_First)
- Visual warnings when active

### Mode Switching Rules

**Phase-Based Restrictions**:
- **Experience Phase**: Paper trading ONLY (live mode blocked)
- **Proof Phase**: Live trading allowed (1 trade/day)
- **Trial Phase**: Live trading allowed (small position sizes)
- **Scaling Phase**: Live trading allowed (gradual scaling)

**Visual Indicators**:
```
╔════════════════════════════════════════════════════════════╗
║                    PAPER TRADING MODE                      ║
║                  (Simulation - No Real Money)              ║
╚════════════════════════════════════════════════════════════╝

╔════════════════════════════════════════════════════════════╗
║  ⚠️  ⚠️  ⚠️       LIVE TRADING MODE       ⚠️  ⚠️  ⚠️        ║
║                                                            ║
║              REAL MONEY WILL BE USED!                      ║
╚════════════════════════════════════════════════════════════╝
```

### Usage

```python
from src.trading_bot.mode_switcher import ModeSwitcher

# Initialize with config
switcher = ModeSwitcher(config)

# Check current mode
print(switcher.get_mode_indicator())  # [PAPER] or [⚠️  LIVE ⚠️]

# Display full banner
print(switcher.display_mode_banner())

# Switch modes
switcher.switch_to_paper()  # Always allowed (safer)
switcher.switch_to_live()   # Blocked if in experience phase

# Get detailed status
status = switcher.get_status()
print(f"Mode: {status.current_mode}")
print(f"Phase: {status.phase}")
print(f"Can switch to live: {status.can_switch_to_live}")
```

---

## 📊 Phase Progression

**Gradual Scaling System (Constitution §Risk_Management)**:

The bot uses a 4-phase progression system to safely transition from paper trading to live trading:

### Phase 1: Experience (Paper Trading Only)
- **Mode**: Paper trading ONLY (live mode blocked)
- **Purpose**: Learn strategy mechanics without risk
- **Trades/Day**: Unlimited
- **Position Size**: Simulated (100 shares default)
- **Advancement**: Complete 10-20 profitable sessions

### Phase 2: Proof of Concept (Limited Live Trading)
- **Mode**: Paper or live trading allowed
- **Purpose**: Prove strategy works with real money
- **Trades/Day**: 1 trade maximum
- **Position Size**: Small (100 shares)
- **Advancement**: Consistent profitability over 10-20 sessions

### Phase 3: Trial (Controlled Live Trading)
- **Mode**: Paper or live trading allowed
- **Purpose**: Build confidence with larger size
- **Trades/Day**: Unlimited
- **Position Size**: Small to medium
- **Advancement**: Meet risk-reward targets consistently

### Phase 4: Scaling (Full Operation)
- **Mode**: Paper or live trading allowed
- **Purpose**: Gradually increase position size
- **Trades/Day**: Unlimited
- **Position Size**: Gradual increases based on performance
- **Advancement**: Ongoing based on metrics

**Phase Configuration** (config.json):
```json
{
  "phase_progression": {
    "current_phase": "experience",
    "experience": {
      "mode": "paper",
      "max_trades_per_day": 999
    },
    "proof": {
      "mode": "paper",
      "max_trades_per_day": 1
    },
    "trial": {
      "mode": "paper",
      "max_trades_per_day": 999
    },
    "scaling": {
      "mode": "paper",
      "max_trades_per_day": 999
    }
  }
}
```

---

## 📝 Logging System

**Structured Logging (Constitution §Audit_Everything)**:

The bot uses a comprehensive logging system with separate logs for different purposes:

### Log Files

All logs are stored in the `logs/` directory with automatic rotation:

1. **`logs/trading_bot.log`** - General application logs
   - Startup/shutdown events
   - Configuration loading
   - System status updates
   - Debug information

2. **`logs/trades.log`** - Trade execution audit trail (§Audit_Everything)
   - All buy/sell orders
   - Entry/exit prices
   - Position sizes
   - Strategy signals
   - Profit/loss calculations

3. **`logs/errors.log`** - Error and exception tracking
   - API errors
   - Validation failures
   - Exception tracebacks
   - Critical issues

### Features

- ✅ **UTC Timestamps** (§Data_Integrity) - All logs use ISO 8601 UTC format
- ✅ **Log Rotation** - Automatic rotation at 10MB, keeps 5 backup files
- ✅ **Structured Format** - Consistent formatting with timestamp, level, module, message
- ✅ **Console + File** - Logs written to both console and files
- ✅ **Audit Trail** - Complete trade history for compliance and analysis

### Usage

```python
from src.trading_bot.logger import setup_logging, get_logger, log_trade, log_error

# Initialize logging (call once at startup)
setup_logging()

# Get a logger for your module
logger = get_logger(__name__)

# Log general messages
logger.info("Bot started successfully")
logger.warning("Market volatility detected")
logger.error("API connection failed")

# Log trade executions (§Audit_Everything)
log_trade(
    action="BUY",
    symbol="AAPL",
    quantity=100,
    price=150.50,
    mode="PAPER",
    strategy="Bull Flag",
    stop_loss=148.00,
    target=155.50
)

# Log errors with context
try:
    # ... some operation ...
except Exception as e:
    log_error(e, "During order placement")
```

### Log Format

```
2025-10-07 14:23:45 UTC | INFO     | trading_bot.bot | Bot initialized
2025-10-07 14:23:46 UTC | INFO     | trading_bot.trades | BUY 100 AAPL @ 150.50 [PAPER]
2025-10-07 14:23:47 UTC | ERROR    | trading_bot.errors | API timeout during order submission
```

### Testing Logging

```bash
# Test logging system
python test_logging.py

# View logs
tail -f logs/trading_bot.log    # General logs
tail -f logs/trades.log          # Trade executions
tail -f logs/errors.log          # Errors only
```

### Log Rotation

- **Max Size**: 10MB per file
- **Backups**: 5 backup files kept (e.g., `trading_bot.log.1`, `trading_bot.log.2`)
- **Automatic**: Old logs automatically rotated when size limit reached
- **No Manual Cleanup**: System manages log files automatically

---

## 🔒 Security

**Constitution §Security Requirements**:

1. **Never commit credentials**:
   - All secrets in `.env` (gitignored)
   - User configs in `config.json` (gitignored)
   - Use `.env.example` and `config.example.json` as templates

2. **API Key Safety**:
   - Store in environment variables
   - Never log or print credentials
   - Use minimal OAuth scopes

3. **Robinhood Best Practices**:
   - Enable 2FA on account
   - Use MFA secret with pyotp for automation
   - Use device token when possible
   - Respect API rate limits

---

## 🧪 Development Workflow

### 1. Specify Strategy

Use the strategy spec template:
```bash
cp .specify/templates/trading-strategy-spec-template.md specs/my-strategy-spec.md
# Fill out hypothesis, entry/exit rules, risk limits
```

### 2. Write Tests First (TDD)

```bash
# Create test file
touch tests/unit/test_my_strategy.py

# Write failing tests
pytest tests/unit/test_my_strategy.py  # Should fail initially
```

### 3. Implement Strategy

```bash
# Implement in src/trading_bot/strategies/
touch src/trading_bot/strategies/my_strategy.py
```

### 4. Backtest

```bash
# Create backtest script
python backtests/my_strategy_backtest.py

# Generate report using template
cp .specify/templates/backtest-report-template.md backtests/results/my_strategy_report.md
```

### 5. Paper Trade

```bash
# Ensure PAPER_TRADING=true in .env
python -m src.trading_bot.main
# Monitor for 1-2 weeks
```

### 6. Deploy to Real Money (Only after thorough testing!)

```bash
# Update .env
PAPER_TRADING=false

# Start with small position sizes
python -m src.trading_bot.main
```

---

## 🎯 Quality Gates

Per Constitution §Pre_Deploy, before deploying:

- [ ] **Tests**: All tests pass, 90%+ coverage
- [ ] **Type Safety**: `mypy` passes with no errors
- [ ] **Linting**: `ruff` and `pylint` clean
- [ ] **Security**: `bandit` scan shows no high-severity issues
- [ ] **Backtesting**: Sharpe ≥1.0, Max DD <15%, Win Rate ≥55%
- [ ] **Paper Trading**: 1-2 weeks validation, performance matches backtest
- [ ] **Risk Controls**: Circuit breakers tested, stop losses active
- [ ] **Logging**: All trades logged with reasoning

---

## 🛠️ Commands

### Testing
```bash
# Run all tests with coverage
pytest

# Run specific test file
pytest tests/unit/test_bot.py

# Run with verbose output
pytest -v
```

### Code Quality
```bash
# Type checking
mypy src/

# Linting
ruff check src/

# Format code
ruff format src/

# Security scan
bandit -r src/
```

### Validation
```bash
# Validate configuration before startup (§Pre_Deploy)
python validate_startup.py

# Test configuration loading
python test_config.py
```

### Logging
```bash
# Test logging system
python test_logging.py

# View logs in real-time
tail -f logs/trading_bot.log
tail -f logs/trades.log
tail -f logs/errors.log
```

### Trading
```bash
# Start bot (paper trading)
python -m src.trading_bot.main

# Run backtest
python backtests/my_strategy_backtest.py

# View logs
tail -f logs/trading_bot.log
```

---

## 📊 Circuit Breakers

The bot includes safety circuit breakers (Constitution §Safety_First):

1. **Daily Loss Limit**: Halts trading if daily loss exceeds threshold (default: 3%)
2. **Consecutive Losses**: Halts after N consecutive losses (default: 3)
3. **Manual Kill Switch**: `bot.stop()` immediately halts all trading

Circuit breakers require manual reset after triggering.

---

## 📈 Risk Management

Per Constitution §Risk_Management:

- **Position Sizing**: Max 5% of portfolio per position
- **Stop Losses**: Required on every position
- **Input Validation**: All market data validated
- **Rate Limiting**: Respect Robinhood API limits with exponential backoff

---

## 📝 Testing Strategy

1. **Unit Tests**: Test individual functions in isolation
2. **Integration Tests**: Test Robinhood API interactions (mocked)
3. **Backtesting**: Validate strategy against historical data
4. **Paper Trading**: Live market testing without real money

Target: 90% test coverage (enforced by `pytest-cov`)

---

## 🚫 Anti-Patterns (DONT_DO.md)

See [`.specify/memory/DONT_DO.md`](.specify/memory/DONT_DO.md) for known anti-patterns:

- ❌ Trading without circuit breakers
- ❌ Hard-coding API credentials
- ❌ Skipping paper trading validation
- ❌ Ignoring API rate limits
- ❌ Deploying without stop losses

---

## 📚 Resources

- **robin_stocks Documentation**: https://robin-stocks.readthedocs.io/
- **Robinhood API**: https://robinhood.com/us/en/support/articles/developer-api/
- **Constitution**: [`.specify/memory/constitution.md`](.specify/memory/constitution.md)
- **Changelog**: [`.specify/memory/CONSTITUTION_CHANGELOG.md`](.specify/memory/CONSTITUTION_CHANGELOG.md)

---

## 🤝 Contributing

This is a personal project, but contributions are welcome:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-strategy`)
3. Follow Constitution principles (type hints, tests, etc.)
4. Ensure quality gates pass
5. Submit a pull request

---

## 📄 License

MIT License - See LICENSE file for details

---

## ⚖️ Legal & Compliance

- **Personal Use Only**: Not financial advice
- **Tax Responsibility**: You must report all trades for tax purposes
- **Robinhood ToS**: Ensure compliance with Robinhood Terms of Service
- **Pattern Day Trading**: Rules apply if making 4+ day trades in 5 days

---

## 🆘 Support

- **Issues**: Open a GitHub issue
- **Logs**: Check `logs/trading_bot.log` for errors
- **Circuit Breaker Tripped**: Review logs, fix issue, manually reset
- **API Errors**: Check Robinhood service status, verify credentials

---

**Remember**: Start with paper trading, test thoroughly, never risk more than you can afford to lose!
