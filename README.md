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

4. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your Robinhood credentials
   ```

5. **Verify installation**:
   ```bash
   pytest  # Run tests
   mypy src/  # Type checking
   ruff check src/  # Linting
   ```

---

## 📁 Project Structure

```
Stocks/
├── src/trading_bot/          # Main source code
│   ├── __init__.py
│   ├── bot.py                # Core trading bot with circuit breakers
│   ├── config.py             # Configuration management
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

## 🔒 Security

**Constitution §Security Requirements**:

1. **Never commit credentials**:
   - All secrets in `.env` (gitignored)
   - Use `.env.example` as template

2. **API Key Safety**:
   - Store in environment variables
   - Never log or print credentials
   - Use minimal OAuth scopes

3. **Robinhood Best Practices**:
   - Enable 2FA on account
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
