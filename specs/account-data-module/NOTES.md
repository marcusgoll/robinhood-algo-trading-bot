# Account Data Module - Research & Planning Notes

**Feature**: account-data-module
**Date**: 2025-01-08
**Status**: Phase 0 - Specification Complete

---

## Research Findings

### Existing Codebase Patterns

**Authentication Pattern** (authentication-module):
- ✅ Established pattern: Service class with auth dependency injection
- ✅ Clear separation: AuthConfig (dataclass) + RobinhoodAuth (service)
- ✅ Error handling: Exponential backoff retry (1s, 2s, 4s)
- ✅ Security: Credential masking via _mask_credential() helper
- ✅ Caching: Pickle-based session persistence with TTL validation

**Bot Integration Pattern** (bot.py):
- ✅ Optional dependency injection via constructor parameter
- ✅ Backward compatibility: Module works with or without new feature
- ✅ Mock values for testing: get_buying_power() returns $10k (line 251)
- ✅ TODO comment: "TODO: Integrate with account-data-module when available" (line 247)

**SafetyChecks Pattern** (safety_checks.py):
- ✅ Dependency injection: Accepts config in __init__
- ✅ Parameter flexibility: current_buying_power parameter allows external value
- ✅ Integration point: validate_trade() can accept buying power override

### robin-stocks API Research

**Available Account Endpoints**:

1. **load_account_profile()** - Primary account data source
   ```python
   profile = robin_stocks.robinhood.account.load_account_profile()
   # Returns dict with:
   # - 'buying_power': str (e.g., '10000.50')
   # - 'equity': str (total account value)
   # - 'day_trade_count': str (e.g., '0')
   # - 'cash': str (cash balance)
   ```

2. **build_holdings()** - Position data with P&L
   ```python
   holdings = robin_stocks.robinhood.account.build_holdings()
   # Returns dict keyed by symbol:
   # {
   #   'AAPL': {
   #     'quantity': '10',
   #     'average_buy_price': '150.25',
   #     'price': '155.00',  # Current price
   #     'equity': '1550.00',  # quantity × price
   #     'percent_change': '3.16',
   #     'equity_change': '47.50',
   #     ...
   #   }
   # }
   ```

3. **get_day_trades_info()** - Day trade details
   ```python
   day_trades = robin_stocks.robinhood.account.get_day_trades_info()
   # Returns list of recent day trades
   # But day_trade_count is simpler from load_account_profile()
   ```

**API Performance**:
- load_account_profile(): ~500ms-1s typical response time
- build_holdings(): ~1-2s for accounts with multiple positions
- Rate limits: Robinhood enforces rate limits (exact limit undocumented)
- Best practice: Cache aggressively to avoid 429 errors

### Identified Integration Points

1. **TradingBot.get_buying_power()** (bot.py:240-251)
   - Current: Returns hardcoded 10000.00
   - Change: Return self.account_data.get_buying_power() if initialized
   - Fallback: Keep mock value for backward compatibility

2. **TradingBot.execute_trade()** (bot.py:253-324)
   - Current: Uses get_buying_power() for SafetyChecks
   - Change: Invalidate cache after successful trade
   - Integration: self.account_data.invalidate_cache('buying_power')

3. **SafetyChecks.validate_trade()** (safety_checks.py)
   - Current: Accepts current_buying_power as parameter
   - Change: Optionally fetch from AccountData if not provided
   - Backward compatible: Parameter still works if provided

4. **Circuit Breaker Daily Loss Calculation**
   - Current: Uses portfolio_value parameter in check_and_trip()
   - Change: Fetch from AccountData.get_account_balance()
   - Integration point: SafetyChecks needs AccountData reference

### Caching Strategy Research

**Cache Requirements**:
- Minimize API calls to avoid rate limiting
- Balance freshness vs performance
- Invalidate on state changes (trades)
- Handle concurrent access (threading safety not required for MVP)

**Proposed TTLs** (based on data volatility):
- buying_power: 60s (changes on trades)
- positions: 60s (changes on trades + price fluctuations)
- account_balance: 60s (changes on trades)
- day_trade_count: 300s (5 min - rarely changes)

**Cache Implementation Options**:
1. ✅ **In-memory dict with timestamps** (CHOSEN)
   - Pros: Simple, fast, no dependencies
   - Cons: Lost on restart (acceptable - session-scoped data)
   - Implementation: `self._cache = {'buying_power': CacheEntry(...)}`

