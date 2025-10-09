# Implementation Plan: Robinhood Authentication Module

## [RESEARCH DECISIONS]

### Decision: Use robin-stocks Library for Authentication
- **Decision**: Use existing `robin-stocks==3.0.5` library already in requirements.txt
- **Rationale**:
  - Already a project dependency
  - Handles Robinhood API authentication flow
  - Provides built-in pickle session management
  - Handles token refresh automatically
- **Alternatives**: Direct Robinhood API calls (rejected - unnecessary complexity, reinventing the wheel)
- **Source**: requirements.txt:5, Robinhood API is unofficial and robin-stocks abstracts complexity

### Decision: pyotp for MFA TOTP Generation
- **Decision**: Add `pyotp==2.9.0` for MFA challenge handling
- **Rationale**:
  - TOTP standard (RFC 6238) implementation
  - Lightweight, single-purpose library
  - Compatible with Robinhood's MFA system
  - Used by robin-stocks examples
- **Alternatives**: Manual TOTP implementation (rejected - security risk, complexity)
- **Source**: spec.md FR-002, industry standard for MFA

### Decision: Pickle File for Session Persistence
- **Decision**: Store authenticated session in `.robinhood.pickle` (robin-stocks default)
- **Rationale**:
  - robin-stocks built-in support
  - Transparent session restoration
  - No custom serialization needed
  - Permissions can be set to 600 (owner-only)
