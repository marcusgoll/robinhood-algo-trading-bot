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

## 🚀 Quick Start

### Prerequisites

- Python 3.11 or higher
- Robinhood account (enable 2FA recommended)
- Git

### Installation

1. **Clone the repository**:
   ```bash
   git clone <your-repo-url>
   cd Stocks
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
  - `ROBINHOOD_USERNAME`
  - `ROBINHOOD_PASSWORD`
- **Optional**:
  - `ROBINHOOD_MFA_SECRET` - For pyotp MFA automation
  - `ROBINHOOD_DEVICE_TOKEN` - For faster authentication

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