2. ❌ functools.lru_cache (NOT CHOSEN)
   - Pros: Built-in, automatic
   - Cons: No TTL support, can't invalidate selectively

3. ❌ redis/memcached (NOT CHOSEN)
   - Pros: Persistent, distributed
   - Cons: Overkill for single-process bot, external dependency

### P&L Calculation Research

**Formula** (from robin-stocks build_holdings):
```python
# Cost basis
cost_basis = Decimal(quantity) * Decimal(average_buy_price)

# Current value
current_value = Decimal(quantity) * Decimal(current_price)

# Profit/Loss
profit_loss = current_value - cost_basis

# P/L Percentage
profit_loss_pct = (profit_loss / cost_basis) * 100
```

**Edge Cases**:
- Zero quantity: P&L = 0 (no position)
- Negative quantity: Short positions (future enhancement)
- Fractional shares: Robinhood supports, use Decimal for precision

### Error Handling Research

**Expected Errors**:

1. **Network Errors** (requests.exceptions.ConnectionError)
   - Mitigation: Exponential backoff retry (pattern from authentication-module)
   - Retry delays: 1s, 2s, 4s (max 3 attempts)

2. **Rate Limit** (429 Too Many Requests)
   - Mitigation: Exponential backoff with longer delays
   - Cache aggressively to prevent hitting limits

3. **Authentication Errors** (401 Unauthorized)
   - Mitigation: Trigger RobinhoodAuth.refresh_token()
   - If refresh fails: Raise AuthenticationError (bot stops)

4. **API Response Errors** (malformed JSON, missing fields)
   - Mitigation: Validate response structure
   - Fallback: Return cached value or raise ValueError

5. **Empty Account** (no positions, zero balance)
   - Mitigation: Handle gracefully (return empty list, 0.0)
   - Not an error condition

### Security Considerations

**Data Sensitivity**:
- Account numbers: HIGH (never log)
- Account balance: MEDIUM (mask in logs: "$X,XXX.XX" → "$X,***.**")
- Position symbols: LOW (can log)
- Position P&L: MEDIUM (mask specific values)

**Logging Strategy** (§Audit_Everything compliance):
- ✅ Log API calls: "Fetching buying power"
- ✅ Log cache behavior: "Cache hit: buying_power"
- ✅ Log data freshness: "Data age: 45s (TTL: 60s)"
- ❌ Don't log exact balances: Use "Buying power: $X,XXX.XX"
- ❌ Don't log account IDs

### Testing Strategy

**Unit Test Categories**:
1. Data Model Tests (Position, AccountBalance, CacheEntry)
2. Cache Logic Tests (hit, miss, stale, invalidation)
3. API Fetch Tests (mocked robin-stocks responses)
4. P&L Calculation Tests (profit, loss, percentage)
5. Error Handling Tests (network, rate limit, auth)

**Integration Test Categories**:
1. Bot Integration (get_buying_power, cache invalidation)
2. SafetyChecks Integration (buying power validation)
3. Authentication Integration (session usage)

**Mock Strategy**:
- Mock robin_stocks.robinhood.account.* functions
- Use unittest.mock.patch for all API calls
- Create fixture data for realistic API responses

### Dependencies

**No New External Dependencies**:
- ✅ robin-stocks==3.0.5 (already in requirements.txt)
- ✅ Standard library: datetime, typing, dataclasses, decimal
- ✅ Internal: RobinhoodAuth (authentication-module)

**Backward Compatibility**:
- ✅ TradingBot works with or without AccountData
- ✅ SafetyChecks fallback to parameter-based buying power
- ✅ No breaking changes to existing tests

---

## Architecture Decisions