- **Alternatives**: JSON session storage (rejected - robin-stocks doesn't support), database storage (rejected - overkill for single-user bot)
- **Source**: spec.md FR-003, robin-stocks documentation

### Decision: Reuse Existing Config and Logger Infrastructure
- **Decision**: Use existing `Config` class and `TradingLogger` system
- **Rationale**:
  - Config already loads ROBINHOOD_* env vars (config.py:36-39)
  - TradingLogger provides UTC timestamps and audit trail (§Audit_Everything)
  - No duplication needed
- **Alternatives**: Create separate auth config/logging (rejected - violates DRY principle)
- **Source**: src/trading_bot/config.py, src/trading_bot/logger.py

### Decision: Service Layer Pattern
- **Decision**: Create `RobinhoodAuth` service class in `src/trading_bot/auth/robinhood_auth.py`
- **Rationale**:
  - Matches existing codebase patterns (safety_checks.py, mode_switcher.py)
  - Encapsulates authentication logic
  - Testable with mocks
  - Single responsibility principle
- **Alternatives**: Integrate directly into bot.py (rejected - violates SRP, hard to test)
- **Source**: Existing codebase pattern analysis

---

## [ARCHITECTURE DECISIONS]

**Stack**:
- Backend: Python 3.11+ (existing)
- Auth Library: robin-stocks==3.0.5 (existing)
- MFA: pyotp==2.9.0 (NEW)
- Config: python-dotenv==1.0.0 (existing)
- Logging: Built-in logging + TradingLogger (existing)
- Testing: pytest + pytest-mock (existing)

**Patterns**:
- **Service Layer**: RobinhoodAuth class encapsulates all authentication logic
- **Dependency Injection**: Config instance passed to RobinhoodAuth constructor
- **Fail-Safe Design**: All auth failures block bot startup (§Safety_First)
- **Separation of Concerns**: Credentials in .env, trading params in config.json
- **Audit Trail**: All auth events logged to logs/trading_bot.log (§Audit_Everything)

**Dependencies** (new packages required):
- `pyotp==2.9.0`: MFA TOTP generation

---

## [STRUCTURE]

**Directory Layout** (follow existing patterns):

```
src/trading_bot/
├── auth/
│   ├── __init__.py
│   └── robinhood_auth.py     # NEW: Authentication service
├── bot.py                     # MODIFIED: Integrate RobinhoodAuth
├── config.py                  # UNMODIFIED: Already has credential fields
└── logger.py                  # UNMODIFIED: Reuse existing logging

tests/
├── unit/
│   └── test_robinhood_auth.py # NEW: Unit tests for auth service
└── integration/
    └── test_auth_integration.py # NEW: Integration tests with bot

.robinhood.pickle              # NEW: Session storage (gitignored)
```

**Module Organization**:
- `auth/robinhood_auth.py`: Core authentication service (login, logout, session management)
- `bot.py`: Modified to call RobinhoodAuth during startup
- Tests: Comprehensive unit + integration tests (≥90% coverage per NFR-005)

---

## [SCHEMA]

**No Database Changes** - Authentication state stored in pickle file only.

**API Schema** (robin-stocks internal):
```python
# robin_stocks.login() returns session object (opaque)
# We don't need to define schema - library handles it
```

**State Shape** (RobinhoodAuth class):
```python
@dataclass
class AuthConfig:
    """Authentication configuration from Config instance."""
    username: str
    password: str
    mfa_secret: Optional[str] = None
    device_token: Optional[str] = None
    pickle_path: str = ".robinhood.pickle"

class RobinhoodAuth:
    """Authentication service for Robinhood API."""
    _session: Optional[Any] = None  # robin_stocks session object
    _authenticated: bool = False
    _config: AuthConfig
    _logger: logging.Logger
```

---

## [PERFORMANCE TARGETS]

**From spec.md NFRs**:
- NFR-004: Login with pickle <2 seconds
- NFR-004: Login with username/password <10 seconds
- NFR-004: Token refresh <5 seconds
- NFR-004: Must NOT block trading operations during refresh

**No Lighthouse Targets** (backend-only feature)

---

## [SECURITY]

**Authentication Strategy**:
- Environment variables only (ROBINHOOD_USERNAME, ROBINHOOD_PASSWORD)
- Optional MFA secret (ROBINHOOD_MFA_SECRET) for enhanced security
- Optional device token (ROBINHOOD_DEVICE_TOKEN) for faster auth

**Credential Protection** (NFR-001):
- NO credentials in logs (username, password, MFA secret masked)
- Pickle file permissions set to 600 (owner read/write only)
- Credentials cleared from memory after use
- All inputs validated before use

**Error Handling**:
- Invalid credentials → block bot startup (§Safety_First)
- MFA failure → clear error message, block startup
- Network errors → retry with exponential backoff (§Error_Handling)
- Corrupt pickle → delete and re-authenticate

**Input Validation** (FR-007):
- Username must be valid email format
- Password must not be empty
- MFA secret must be valid base32 (if provided)
- Device token format validated (if provided)

**Data Protection**:
- Session tokens never logged
- Pickle file in .gitignore
- No PII in error messages
- UTC timestamps for all logs (§Data_Integrity)

---

## [EXISTING INFRASTRUCTURE - REUSE] (5 components)

**Configuration**:
- `src/trading_bot/config.py`: Config class with ROBINHOOD_* env var support (lines 36-39)
- `.env.example`: Template with credential fields already documented

**Logging**:
- `src/trading_bot/logger.py`: TradingLogger with UTC timestamps, file rotation, audit trail

**Testing**:
- `tests/unit/`: Existing pytest infrastructure with pytest-mock
- `tests/integration/`: Existing integration test patterns

**Utilities**:
- `python-dotenv==1.0.0`: Environment variable loading (already in requirements.txt)
- `robin-stocks==3.0.5`: Robinhood API client (already in requirements.txt)

---

## [NEW INFRASTRUCTURE - CREATE] (3 components)

**Backend**:
- `src/trading_bot/auth/robinhood_auth.py`: Authentication service class
  - Methods: login(), logout(), get_session(), refresh_token(), is_authenticated()
  - Private methods: _login_with_pickle(), _login_with_credentials(), _handle_mfa_challenge(), _save_session(), _validate_credentials()

**Testing**:
- `tests/unit/test_robinhood_auth.py`: Unit tests for RobinhoodAuth
  - Test scenarios: credential loading, login flows, session persistence, token refresh, logout, error handling
  - Target: ≥90% coverage per NFR-005
- `tests/integration/test_auth_integration.py`: Integration tests with bot.py
  - Test scenarios: bot startup with auth, session restoration, MFA challenge, auth failure handling

**Dependencies**:
- Add `pyotp==2.9.0` to requirements.txt

---

## [CI/CD IMPACT]

**From spec.md deployment considerations:**
- Platform: N/A (backend-only, no platform coupling)
- Env vars: No new env vars (ROBINHOOD_* already documented in .env.example)
- Breaking changes: No (new module, additive only)
- Migration: No database changes

**Build Commands**:
- No changes to build process

**Environment Variables** (already documented):
```bash
# Required (already in .env.example)
ROBINHOOD_USERNAME=your_email@example.com
ROBINHOOD_PASSWORD=your_secure_password

# Optional (already in .env.example)
ROBINHOOD_MFA_SECRET=BASE32_ENCODED_SECRET
ROBINHOOD_DEVICE_TOKEN=your_device_token
```

**Dependencies Update**:
```bash
# Add to requirements.txt
pyotp==2.9.0  # MFA TOTP generation
```

**Gitignore Update** (if needed):
```bash
# Ensure these are in .gitignore
.env
.robinhood.pickle
*.pickle
```

**Database Migrations**:
- None required (pickle file storage only)

**Smoke Tests** (manual validation):
- Bot startup with valid credentials → successful login
- Bot startup with pickle file → session restored
- Bot startup with invalid credentials → fails safely
- Bot startup with MFA → challenge handled correctly

**Platform Coupling**:
- None (pure Python backend service)

---

## [DEPLOYMENT ACCEPTANCE]

**Production Invariants** (must hold true):
- .env file exists with valid ROBINHOOD_USERNAME and ROBINHOOD_PASSWORD
- .robinhood.pickle has 600 permissions (owner-only) if exists
- No credentials logged in logs/trading_bot.log
- Bot fails to start if authentication fails (fail-safe)

**Staging Smoke Tests** (Given/When/Then):
```gherkin
Given valid credentials in .env
When bot starts for first time
Then authentication succeeds
  And .robinhood.pickle created with 600 permissions
  And "Authentication successful" in logs
  And no credentials visible in logs

Given .robinhood.pickle exists with valid session
When bot restarts
Then session restored without re-login
  And "Session restored from cache" in logs
  And login time <2 seconds

Given invalid credentials in .env
When bot attempts to start
Then bot fails to start
  And clear error message shown
  And no credentials in error logs
```

**Rollback Plan**:
- Remove RobinhoodAuth import from bot.py
- Bot falls back to previous behavior (no auth)
- Delete .robinhood.pickle if needed
- No database rollback required

**Artifact Strategy** (build-once-promote-many):
- N/A (backend-only, no artifacts to promote)
- Changes deployed via git pull + dependency update

---

## [INTEGRATION SCENARIOS]

**From quickstart perspective:**

### Scenario 1: Initial Setup (First-Time Developer)
```bash
# Install dependencies (including new pyotp)
pip install -r requirements.txt

# Create .env from example
cp .env.example .env

# Edit .env with your Robinhood credentials
nano .env  # Add ROBINHOOD_USERNAME, ROBINHOOD_PASSWORD, optionally ROBINHOOD_MFA_SECRET

# Verify .robinhood.pickle doesn't exist yet
ls -la .robinhood.pickle  # Should not exist

# Start bot (will authenticate on first run)
python -m src.trading_bot.bot

# Verify pickle created with correct permissions
ls -la .robinhood.pickle  # Should show -rw------- (600)
```

### Scenario 2: Validation (Developer Testing)
```bash
# Run unit tests for auth module
pytest tests/unit/test_robinhood_auth.py -v

# Run integration tests
pytest tests/integration/test_auth_integration.py -v

# Run all tests with coverage
pytest tests/ --cov=src.trading_bot.auth --cov-report=term-missing

# Check types
mypy src/trading_bot/auth/

# Security scan
bandit -r src/trading_bot/auth/

# Verify no credentials in logs
grep -i "password\|secret\|token" logs/trading_bot.log  # Should find none
```

### Scenario 3: Manual Testing (QA)
1. **First-time login**:
   - Delete .robinhood.pickle
   - Start bot
   - Verify: Login succeeds, pickle created, logged "Authentication successful"

2. **Session restoration**:
   - Keep .robinhood.pickle
   - Restart bot
   - Verify: Login <2s, no re-authentication, logged "Session restored from cache"

3. **MFA challenge** (if ROBINHOOD_MFA_SECRET set):
   - Delete .robinhood.pickle
   - Start bot
   - Verify: MFA handled automatically via pyotp, login succeeds

4. **Invalid credentials**:
   - Set wrong password in .env
   - Try to start bot
   - Verify: Bot fails to start, clear error message, no credentials in logs

5. **Logout**:
   - Run bot.stop() or Ctrl+C
   - Verify: Logged "Logout successful", .robinhood.pickle deleted

### Scenario 4: Monitoring (Production)
```bash
# Check authentication status
grep "Authentication" logs/trading_bot.log | tail -5

# Monitor session restoration
grep "Session restored" logs/trading_bot.log | tail -5

# Check for auth errors
grep "ERROR.*auth" logs/errors.log | tail -10

# Verify pickle permissions (security audit)
ls -la .robinhood.pickle  # Should be -rw------- (600)

# Check for credential leaks (security audit)
grep -rni "password\|secret\|token" logs/  # Should find no actual values
```

---

## [TESTING STRATEGY]

**Test Coverage Target**: ≥90% per NFR-005

### Unit Tests (`tests/unit/test_robinhood_auth.py`)

**Credential Loading**:
- ✅ Valid credentials from Config → AuthConfig created
- ✅ Missing username → ValueError raised
- ✅ Missing password → ValueError raised
- ✅ Invalid email format → ValueError raised
- ✅ Optional MFA secret → loaded successfully
- ✅ Optional device token → loaded successfully

**Login Flow**:
- ✅ No pickle, first login → username/password authentication
- ✅ Valid pickle exists → session restored
- ✅ Corrupt pickle → deleted and re-authenticate
- ✅ MFA challenge → handled with pyotp
- ✅ Device token → MFA skipped
- ✅ Invalid credentials → AuthenticationError raised
- ✅ Network error → retry with exponential backoff
- ✅ MFA failure → clear error message

**Session Management**:
- ✅ Save session → pickle created with 600 permissions
- ✅ Load session → session restored correctly
- ✅ Pickle permissions → verified 600 (owner-only)
- ✅ Session validation → expired sessions detected

**Token Refresh**:
- ✅ Token expires → auto-refresh triggered
- ✅ Refresh succeeds → pickle updated
- ✅ Refresh fails → AuthenticationError raised
- ✅ Multiple refresh attempts → exponential backoff

**Logout**:
- ✅ Logout called → robin_stocks.logout() invoked
- ✅ Pickle deleted → .robinhood.pickle removed
- ✅ Logout error → handled gracefully

**Security**:
- ✅ Credentials NOT in logs → verified via log inspection
- ✅ Credentials NOT in error messages → verified
- ✅ Pickle permissions → 600 enforced
- ✅ Input validation → all inputs sanitized

### Integration Tests (`tests/integration/test_auth_integration.py`)

**Bot Startup Flow**:
- ✅ Bot starts with valid credentials → authentication succeeds
- ✅ Bot starts with pickle → session restored
- ✅ Bot starts with invalid credentials → fails safely
- ✅ Bot starts with MFA → challenge handled

**End-to-End Authentication**:
- Mock robin_stocks.login() responses
- Mock robin_stocks.logout() behavior
- Test complete login → trade → logout flow
- Verify audit trail in logs

---

## [OPEN QUESTIONS]

None - Specification is clear and all dependencies are known.

---

## [RISKS & MITIGATIONS]

**Risk 1: robin-stocks API Changes**
- **Impact**: High (authentication breaks)
- **Probability**: Low (stable library)
- **Mitigation**: Pin version (3.0.5), monitor for updates, comprehensive tests

**Risk 2: Robinhood API Rate Limiting**
- **Impact**: Medium (login failures)
- **Probability**: Medium (unofficial API)
- **Mitigation**: Implement exponential backoff, session caching, device token support

**Risk 3: Pickle File Corruption**
- **Impact**: Medium (re-authentication needed)
- **Probability**: Low (stable format)
- **Mitigation**: Detect corruption, auto-delete, re-authenticate, log error

**Risk 4: MFA Secret Leakage**
- **Impact**: Critical (account compromise)
- **Probability**: Low (if following security practices)
- **Mitigation**: Never log secrets, .env in .gitignore, file permissions, security audit

---

## [SUCCESS CRITERIA]

From spec.md:
- [ ] All 7 functional requirements implemented
- [ ] Test coverage ≥90% (NFR-005)
- [ ] Successful login with username/password + MFA
- [ ] Session restored from pickle on bot restart
- [ ] Token auto-refresh on expiry
- [ ] Logout cleans up session and pickle
- [ ] Credentials never logged or exposed (NFR-001)
- [ ] mypy passes with no errors (NFR-006)
- [ ] bandit security scan clean

---

## [IMPLEMENTATION PHASES]

**Phase 1: Core Authentication** (1-2 hours)
1. Create `src/trading_bot/auth/` directory
2. Implement `RobinhoodAuth` class skeleton
3. Implement `_validate_credentials()` method
4. Implement basic `login()` with username/password

**Phase 2: Session Management** (1-2 hours)
1. Implement `_save_session()` with pickle
2. Implement `_login_with_pickle()`
3. Implement session restoration logic
4. Set pickle file permissions to 600

**Phase 3: MFA Support** (1 hour)
1. Add pyotp dependency
2. Implement `_handle_mfa_challenge()`
3. Integrate device token support

**Phase 4: Token Refresh** (1 hour)
1. Implement `refresh_token()` method
2. Implement auto-refresh on 401 errors
3. Add exponential backoff logic

**Phase 5: Integration** (1 hour)
1. Integrate RobinhoodAuth into bot.py
2. Call login() during bot startup
3. Call logout() during bot shutdown
4. Add error handling

**Phase 6: Testing** (2-3 hours)
1. Write unit tests (target 90% coverage)
2. Write integration tests
3. Run security scan (bandit)
4. Manual testing (all scenarios)

**Total Estimate**: 7-10 hours
