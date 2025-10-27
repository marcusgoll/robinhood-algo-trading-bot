# Trading Bot Constitution

**Version**: v1.0.0
**Amended**: 2025-10-07
**Project**: Robinhood Stock Trading Bot

---

## Core Principles

### §Safety_First
- **Never trade with real money until fully tested** - All development uses paper trading/sandbox
- **Implement circuit breakers** - Hard limits on losses, trades per day, position sizes
- **Fail safe, not fail open** - Errors halt trading, never continue blindly
- **Audit everything** - Every trade decision must be logged with reasoning

### §Code_Quality
- **Type hints required** - All Python code must use type annotations
- **Test coverage ≥90%** - Financial code demands rigorous testing
- **One function, one purpose** - KISS principle for maintainability
- **No duplicate logic** - DRY principle enforced strictly

### §Risk_Management
- **Position sizing mandatory** - Never exceed 5% portfolio per position
- **Stop losses required** - Every position must have defined exit criteria
- **Validate all inputs** - API responses, user inputs, configuration
- **Rate limit protection** - Respect Robinhood API limits, implement backoff

### §Security
- **No credentials in code** - Use environment variables or secure vault
- **API keys encrypted** - Never commit plaintext secrets
- **Minimal permissions** - Request only needed OAuth scopes
- **Session management** - Proper token refresh and expiry handling

### §Data_Integrity
- **Validate market data** - Check timestamps, bounds, data completeness
- **Handle missing data** - Never assume data availability
- **Time zone awareness** - All timestamps in UTC, convert for display
- **Data retention** - Keep trade history for analysis and compliance

### §Testing_Requirements
- **Unit tests** - Every function has isolated tests
- **Integration tests** - API interaction tests with mocking
- **Backtesting** - Strategy validation against historical data
- **Paper trading** - Live testing without real money

## Quality Gates

### §Pre_Commit
- All tests pass (`pytest`)
- Type checking passes (`mypy`)
- Linting clean (`ruff` or `pylint`)
- No security issues (`bandit`)

### §Pre_Deploy
- 90%+ test coverage
- No high-severity vulnerabilities
- Paper trading validation passed
- Risk limits configured correctly

### §Production_Readiness
- Circuit breakers tested and active
- Logging to persistent storage
- Error alerting configured
- Manual kill switch implemented

## Technology Constraints

### §Stack
- **Language**: Python 3.11+
- **Trading**: `robin_stocks` library
- **Data**: `pandas`, `numpy` for analysis
- **Testing**: `pytest`, `pytest-mock`
- **Type checking**: `mypy`

### §Architecture
- **Strategy pattern** - Pluggable trading strategies
- **Repository pattern** - Abstract data access
- **Dependency injection** - Testable components
- **Event-driven** - Async market data handling

### §Dependencies
- Pin all versions - Reproducible builds
- Minimal dependencies - Reduce attack surface
- Security audits - Regular `pip-audit` checks

## Development Workflow

### §Iteration_Cycle
1. Write specification with acceptance criteria
2. Write tests first (TDD)
3. Implement minimum viable code
4. Refactor for clarity
5. Paper trade validation
6. Code review before merge

### §Documentation
- Docstrings required - All public functions
- Strategy documentation - Explain logic and parameters
- Risk documentation - Document all risk controls
- Runbooks - Operations and troubleshooting

## Anti-Patterns (Never Do)

### §Forbidden
- ❌ Trade without stop losses
- ❌ Ignore API errors
- ❌ Hard-code credentials
- ❌ Skip paper trading validation
- ❌ Deploy without circuit breakers
- ❌ Use mutable default arguments
- ❌ Catch bare exceptions without logging

## Compliance Notes

- This bot is for **personal use only**
- Not financial advice - Educational/experimental purposes
- User responsible for tax reporting
- Comply with Robinhood Terms of Service
- Pattern day trading rules apply

---

**Constitution is SSOT** - All templates and commands reference these principles.

---

## Project Documentation

**Location**: `docs/project/`

Comprehensive project-level design documentation:
- `overview.md` - Vision, users, scope, success metrics
- `system-architecture.md` - Components, integrations, Mermaid diagrams, C4 models
- `tech-stack.md` - Technology choices with rationale
- `data-architecture.md` - Data sources, storage strategy, log schemas, data lifecycle
- `api-strategy.md` - REST patterns, auth, versioning, external API integrations
- `capacity-planning.md` - Micro → scale tiers, cost projections
- `deployment-strategy.md` - CI/CD, environments, rollback, disaster recovery
- `development-workflow.md` - Git flow, PR process, Definition of Done

**Created**: 2025-10-26 via `/init-project`

**Maintenance**: Update docs when:
- Adding new module/component (system-architecture.md)
- Changing tech stack or dependencies (tech-stack.md)
- Scaling to next tier (capacity-planning.md)
- Adjusting deployment strategy (deployment-strategy.md)
- Modifying data schemas or adding storage (data-architecture.md)

**Workflow Integration**:
All features MUST align with project architecture:
- `/roadmap` - Checks overview.md for vision alignment
- `/spec` - References project docs during research phase
- `/plan` - Heavily integrates with all 8 docs for architecture decisions
- `/tasks` - Follows patterns from tech-stack.md, api-strategy.md
- `/implement` - Validates against system-architecture.md, data-architecture.md

**Cross-Document Consistency**:
Project docs form a coherent system:
- Tech choices (tech-stack.md) must support architecture (system-architecture.md)
- API design (api-strategy.md) must align with data model (data-architecture.md)
- Capacity planning (capacity-planning.md) must reflect deployment platform (deployment-strategy.md)
- Development workflow (development-workflow.md) must enforce quality gates (§Pre_Commit, §Pre_Deploy)

---

<!-- SYNC IMPACT: v1.0.0
Initial constitution for trading bot project
Last updated: 2025-10-07
Project documentation added: 2025-10-26
-->
