# Development Workflow

**Last Updated**: 2025-10-26
**Team Size**: 1 (solo developer/trader)
**Related Docs**: See `deployment-strategy.md` for CI/CD, `tech-stack.md` for tools

## Team Structure

**Current Team**:
- **Solo Developer/Trader**: Marcus - Full-stack development, strategy design, trading, DevOps

**Future** (if expanding):
- **Quant Developer**: Strategy research, backtesting
- **DevOps Engineer**: Infrastructure, monitoring, deployment automation
- **Data Analyst**: Performance analysis, trade review

---

## Git Workflow

**Strategy**: GitHub Flow (simplified, optimized for solo dev)

**Branches**:
- `main` - Production code (always deployable to live trading)
- `feature/[name]` - Feature branches (short-lived, 1-3 days)

**Flow**:
```
main (production)
  ↑
feature/add-momentum-scanner (active work)
```

**Why GitHub Flow?**:
- Solo developer: No need for complex Git Flow (develop/release branches)
- Fast iteration: Merge to main quickly
- Simple: Easy to remember
- Staging validation: Paper trading mode provides safety net

---

### Branch Naming

**Format**: `[type]/[short-description]`

**Types**:
- `feature/` - New features (e.g., momentum scanner, LLM integration)
- `fix/` - Bug fixes (e.g., circuit breaker not triggering)
- `refactor/` - Code refactoring (e.g., extract order management module)
- `docs/` - Documentation updates
- `chore/` - Maintenance (e.g., dependency updates)

**Examples**:
- `feature/bull-flag-detector`
- `fix/robinhood-session-expiry`
- `refactor/extract-risk-management`
- `docs/update-readme`
- `chore/upgrade-python-3.12`

---

### Creating a Feature Branch

```bash
# Start from latest main
git checkout main
git pull origin main

# Create feature branch
git checkout -b feature/order-flow-monitor

# Work on feature (commit frequently)
git add src/trading_bot/order_flow/
git commit -m "feat: add Polygon.io Level 2 order flow monitor"

# Push to remote
git push -u origin feature/order-flow-monitor

# Create PR on GitHub (optional for solo dev, but good practice)
gh pr create --base main --title "Add order flow monitor"
```

**Branch Lifetime**: 1-3 days (merge quickly, avoid long-lived branches)

---

## Pull Request Process

**Solo Developer Exception**: PRs optional (can merge directly to main)
**Recommended**: Create PRs for major features (self-review, documentation)

### Creating a PR (Optional)

**Required Information**:
- **Title**: Clear, concise (e.g., "Add Polygon.io order flow monitor")
- **Description**: What changed, why, testing notes
- **Testing**: Manual testing results (backtest, paper trading)

**PR Template**:
```markdown
## Summary
Add Level 2 order flow monitoring via Polygon.io WebSocket to detect large sellers and adjust stop-loss dynamically.

## Changes
- Add `OrderFlowMonitor` class (src/trading_bot/order_flow/)
- Integrate Polygon.io WebSocket client
- Add exit signal logic (large seller detection)
- Update risk manager to tighten stops on exit signals

## Testing
- Unit tests: pytest src/trading_bot/order_flow/
- Backtest: Tested on AAPL 2024-10-01 to 2024-10-26 (improved exits by 15%)
- Paper trading: Ran for 24 hours, 3 trades with order flow data (no errors)

## Checklist
- [x] Tests pass locally
- [x] Backtest validates improvement
- [x] Paper trading for 24 hours
- [x] Code follows style guide (ruff, mypy)
- [x] No sensitive data in code
```

---

### Self-Review & Merge

**Solo Developer Process**:
1. Review own code (self-review checklist)
2. Run tests locally
3. Backtest strategy change (if applicable)
4. Paper trade for 24 hours minimum
5. Merge to main
6. Deploy to staging (paper trading VPS)
7. Validate in staging (24-48 hours)
8. Deploy to production (live trading VPS)

**Self-Review Checklist**:
- [ ] Code is readable (clear variable names, no magic numbers)
- [ ] No debug prints or commented code
- [ ] Error handling implemented (try/except with logging)
- [ ] Risk limits respected (position size, stop-loss)
- [ ] Type hints added (mypy passes)
- [ ] Tests added for new logic
- [ ] Backtest validates (if strategy change)

---

## Commit Conventions

