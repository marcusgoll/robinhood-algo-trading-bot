# Contributing to Robinhood Trading Bot

Thank you for your interest in contributing! This guide will help you get started.

---

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Code Style Guide](#code-style-guide)
- [Testing Requirements](#testing-requirements)
- [Pull Request Process](#pull-request-process)
- [Commit Message Convention](#commit-message-convention)
- [Project Structure](#project-structure)
- [Constitution Compliance](#constitution-compliance)
- [Quality Gates](#quality-gates)
- [Common Tasks](#common-tasks)

---

## Code of Conduct

This is a personal educational project, but we expect respectful and constructive interactions. Please:

- Be respectful and inclusive
- Focus on constructive feedback
- Assume good intentions
- Help others learn and grow

---

## Getting Started

### Prerequisites

Before contributing, ensure you have:

- **Python 3.11+**: [Download](https://www.python.org/downloads/)
- **Git 2.39+**: [Download](https://git-scm.com/)
- **`uv`**: Python environment manager ([Install](https://github.com/astral-sh/uv))
- **PowerShell 7.3+** (Windows) or **Bash 5+** (macOS/Linux)

### Ways to Contribute

1. **Bug Reports**: Found a bug? Open an issue with reproduction steps
2. **Feature Requests**: Have an idea? Create an issue with your proposal
3. **Code Contributions**: Fix bugs, add features, improve documentation
4. **Documentation**: Improve guides, add examples, fix typos
5. **Testing**: Add test coverage, find edge cases

---

## Development Setup

### 1. Fork and Clone

```bash
# Fork the repository on GitHub
# Then clone your fork
git clone https://github.com/YOUR_USERNAME/robinhood-algo-trading-bot.git
cd robinhood-algo-trading-bot

# Add upstream remote
git remote add upstream https://github.com/marcusgoll/robinhood-algo-trading-bot.git
```

### 2. Create Virtual Environment

```bash
# Using uv (recommended)
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Or using standard Python
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
# Install all dependencies
pip install -r requirements.txt

# Install development dependencies
pip install pytest pytest-cov mypy ruff bandit black
```

### 4. Configure Environment

```bash
# Copy example files
cp .env.example .env
cp config.example.json config.json

# Edit .env with your test credentials (or use paper trading mode)
# DO NOT commit .env or config.json
```

### 5. Verify Setup

```bash
# Run tests
pytest

# Type checking
mypy src/

# Linting
ruff check src/

# Format check
black --check src/
```

---

## Code Style Guide

This project follows strict code quality standards defined in the [Constitution](.spec-flow/memory/constitution.md).

### Python Style

- **PEP 8**: Follow Python style guide
- **Type Hints**: Required on all functions (§Code_Quality)
- **Docstrings**: Google-style docstrings for public functions
- **Line Length**: 100 characters maximum
- **Imports**: Organized (stdlib → third-party → local)

**Example**:
```python
from typing import Optional
from decimal import Decimal

def calculate_position_size(
    account_balance: Decimal,
    max_position_pct: float,
    stop_distance: Decimal
) -> int:
    """Calculate position size based on risk parameters.

    Args:
        account_balance: Current account balance in dollars
        max_position_pct: Maximum position size as percentage (0-100)
        stop_distance: Distance from entry to stop loss in dollars

    Returns:
        Number of shares to buy

    Raises:
        ValueError: If parameters are invalid
    """
    if max_position_pct <= 0 or max_position_pct > 100:
        raise ValueError(f"Invalid max_position_pct: {max_position_pct}")

    max_position_value = account_balance * Decimal(max_position_pct / 100)
    shares = int(max_position_value / stop_distance)
    return max(1, shares)  # Minimum 1 share
```

### Naming Conventions

- **Files**: `snake_case.py`
- **Classes**: `PascalCase`
- **Functions**: `snake_case`
- **Constants**: `UPPER_SNAKE_CASE`
- **Private**: `_leading_underscore`

### Code Organization

```python
# 1. Module docstring
"""Module description."""

# 2. Imports (grouped and sorted)
# stdlib
import os
from datetime import datetime
from typing import Dict, List

# third-party
import requests
from robin_stocks import robinhood as rh

# local
from src.trading_bot.config import Config
from src.trading_bot.logger import get_logger

# 3. Constants
DEFAULT_TIMEOUT = 30
MAX_RETRIES = 3

# 4. Classes and functions
class TradingBot:
    """Main trading bot class."""
    pass
```

---

## Testing Requirements

All code changes MUST include tests (§Testing_Requirements). Target: **90% coverage**.

### Test Structure

```
tests/
├── unit/                # Unit tests (isolated functions)
├── integration/         # Integration tests (API calls, DB)
├── performance/         # Performance benchmarks
└── smoke/               # Smoke tests (critical paths)
```

### Writing Tests

```python
# tests/unit/test_position_sizing.py
import pytest
from decimal import Decimal

from src.trading_bot.risk_management import calculate_position_size

def test_calculate_position_size_basic():
    """Test basic position size calculation."""
    account_balance = Decimal("100000")
    max_position_pct = 5.0  # 5%
    stop_distance = Decimal("2.00")

    size = calculate_position_size(account_balance, max_position_pct, stop_distance)

    assert size == 2500  # $100k * 5% / $2 = 2500 shares

def test_calculate_position_size_invalid_pct():
    """Test that invalid percentage raises ValueError."""
    with pytest.raises(ValueError, match="Invalid max_position_pct"):
        calculate_position_size(Decimal("100000"), 150.0, Decimal("2.00"))

@pytest.mark.parametrize("balance,pct,stop,expected", [
    (100000, 5.0, 2.0, 2500),
    (50000, 10.0, 1.5, 3333),
    (200000, 2.5, 5.0, 1000),
])
def test_calculate_position_size_parameterized(balance, pct, stop, expected):
    """Test position sizing with multiple inputs."""
    result = calculate_position_size(Decimal(balance), pct, Decimal(stop))
    assert result == expected
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/trading_bot --cov-report=html

# Run specific test file
pytest tests/unit/test_position_sizing.py

# Run with verbose output
pytest -v

# Run only unit tests
pytest tests/unit/

# Run specific test
pytest tests/unit/test_bot.py::test_circuit_breaker
```

### Test Coverage Requirements

- **Minimum**: 90% coverage for new code
- **Focus Areas**:
  - Risk management (100% required)
  - Safety checks (100% required)
  - Order execution (95%+ required)
  - Configuration validation (95%+ required)

```bash
# Check coverage
pytest --cov=src/trading_bot --cov-report=term-missing

# Generate HTML report
pytest --cov=src/trading_bot --cov-report=html
open htmlcov/index.html
```

---

## Pull Request Process

### 1. Create Feature Branch

```bash
# Update main branch
git checkout main
git pull upstream main

# Create feature branch
git checkout -b feature/my-feature-name

# Or for bug fixes
git checkout -b fix/bug-description
```

### 2. Make Changes

- Write code following style guide
- Add tests for new functionality
- Update documentation
- Run quality checks locally

### 3. Run Quality Checks

```bash
# Format code
black src/ tests/

# Lint
ruff check src/ tests/

# Type check
mypy src/

# Security scan
bandit -r src/

# Run tests
pytest --cov=src/trading_bot
```

### 4. Commit Changes

Follow [commit message convention](#commit-message-convention):

```bash
git add .
git commit -m "feat: add ATR-based stop loss calculation

- Implement ATR calculator with 14-period lookback
- Add dynamic stop adjustment on volatility changes
- Include comprehensive test coverage (96%)
- Update configuration with atr_enabled flag

Closes #123"
```

### 5. Push and Create PR

```bash
# Push to your fork
git push origin feature/my-feature-name

# Create pull request on GitHub
# Fill out PR template
# Link related issues
```

### 6. PR Review Process

1. **Automated Checks**: CI runs tests, linting, type checking
2. **Code Review**: Maintainer reviews code for quality and style
3. **Feedback**: Address review comments
4. **Approval**: PR approved and merged

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix (non-breaking)
- [ ] New feature (non-breaking)
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Tests pass locally
- [ ] Added tests for new code
- [ ] Coverage ≥90%

## Checklist
- [ ] Code follows style guide
- [ ] Type hints added
- [ ] Docstrings added
- [ ] Tests added
- [ ] Documentation updated
- [ ] CHANGELOG.md updated

## Related Issues
Closes #issue_number
```

---

## Commit Message Convention

Follow [Conventional Commits](https://www.conventionalcommits.org/):

### Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Code style (formatting, no logic change)
- `refactor`: Code restructure (no feature/fix)
- `perf`: Performance improvement
- `test`: Test additions/changes
- `chore`: Maintenance (dependencies, build, etc.)

### Examples

```bash
# Feature
feat(risk-management): add ATR-based stop loss calculation

# Bug fix
fix(auth): handle session timeout gracefully

# Documentation
docs(api): add WebSocket streaming examples

# Breaking change
feat(config)!: change atr_period default from 20 to 14

BREAKING CHANGE: atr_period default changed to match Wilder's standard
```

### Best Practices

- **Subject**: Max 75 characters, imperative mood ("add" not "added")
- **Body**: Explain *what* and *why*, not *how*
- **Footer**: Reference issues (`Closes #123`, `Fixes #456`)

---

## Project Structure

```
robinhood-algo-trading-bot/
├── src/trading_bot/           # Main source code
│   ├── __init__.py
│   ├── bot.py                 # Core trading bot
│   ├── config.py              # Configuration management
│   ├── logger.py              # Logging system
│   ├── auth/                  # Authentication
│   ├── strategies/            # Trading strategies
│   ├── risk_management/       # Risk and position sizing
│   ├── market_data/           # Market data fetching
│   ├── performance/           # Performance tracking
│   ├── order_management/      # Order execution
│   ├── backtest/              # Backtesting engine
│   └── cli/                   # CLI tools
│
├── api/                       # FastAPI service (v1.8.0)
│   ├── app/
│   │   ├── main.py           # FastAPI application
│   │   ├── routes/           # API endpoints
│   │   ├── schemas/          # Pydantic models
│   │   ├── services/         # Business logic
│   │   ├── middleware/       # Auth, rate limiting
│   │   └── core/             # WebSocket, auth
│   └── requirements.txt
│
├── tests/                     # Test suite
│   ├── unit/                 # Unit tests
│   ├── integration/          # Integration tests
│   ├── performance/          # Performance tests
│   └── smoke/                # Smoke tests
│
├── docs/                      # Documentation
│   ├── API.md                # API reference
│   ├── ARCHITECTURE.md       # System design
│   ├── OPERATIONS.md         # Operations guide
│   └── DEPLOYMENT.md         # Deployment guide
│
├── specs/                     # Feature specifications
│   └── NNN-feature-name/     # Per-feature docs
│
├── examples/                  # Example scripts
│   ├── simple_backtest.py
│   ├── strategy_comparison.py
│   └── custom_strategy_example.py
│
├── .spec-flow/               # Spec-Flow workflow
│   ├── memory/               # Roadmap, constitution
│   ├── scripts/              # Automation scripts
│   └── templates/            # Document templates
│
├── config/                    # Configuration
├── logs/                      # Log files (gitignored)
├── data/                      # Market data (gitignored)
├── .env                       # Credentials (gitignored)
├── config.json                # User config (gitignored)
├── README.md                  # Main documentation
├── CONTRIBUTING.md            # This file
├── CHANGELOG.md               # Version history
├── SECURITY.md                # Security policy
└── requirements.txt           # Python dependencies
```

---

## Constitution Compliance

All contributions must comply with the [Constitution](.spec-flow/memory/constitution.md):

### §Safety_First
- Paper trading by default
- Circuit breakers required
- Audit logging for all trades
- Input validation

### §Code_Quality
- Type hints on all functions
- 90% test coverage minimum
- KISS/DRY principles
- No dead code

### §Risk_Management
- Position limits enforced
- Stop losses mandatory
- Input validation
- No unsafe defaults

### §Security
- No credentials in code
- Environment variables for secrets
- Minimal permissions
- Secure defaults

### §Testing_Requirements
- Unit tests for all logic
- Integration tests for API calls
- Backtesting before live trading
- Paper trading validation

### §Audit_Everything
- All trades logged
- UTC timestamps
- Structured logging
- Audit trails

### §Error_Handling
- Try/catch all external calls
- Exponential backoff
- Circuit breakers
- Graceful degradation

### §Data_Integrity
- Decimal for money
- UTC for timestamps
- Input validation
- Data validation

---

## Quality Gates

Before merging, all PRs must pass:

### Automated Checks

```bash
# 1. Tests (90%+ coverage)
pytest --cov=src/trading_bot --cov-fail-under=90

# 2. Type checking (zero errors)
mypy src/ --strict

# 3. Linting (zero errors)
ruff check src/ tests/

# 4. Security scan (no high/critical)
bandit -r src/ -ll

# 5. Format check
black --check src/ tests/
```

### Manual Review

- [ ] Code follows style guide
- [ ] Tests cover new functionality
- [ ] Documentation updated
- [ ] No breaking changes (or documented)
- [ ] Constitution compliance
- [ ] Performance acceptable
- [ ] Security considered

---

## Common Tasks

### Running the Bot

```bash
# Paper trading (safe)
python -m src.trading_bot

# Dry run (validate only)
python -m src.trading_bot --dry-run

# Live trading (requires phase progression)
# Edit config.json: "mode": "live"
python -m src.trading_bot
```

### Running API Service

```bash
# Start API
bash scripts/start_api.sh

# Or manually
cd api
uvicorn app.main:app --reload --port 8000
```

### Running Tests

```bash
# All tests
pytest

# Specific test
pytest tests/unit/test_bot.py::test_circuit_breaker

# With coverage
pytest --cov=src/trading_bot --cov-report=html

# Performance tests
pytest tests/performance/ --benchmark-only
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint
ruff check src/ tests/ --fix

# Type check
mypy src/

# Security scan
bandit -r src/
```

### Backtesting

```bash
# Run backtest
python examples/simple_backtest.py

# Compare strategies
python examples/strategy_comparison.py
```

### Documentation

```bash
# Generate API docs
cd api
python -m app.main  # Start server
open http://localhost:8000/api/docs

# Preview markdown
# Use VSCode markdown preview or
grip README.md
```

---

## Getting Help

- **Issues**: [GitHub Issues](https://github.com/marcusgoll/robinhood-algo-trading-bot/issues)
- **Discussions**: Create an issue for questions
- **Documentation**: Check [README.md](README.md) and [docs/](docs/)
- **Examples**: See [examples/](examples/)

---

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

**Thank you for contributing!** 🎉

Every contribution, no matter how small, helps make this project better.