### Decision 1: Cache Storage (In-Memory Dict)
**Context**: Need fast, TTL-based cache for account data
**Decision**: Use in-memory dict with CacheEntry dataclass
**Rationale**:
- Simple implementation (no external dependencies)
- Fast access (<10ms)
- Session-scoped data (doesn't need persistence)
- Easy invalidation for specific keys

**Alternatives Considered**:
- functools.lru_cache: No TTL support
- redis: Overkill for single-process bot
- pickle: Too slow, persistence not needed

### Decision 2: P&L Calculation (Use robin-stocks build_holdings)
**Context**: Need position P&L for portfolio tracking
**Decision**: Use build_holdings() API which includes current prices and equity
**Rationale**:
- API already calculates current value and P&L
- Avoids separate price fetching
- Single API call for all position data

**Alternatives Considered**:
- Fetch positions + separate price lookup: More API calls
- Cache prices separately: Added complexity

### Decision 3: TTL Values (60s for volatile data, 300s for stable)
**Context**: Balance data freshness vs API rate limiting
**Decision**:
- 60s TTL for buying_power, positions, balance (volatile)
- 300s TTL for day_trade_count (stable)
**Rationale**:
- 60s provides near-real-time data without hammering API
- day_trade_count changes infrequently (once per trade cycle)
- Invalidation on trades ensures accuracy after state changes

**Alternatives Considered**:
- 30s TTL: Too aggressive (more API calls)
- 120s TTL: Data too stale for trading decisions
- No cache: Risk of rate limiting

### Decision 4: Integration Pattern (Optional Dependency Injection)
**Context**: Need to integrate with TradingBot without breaking existing code
**Decision**: Optional AccountData initialization, backward compatible fallback
**Rationale**:
- Matches authentication-module pattern (optional config parameter)
- Existing tests continue to work (mock buying power still available)
- Gradual migration path

**Alternatives Considered**:
- Required dependency: Would break existing tests
- Global singleton: Poor testability

---

## Implementation Notes

### Phase Execution Plan

**Phase 0: Specify** (✅ COMPLETE)
- [x] Research robin-stocks API
- [x] Identify integration points
- [x] Define requirements and data models
- [x] Create spec.md

**Phase 1: Plan** (NEXT)
- [ ] Architecture diagrams
- [ ] Detailed task breakdown (T001-T050)
- [ ] Risk mitigation strategies
- [ ] Dependencies mapping

**Phase 2: Tasks** (TDD Approach)
- [ ] RED: Write failing tests for data models
- [ ] RED: Write failing tests for cache logic
- [ ] RED: Write failing tests for API fetching
- [ ] GREEN: Implement data models
- [ ] GREEN: Implement cache layer
- [ ] GREEN: Implement API fetching
- [ ] REFACTOR: Type hints, logging, error handling
- [ ] Integration tests

**Phase 3: Analyze**
- [ ] Code review
- [ ] Test coverage validation (≥90%)
- [ ] Performance testing
- [ ] Security audit

**Phase 4: Optimize**
- [ ] Performance optimization
- [ ] Cache hit ratio analysis
- [ ] API call minimization

**Phase 5: Ship**
- [ ] Deployment readiness checklist
- [ ] Documentation (NOTES.md, DEPLOYMENT_READY.md)
- [ ] Git commit with atomic changes
- [ ] Roadmap update (Backlog → In Progress → Shipped)

---

## Key Patterns to Follow

### TDD Workflow
```
RED → GREEN → REFACTOR
1. Write failing test
2. Run test (should fail)
3. Write minimal code to pass
4. Run test (should pass)
5. Refactor for quality
6. Repeat
```

### Constitution Compliance
- §Security: Never log account numbers, mask sensitive values
- §Risk_Management: Day trade count enforcement, buying power validation
- §Audit_Everything: Log all API calls, cache events, errors
- §Testing_Requirements: ≥90% coverage, comprehensive error scenarios
- §Code_Quality: Type hints, docstrings, KISS/DRY principles
- §Error_Handling: Exponential backoff, graceful degradation, cached fallback

### Git Commit Style
```
feat: implement account data fetching module

- Add AccountData service with robin-stocks integration
- Implement TTL-based caching (60s for volatile, 300s for stable)
- Add Position dataclass with P&L calculations
- Integrate with TradingBot.get_buying_power()
- Add exponential backoff retry for API errors

Resolves: account-data-module (FR-001 through FR-007)
Tests: 25 unit + 5 integration (100% pass rate, 92% coverage)

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

---

## Next Steps

1. **Immediate**: Run /plan to create detailed architecture and task breakdown
2. **After /plan**: Run /tasks to generate TDD task list (T001-T050)
3. **After /tasks**: Run /implement to execute tasks with RED → GREEN → REFACTOR
4. **After /implement**: Run /optimize for code review and performance tuning
5. **After /optimize**: Run /ship to create deployment artifacts and commit

---

## References

- **Roadmap**: `.specify/memory/roadmap.md` (account-data-module requirements)
- **Constitution**: `.specify/memory/constitution.md` (compliance principles)
- **Auth Pattern**: `specs/authentication-module/spec.md` (service pattern reference)
- **robin-stocks Docs**: https://robin-stocks.readthedocs.io/en/latest/functions.html
- **Bot Integration**: `src/trading_bot/bot.py:240-251` (get_buying_power mock)
- **SafetyChecks**: `src/trading_bot/safety_checks.py` (buying power validation)

---

## Phase Checkpoints

### Phase 0: Specification (✅ COMPLETE)
- **Date**: 2025-01-08
- **Duration**: ~30 minutes
- **Artifacts**:
  - spec.md (7 functional requirements, 6 non-functional requirements)
  - NOTES.md (research findings, architecture decisions)
- **Key Decisions**:
  - robin-stocks API endpoints identified (load_account_profile, build_holdings)
  - Requirements: buying power, positions, balance, day trade count
  - Caching strategy: 60s TTL for volatile, 300s for stable
- **Status**: ✅ Committed (d8a8b95)

### Phase 1: Planning (✅ COMPLETE)
- **Date**: 2025-01-08
- **Duration**: ~45 minutes
- **Artifacts**:
  - plan.md (consolidated architecture + design decisions)
  - contracts/api.yaml (robin-stocks API reference + internal API specs)
  - error-log.md (initialized for error tracking)
- **Research Summary**:
  - Codebase patterns analyzed: 8 reusable components identified
  - Architecture decisions: 7 major decisions documented
  - Integration points: bot.py, safety_checks.py, auth module
- **Key Decisions**:
  1. Service pattern following RobinhoodAuth model
  2. In-memory dict cache with TTL (60s/300s)
  3. Reuse _retry_with_backoff() for network resilience
  4. Dataclass pattern for Position, AccountBalance, CacheEntry
  5. P&L calculation via build_holdings() API
  6. Optional dependency injection for backward compatibility
  7. TTLs: 60s volatile, 300s stable
- **Reusable Components**: 8
  - RobinhoodAuth service (auth dependency)
  - _retry_with_backoff() helper (exponential backoff)
  - _mask_credential() helper (security logging)
  - Config dataclass pattern
  - bot.get_buying_power() integration point
  - bot.execute_trade() cache invalidation point
  - SafetyChecks integration (buying power validation)
  - Test patterns (GIVEN/WHEN/THEN, unittest.mock)
- **New Components**: 5
  - account_data.py (AccountData service)
  - __init__.py (clean exports)
  - Position, AccountBalance, CacheEntry dataclasses
  - test_account_data.py (unit tests)
  - test_account_integration.py (integration tests)
- **Status**: ✅ Committed (e4df3a5)

### Phase 2: Tasks (✅ COMPLETE)
- **Date**: 2025-01-08
- **Duration**: ~30 minutes
- **Artifacts**:
  - tasks.md (60 concrete TDD tasks)
- **Task Breakdown**:
  - Total tasks: 60
  - RED tasks: 19 (test-first behaviors)
  - GREEN tasks: 14 (implementations)
  - Parallel tasks: 23 (setup, refactor, docs)
  - REFACTOR tasks: 4 (type hints, logging, cleanup)
- **TDD Structure**:
  - Phase 3.1: Setup (T001-T005) - Module structure
  - Phase 3.2: RED - Data Models (T006-T010) - Failing tests
  - Phase 3.3: GREEN - Data Models (T011-T015) - Implementation
  - Phase 3.4: RED - Cache Logic (T016-T020) - Failing tests
  - Phase 3.5: GREEN - Cache (T021-T025) - Implementation
  - Phase 3.6: RED - API Fetching (T026-T032) - Failing tests
  - Phase 3.7: GREEN - API (T033-T039) - Implementation
  - Phase 3.8: REFACTOR (T040-T043) - Type hints, logging, docs
  - Phase 3.9: Integration (T044-T052) - Bot & SafetyChecks
  - Phase 3.10: Testing (T053-T056) - Coverage validation
  - Phase 3.11: Documentation (T057-T059) - DEPLOYMENT_READY.md
  - Phase 3.12: Final Validation (T060)
- **Coverage Target**: ≥90% line coverage (~30-35 tests)
- **Key Tasks**:
  - T011: Position dataclass with P&L calculations
  - T022: get_buying_power with TTL cache
  - T033: get_positions with robin-stocks integration
  - T036: Exponential backoff retry (reuse from auth)
  - T045: Replace bot.get_buying_power() mock
  - T046: Cache invalidation on trade execution
- **Status**: ✅ Committed ([SHA pending])

---

Last Updated: 2025-01-08 (Phase 1 - Planning Complete)