**Format**: [Conventional Commits](https://www.conventionalcommits.org/)

**Structure**: `<type>(<scope>): <subject>`

**Types**:
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation
- `style:` - Formatting, no code change
- `refactor:` - Code refactoring
- `test:` - Adding tests
- `chore:` - Maintenance

**Examples**:
```
feat(momentum): add premarket scanner with volume filter
fix(risk): correct ATR calculation for stop-loss
docs(readme): update installation instructions
refactor(order): extract order manager to separate module
test(patterns): add unit tests for bull flag detector
chore(deps): upgrade alpaca-py to 0.30.0
```

**Why**: Enables automatic changelog generation, clear git history

---

## Development Environment Setup

**Prerequisites**:
- Python 3.11+ (recommended: 3.11.10)
- Git
- Docker (optional, for Redis)
- Robinhood account (with 2FA)
- Alpaca account (for market data)
- Polygon.io API key (for order flow, optional)
- OpenAI API key (for LLM, optional)

**First-Time Setup**:
```bash
# 1. Clone repo
git clone https://github.com/yourusername/trading-bot.git
cd trading-bot

# 2. Install Python dependencies
pip install -r requirements.txt
# OR use uv (faster)
uv pip install -r requirements.txt

# 3. Copy environment template
cp .env.example .env
# Edit .env with your credentials

# 4. Generate Robinhood MFA secret (one-time)
python scripts/setup_mfa.py  # Follow prompts to set up TOTP

# 5. Test authentication
python -m trading_bot --dry-run

# 6. (Optional) Start Redis for LLM caching
docker-compose up -d redis

# 7. Run tests
pytest

# 8. Start bot in paper trading mode
PAPER_TRADING=true python -m trading_bot
```

**Onboarding Time**: ~30 minutes for first-time setup

---

## Code Style Guidelines

### Python (Backend)

**Linting**: Ruff (replaces Pylint, Flake8, isort, Black)
**Type Checking**: Pyright (via VS Code/Cursor) or mypy
**Formatting**: Ruff format (Black-compatible)

**Key Rules**:
- Use type hints for all function signatures
- Use Pydantic models for data validation (API, config)
- Follow PEP 8 (automated by Ruff)
- Extract business logic to services (not in main bot loop)
- Use async/await for I/O operations (future)

**Module Structure**:
```python
# Good example
from decimal import Decimal
from trading_bot.risk_management import RiskManager
from trading_bot.logging import TradeRecord

def calculate_position_size(
    account_balance: Decimal,
    risk_pct: Decimal,
    stop_loss_distance: Decimal
) -> int:
    """Calculate position size based on account risk.

    Args:
        account_balance: Total account value
        risk_pct: Risk per trade (e.g., 0.02 for 2%)
        stop_loss_distance: Price distance to stop-loss

    Returns:
        Number of shares to buy
    """
    risk_amount = account_balance * risk_pct
    shares = int(risk_amount / stop_loss_distance)
    return shares
```

**File Naming**:
- Modules: `risk_calculator.py` (snake_case)
- Classes: `RiskManager` (PascalCase)
- Functions: `calculate_position` (snake_case)
- Tests: `test_risk_calculator.py`

---

## Testing Strategy

**Test Pyramid** (solo dev, focus on critical paths):
```
        /\
       /  \  Manual Testing (20%)
      /____\  Paper trading validation
     /      \
    /________\  Unit Tests (80%)
               Core business logic
```

### Unit Tests

**What to Test**: Business logic, calculations, validation

**Tools**: pytest

**Coverage Target**: >80% for critical modules (risk management, order management)

**Example**:
```python
# tests/test_risk_calculator.py
from decimal import Decimal
from trading_bot.risk_management import RiskCalculator

def test_calculate_position_size_basic():
    calc = RiskCalculator(max_risk_pct=Decimal("0.02"))

    position = calc.calculate_position_size(
        account_balance=Decimal("10000"),
        entry_price=Decimal("150.00"),
        stop_loss_price=Decimal("148.50")
    )

    # Risk: $10,000 * 2% = $200
    # Stop distance: $150 - $148.50 = $1.50
    # Shares: $200 / $1.50 = 133 shares
    assert position.quantity == 133
    assert position.risk_amount == Decimal("199.50")  # 133 * $1.50

def test_position_size_respects_max_position_pct():
    calc = RiskCalculator(
        max_risk_pct=Decimal("0.02"),
        max_position_pct=Decimal("0.05")
    )

    # Even if risk allows 1000 shares, max position % limits to 333 shares
    position = calc.calculate_position_size(
        account_balance=Decimal("10000"),
        entry_price=Decimal("150.00"),
        stop_loss_price=Decimal("149.00")  # Very tight stop
    )

    # Max position: $10,000 * 5% = $500 / $150 = 3.33 shares → 3 shares
    assert position.quantity == 3
```

**Run Tests**:
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/trading_bot --cov-report=html

# Run specific test file
pytest tests/test_risk_calculator.py

# Run tests matching pattern
pytest -k "test_position_size"
```

---

### Backtest Validation

**When Required**: Any strategy change (entry logic, exit logic, risk parameters)

**Process**:
1. Modify strategy code
2. Run backtest on historical data (3-6 months)
3. Compare metrics: Win rate, profit factor, max drawdown
4. Accept if: Win rate >40%, profit factor >1.5, max drawdown <-10%

**Example**:
```bash
# Run backtest
python -m trading_bot.backtest \
    --strategy bull_flag \
    --symbol AAPL \
    --start-date 2024-07-01 \
    --end-date 2024-10-26

# Output:
# Win rate: 62% (18 wins, 11 losses)
# Profit factor: 2.3 ($4,600 profit / $2,000 loss)
# Max drawdown: -4.2%
# Sharpe ratio: 1.8
```

---

### Paper Trading Validation

**When Required**: All changes before production
**Duration**: 24 hours minimum (major changes: 48 hours)

**Process**:
1. Deploy to staging VPS (paper trading mode)
2. Monitor logs for 24-48 hours
3. Validate: No errors, circuit breaker not tripped, trades execute as expected
4. Review trade decisions (were entries/exits correct?)
5. Approve for production deployment

---

## Definition of Done

**Checklist before merging to main**:

- [ ] **Code Complete**
  - [ ] Feature implemented per requirements
  - [ ] Edge cases handled (e.g., market closed, API errors)
  - [ ] Error handling implemented
  - [ ] Logging added (INFO for key events, DEBUG for details)

- [ ] **Tests**
  - [ ] Unit tests added (>80% coverage for new code)
  - [ ] Tests pass locally (`pytest`)
  - [ ] Backtest validates (if strategy change)
  - [ ] Paper trading for 24 hours (no errors)

- [ ] **Code Quality**
  - [ ] Linter passes (`ruff check`)
  - [ ] Type checker passes (`mypy` or Pyright)
  - [ ] No debug prints or commented code
  - [ ] Code reviewed (self-review checklist)

- [ ] **Documentation**
  - [ ] Docstrings for new functions/classes
  - [ ] README updated (if setup changes)
  - [ ] CHANGELOG updated
  - [ ] Constitution compliance noted (which sections apply)

- [ ] **Configuration**
  - [ ] Environment variables documented (if new)
  - [ ] config.json updated (if new parameters)
  - [ ] .env.example updated

**Only merge when all boxes checked**

---

## Issue Tracking

**Tool**: GitHub Issues
**Board**: Projects board (Kanban: Backlog → In Progress → Done)

**Issue Labels**:
- `type:feature` - New feature
- `type:bug` - Bug fix
- `type:enhancement` - Improvement to existing feature
- `type:chore` - Maintenance work
- `priority:high` - Urgent (circuit breaker bug, money-losing bug)
- `priority:medium` - Normal (strategy improvement)
- `priority:low` - Nice-to-have (dashboard UX)
- `size:small` - <4 hours
- `size:medium` - 4-8 hours
- `size:large` - >8 hours (break into smaller tasks)

**Issue Template**:
```markdown
## Description
[What needs to be done]

## Acceptance Criteria
- [ ] Criterion 1 (e.g., Bull flag detector identifies 80%+ of manual signals)
- [ ] Criterion 2 (e.g., Backtest shows profit factor >1.5)

## Technical Notes
- Uses Polygon.io Level 2 data for order flow
- Integrate with existing RiskManager for stop-loss adjustment

## Related
- Spec: specs/028-order-flow-monitor/spec.md
- Research: See research notes in Notion
```

---

## Release Process

**Cadence**: As-needed (no fixed schedule)
**Versioning**: Semantic versioning (MAJOR.MINOR.PATCH)

**Release Workflow**:
1. Accumulate features on `main` branch
2. When ready to release: Tag commit with version
   ```bash
   git tag v1.2.0
   git push origin v1.2.0
   ```
3. Create GitHub release with changelog
4. Deploy to production (live trading VPS)

**Version Bumps**:
- **MAJOR** (1.0.0 → 2.0.0): Breaking changes (e.g., config format change)
- **MINOR** (1.0.0 → 1.1.0): New features (e.g., order flow monitor)
- **PATCH** (1.0.0 → 1.0.1): Bug fixes (e.g., circuit breaker not triggering)

**Hotfix Process** (for critical bugs in production):
1. Branch from `main`: `hotfix/critical-bug`
2. Fix bug
3. Test in paper trading (1 hour minimum, not 24 hours)
4. Merge to `main`
5. Tag as PATCH version (e.g., 1.2.0 → 1.2.1)
6. Deploy immediately

---

## Communication

**Solo Developer**: No daily standups, async documentation

**Documentation**:
- Code comments: For complex logic only (prefer self-documenting code)
- Commit messages: Conventional Commits (clear git history)
- CHANGELOG.md: Track all changes per version
- Notion: Strategy research, trade reviews, lessons learned

---

## Onboarding (Future)

**If adding team members**:

**Day 1**:
- [ ] Access to GitHub repo
- [ ] Access to VPS (SSH key, read-only initially)
- [ ] Read README.md, CLAUDE.md, docs/project/
- [ ] Setup local development environment

**Week 1**:
- [ ] Pair with Marcus on small task (e.g., add indicator)
- [ ] Read codebase: src/trading_bot/ structure
- [ ] Make first PR (small fix or docs improvement)

**Month 1**:
- [ ] Ship first feature to production
- [ ] Understand trading strategy (backtest, paper trading)
- [ ] Review trade decisions (why did we enter/exit?)

---

## Tools & Subscriptions

**Development**:
- GitHub (version control, issues)
- VS Code / Cursor (IDE)
- Ruff (linting, formatting)
- pytest (testing)
- Postman (API testing, future)

**Monitoring**:
- CLI dashboard (rich library, terminal UI)
- VPS logs (Docker logs, file-based)
- Hetzner dashboard (VPS metrics)

**Infrastructure**:
- Hetzner VPS (CX11)
- Docker + Docker Compose
- GitHub (code hosting)

**Trading APIs**:
- Robinhood (unofficial API, free)
- Alpaca Markets (market data, free tier)
- Polygon.io (Level 2 data, $99/mo)
- OpenAI (GPT-4o-mini, $20-40/mo)

**Cost**: ~$131-151/mo (see capacity-planning.md)

---

## Best Practices

### Code Reviews (Self-Review)

**As Solo Developer**:
- Review own code before committing (pretend someone else wrote it)
- Read commit diff: Does it make sense? Any unintended changes?
- Run tests before pushing
- Use PR checklist (even if not creating PRs)

**Red Flags** (don't commit):
- Hard-coded credentials (use `.env`)
- Magic numbers (extract to config)
- Large commits (>500 lines) - break into smaller commits
- Commented-out code (delete it, git history preserves)

---

### Debugging

**Process**:
1. Reproduce the bug (in local env or paper trading)
2. Add logging (DEBUG level, narrow down where it fails)
3. Write failing test that captures the bug
4. Fix the bug
5. Verify test now passes
6. Remove debug logging (or lower to TRACE level)

**Tools**:
- Python debugger (pdb, VS Code debugger)
- Logs (grep for ERROR, CRITICAL)
- Backtest (reproduce historical bug)

**Example**:
```python
# Debugging circuit breaker not triggering
import logging
logger = logging.getLogger(__name__)

def check_circuit_breaker(daily_pnl: Decimal, limit_pct: Decimal):
    logger.debug(f"Checking circuit breaker: daily_pnl={daily_pnl}, limit={limit_pct}")

    if abs(daily_pnl) > limit_pct:
        logger.critical(f"Circuit breaker TRIPPED: {daily_pnl} > {limit_pct}")
        return True

    logger.debug("Circuit breaker OK")
    return False
```

---

### Performance

**Monitor**:
- Trade execution time (should be <2s)
- API response time (Alpaca, Polygon.io)
- Log write latency (<10ms)
- Memory usage (bot should use <200MB RAM)

**Optimize**:
- Cache market data (avoid redundant API calls)
- Batch log writes (append to buffer, flush periodically)
- Use Redis for LLM caching (avoid $0.15/call to OpenAI)

---

## Change Log

| Date | Change | Reason | Impact |
|------|--------|--------|--------|
| 2025-10-26 | Initial development workflow | Document solo dev process | Foundation for team expansion |
| 2025-10-01 | Adopted Conventional Commits | Better changelog generation | Clear git history |
| 2025-09-20 | Added self-review checklist | Reduce bugs before merge | Improved code quality |
| 2025-09-15 | Defined backtest validation requirement | Safety net for strategy changes | All strategy changes backtested |
