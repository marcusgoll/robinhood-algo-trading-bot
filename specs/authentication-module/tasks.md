# Tasks: Robinhood Authentication Module

## [CODEBASE REUSE ANALYSIS]

Scanned: src/trading_bot/**/*.py, tests/**/*.py

### [EXISTING - REUSE]
- ✅ Config class (src/trading_bot/config.py:36-39) - Already loads ROBINHOOD_* env vars
- ✅ TradingLogger (src/trading_bot/logger.py) - UTC timestamps, audit trail, file rotation
- ✅ .env.example - Credential fields already documented
- ✅ pytest infrastructure (tests/unit/, tests/integration/) - Existing test patterns
- ✅ robin-stocks==3.0.5 (requirements.txt:5) - Robinhood API client
- ✅ python-dotenv==1.0.0 (requirements.txt:27) - Environment variable loading

### [NEW - CREATE]
- 🆕 RobinhoodAuth service (no existing auth module)
- 🆕 pyotp dependency (MFA TOTP generation)
- 🆕 Unit tests for authentication (test_robinhood_auth.py)
- 🆕 Integration tests with bot (test_auth_integration.py)

---

## Phase 3.1: Setup & Dependencies

### T001 [P] Add pyotp dependency to requirements.txt
- **File**: requirements.txt
- **Action**: Add `pyotp==2.9.0` after python-dotenv line
- **Verify**: pip install -r requirements.txt succeeds
- **From**: plan.md [ARCHITECTURE DECISIONS] - new dependency

### T002 [P] Create auth module directory
- **Command**: mkdir -p src/trading_bot/auth
- **Files**: Create __init__.py with module exports
- **Pattern**: src/trading_bot/utils/__init__.py
- **From**: plan.md [STRUCTURE]

### T003 [P] Update .gitignore for pickle files
- **File**: .gitignore
- **Add**: .robinhood.pickle and *.pickle (if not already present)
- **Verify**: git check-ignore .robinhood.pickle returns match
- **From**: plan.md [CI/CD IMPACT]

---

## Phase 3.2: RED - Write Failing Tests

### T004 [RED] Write test: Config validation - valid credentials loaded
- **File**: tests/unit/test_robinhood_auth.py
- **Test**: test_valid_credentials_loaded_from_config()
- **Given**: Config with ROBINHOOD_USERNAME and ROBINHOOD_PASSWORD set
- **When**: AuthConfig created from Config
- **Then**: username and password populated, optional fields None if not set
- **Pattern**: tests/unit/test_validator.py (config validation tests)
- **From**: spec.md FR-001, plan.md [TESTING STRATEGY]

### T005 [RED] Write test: Config validation - missing username raises ValueError
- **File**: tests/unit/test_robinhood_auth.py
- **Test**: test_missing_username_raises_error()
- **Given**: Config with empty/None ROBINHOOD_USERNAME
- **When**: AuthConfig validation called
- **Then**: ValueError raised with clear message
- **Pattern**: tests/unit/test_validator.py:test_missing_credentials()
- **From**: spec.md FR-007

### T006 [RED] Write test: Config validation - missing password raises ValueError
- **File**: tests/unit/test_robinhood_auth.py
- **Test**: test_missing_password_raises_error()
- **Given**: Config with empty/None ROBINHOOD_PASSWORD
- **When**: AuthConfig validation called
- **Then**: ValueError raised with clear message
- **Pattern**: tests/unit/test_validator.py
- **From**: spec.md FR-007

### T007 [RED] Write test: Config validation - invalid email format raises ValueError
- **File**: tests/unit/test_robinhood_auth.py
- **Test**: test_invalid_email_format_raises_error()
- **Given**: ROBINHOOD_USERNAME is not a valid email (e.g., "notanemail")
- **When**: AuthConfig validation called
- **Then**: ValueError raised with "Invalid email format" message
- **Pattern**: tests/unit/test_validator.py
- **From**: spec.md FR-007

### T008 [RED] Write test: Login with pickle - valid session restored
- **File**: tests/unit/test_robinhood_auth.py
- **Test**: test_login_with_valid_pickle_restores_session()
- **Given**: .robinhood.pickle exists with valid session data
- **When**: RobinhoodAuth.login() called
- **Then**: Session restored without calling robin_stocks.login(), logged "Session restored from cache"
- **Mock**: robin_stocks.login (should NOT be called)
- **Pattern**: tests/unit/test_safety_checks.py (mock external dependencies)
- **From**: spec.md Scenario 2, plan.md [TESTING STRATEGY]

### T009 [RED] Write test: Login without pickle - username/password auth
- **File**: tests/unit/test_robinhood_auth.py
- **Test**: test_first_time_login_with_credentials()
- **Given**: No .robinhood.pickle exists
- **When**: RobinhoodAuth.login() called
- **Then**: robin_stocks.login() called with username/password, session saved to pickle, logged "Authentication successful"
- **Mock**: robin_stocks.login() returns success
- **Pattern**: tests/unit/test_bot.py (mock external API calls)
- **From**: spec.md Scenario 1

### T010 [RED] Write test: Login with MFA - pyotp handles challenge
- **File**: tests/unit/test_robinhood_auth.py
- **Test**: test_mfa_challenge_handled_with_pyotp()
- **Given**: ROBINHOOD_MFA_SECRET set, robin_stocks.login() triggers MFA challenge
- **When**: RobinhoodAuth.login() called
- **Then**: pyotp.TOTP(secret).now() called, MFA code submitted, login succeeds
- **Mock**: pyotp.TOTP, robin_stocks.login() with MFA prompt
- **Pattern**: tests/unit/test_safety_checks.py (mock multiple dependencies)
- **From**: spec.md Scenario 1, FR-002

### T011 [RED] Write test: Login with device token - MFA skipped
- **File**: tests/unit/test_robinhood_auth.py
- **Test**: test_device_token_skips_mfa()
- **Given**: ROBINHOOD_DEVICE_TOKEN set in config
- **When**: RobinhoodAuth.login() called
- **Then**: device_token passed to robin_stocks.login(), MFA NOT triggered, logged "Login via device token"
- **Mock**: robin_stocks.login() with device_token parameter
- **From**: spec.md Scenario 7

### T012 [RED] Write test: Login fails - invalid credentials
- **File**: tests/unit/test_robinhood_auth.py
- **Test**: test_invalid_credentials_raises_auth_error()
- **Given**: Wrong password in config
- **When**: RobinhoodAuth.login() called
- **Then**: robin_stocks.login() returns 401, AuthenticationError raised with clear message, logged "Invalid credentials"
- **Mock**: robin_stocks.login() returns 401 error
- **From**: spec.md Scenario 5, NFR-003

### T013 [RED] Write test: Login fails - MFA challenge fails
- **File**: tests/unit/test_robinhood_auth.py
- **Test**: test_mfa_failure_raises_auth_error()
- **Given**: ROBINHOOD_MFA_SECRET incorrect
- **When**: RobinhoodAuth.login() called
- **Then**: MFA code rejected, AuthenticationError raised, logged "MFA challenge failed"
- **Mock**: robin_stocks.login() rejects MFA code
- **From**: spec.md Scenario 4

### T014 [RED] Write test: Session persistence - pickle saved with 600 permissions
- **File**: tests/unit/test_robinhood_auth.py
- **Test**: test_session_saved_to_pickle_with_correct_permissions()
- **Given**: Successful login
- **When**: Session saved via _save_session()
- **Then**: .robinhood.pickle created, permissions set to 0o600 (owner read/write only)
- **Verify**: os.stat().st_mode & 0o777 == 0o600
- **From**: spec.md FR-003, NFR-001 (security)

### T015 [RED] Write test: Corrupt pickle - deleted and re-authenticate
- **File**: tests/unit/test_robinhood_auth.py
- **Test**: test_corrupt_pickle_deleted_and_reauthenticate()
- **Given**: .robinhood.pickle exists but corrupted (invalid format)
- **When**: RobinhoodAuth.login() called
- **Then**: Pickle load fails, file deleted, username/password auth fallback, logged "Corrupt pickle deleted"
- **Mock**: pickle.load() raises exception
- **From**: spec.md FR-003, plan.md [RISKS & MITIGATIONS]

### T016 [RED] Write test: Logout - session cleared and pickle deleted
- **File**: tests/unit/test_robinhood_auth.py
- **Test**: test_logout_clears_session_and_deletes_pickle()
- **Given**: Authenticated session exists
- **When**: RobinhoodAuth.logout() called
- **Then**: robin_stocks.logout() called, .robinhood.pickle deleted, _authenticated = False, logged "Logout successful"
- **Mock**: robin_stocks.logout()
- **From**: spec.md Scenario 6, FR-006

### T017 [RED] Write test: Token refresh - expired token auto-refreshed
- **File**: tests/unit/test_robinhood_auth.py
- **Test**: test_expired_token_auto_refreshed()
- **Given**: Session exists but access token expired (401 error on API call)
- **When**: RobinhoodAuth.refresh_token() called
- **Then**: robin_stocks token refresh triggered, pickle updated, logged "Token auto-refreshed"
- **Mock**: robin_stocks API call returns 401, then succeeds after refresh
- **From**: spec.md Scenario 3, FR-004

### T018 [RED] Write test: Security - credentials never logged
- **File**: tests/unit/test_robinhood_auth.py
- **Test**: test_credentials_not_in_logs()
- **Given**: Full login flow with username/password/MFA secret
- **When**: Login completes successfully
- **Then**: Scan all log messages, verify username/password/MFA secret NOT present
- **Verify**: caplog fixture, assert sensitive strings not in log output
- **Pattern**: tests/integration/test_bot_safety_integration.py (caplog usage)
- **From**: spec.md NFR-001, plan.md [SECURITY]

---

## Phase 3.3: GREEN - Minimal Implementation

### T019 [GREEN→T004] Implement AuthConfig dataclass
- **File**: src/trading_bot/auth/robinhood_auth.py
- **Class**: AuthConfig (dataclass)
- **Fields**: username (str), password (str), mfa_secret (Optional[str]), device_token (Optional[str]), pickle_path (str = ".robinhood.pickle")
- **Method**: from_config(config: Config) -> AuthConfig (factory method)
- **REUSE**: Config class (src/trading_bot/config.py:36-39) for credential fields
- **Pattern**: src/trading_bot/safety_checks.py:SafetyConfig (dataclass with factory)
- **From**: plan.md [SCHEMA], spec.md FR-001

### T020 [GREEN→T005,T006,T007] Implement credential validation
- **File**: src/trading_bot/auth/robinhood_auth.py
- **Method**: AuthConfig._validate_credentials() -> None
- **Logic**: Check username not empty, valid email format, password not empty
- **Raise**: ValueError with specific message for each failure
- **Pattern**: src/trading_bot/validator.py (validation pattern)
- **From**: spec.md FR-007

### T021 [GREEN→T008] Implement _login_with_pickle()
- **File**: src/trading_bot/auth/robinhood_auth.py
- **Method**: RobinhoodAuth._login_with_pickle() -> Optional[Any]
- **Logic**: Check if pickle exists, load with pickle.load(), validate session still valid, return session or None
- **Exception**: Catch pickle errors, return None (triggers re-auth)
- **Log**: logger.info("Session restored from cache") if successful
- **REUSE**: TradingLogger (src/trading_bot/logger.py)
- **From**: spec.md Scenario 2, FR-003

### T022 [GREEN→T009,T010,T011] Implement _login_with_credentials()
- **File**: src/trading_bot/auth/robinhood_auth.py
- **Method**: RobinhoodAuth._login_with_credentials() -> Any
- **Logic**: Call robin_stocks.login(username, password, mfa_code=None, device_token=None)
- **MFA**: If MFA_SECRET set, call _handle_mfa_challenge() when prompted
- **Device**: If DEVICE_TOKEN set, pass to robin_stocks.login()
- **Return**: Authenticated session object
- **Log**: logger.info("Authentication successful") or logger.info("Login via device token")
- **From**: spec.md Scenario 1, 7, FR-002

### T023 [GREEN→T010] Implement _handle_mfa_challenge()
- **File**: src/trading_bot/auth/robinhood_auth.py
- **Method**: RobinhoodAuth._handle_mfa_challenge() -> str
- **Logic**: import pyotp, code = pyotp.TOTP(mfa_secret).now(), return code
- **Raise**: AuthenticationError if mfa_secret invalid or pyotp fails
- **Log**: logger.debug("MFA code generated") (NOT the code itself)
- **From**: spec.md FR-002, NFR-001 (don't log secret)

### T024 [GREEN→T012,T013] Implement error handling for login failures
- **File**: src/trading_bot/auth/robinhood_auth.py
- **Method**: Update _login_with_credentials() with try/except
- **Catch**: robin_stocks exceptions (401, network errors)
- **Raise**: AuthenticationError with user-friendly message
- **Log**: logger.error("Invalid credentials") or logger.error("MFA challenge failed")
- **Pattern**: src/trading_bot/safety_checks.py (error handling)
- **From**: spec.md Scenario 4, 5, NFR-003

### T025 [GREEN→T014] Implement _save_session()
- **File**: src/trading_bot/auth/robinhood_auth.py
- **Method**: RobinhoodAuth._save_session(session: Any) -> None
- **Logic**: Save session to pickle file, set permissions to 0o600
- **Commands**: pickle.dump(session, file), os.chmod(pickle_path, 0o600)
- **Exception**: Catch IOError, log error but don't fail (session still in memory)
- **From**: spec.md FR-003, NFR-001 (security - 600 permissions)

### T026 [GREEN→T015] Implement corrupt pickle detection and cleanup
- **File**: src/trading_bot/auth/robinhood_auth.py
- **Method**: Update _login_with_pickle() with exception handling
- **Catch**: pickle.UnpicklingError, EOFError, IOError
- **Action**: Delete corrupt pickle file, log warning, return None (triggers re-auth)
- **Log**: logger.warning("Corrupt pickle deleted, re-authenticating")
- **From**: plan.md [RISKS & MITIGATIONS]

### T027 [GREEN→T016] Implement logout()
- **File**: src/trading_bot/auth/robinhood_auth.py
- **Method**: RobinhoodAuth.logout() -> None
- **Logic**: Call robin_stocks.logout(), delete pickle file if exists, set _authenticated = False
- **Exception**: Catch errors gracefully (logout failures non-critical)
- **Log**: logger.info("Logout successful")
- **From**: spec.md Scenario 6, FR-006

### T028 [GREEN→T017] Implement refresh_token()
- **File**: src/trading_bot/auth/robinhood_auth.py
- **Method**: RobinhoodAuth.refresh_token() -> bool
- **Logic**: Let robin_stocks handle refresh internally, update pickle after successful API call
- **Return**: True if refresh successful, False otherwise
- **Log**: logger.info("Token auto-refreshed")
- **From**: spec.md Scenario 3, FR-004

### T029 [GREEN→T018] Implement credential masking in logs
- **File**: src/trading_bot/auth/robinhood_auth.py
- **Action**: Review all logger calls, ensure username/password/mfa_secret NEVER logged
- **Verify**: Only log "Authentication successful", "Session restored", etc. (no sensitive data)
- **Pattern**: Mask sensitive fields if needed (e.g., username[0:3] + "***")
- **From**: spec.md NFR-001, plan.md [SECURITY]

### T030 [GREEN] Implement RobinhoodAuth.login() orchestration
- **File**: src/trading_bot/auth/robinhood_auth.py
- **Method**: RobinhoodAuth.login() -> bool
- **Logic**:
  1. Validate credentials
  2. Try _login_with_pickle() first
  3. If pickle fails, try _login_with_credentials()
  4. Save session to pickle on success
  5. Set _authenticated = True
  6. Return True
- **Exception**: Raise AuthenticationError on failure
- **From**: spec.md FR-005, plan.md [ARCHITECTURE DECISIONS]

### T031 [GREEN] Implement helper methods (get_session, is_authenticated)
- **File**: src/trading_bot/auth/robinhood_auth.py
- **Methods**:
  - get_session() -> Optional[Any]: Return _session
  - is_authenticated() -> bool: Return _authenticated
- **From**: spec.md, plan.md [SCHEMA]

---

## Phase 3.4: REFACTOR - Clean Up

### T032 [REFACTOR] Extract AuthenticationError custom exception
- **File**: src/trading_bot/auth/robinhood_auth.py
- **Class**: AuthenticationError(Exception)
- **Fields**: message (str), retry_guidance (str)
- **Purpose**: Clear error messages with actionable guidance
- **Tests**: All GREEN tests still pass (no behavior change)
- **From**: plan.md [SCHEMA]

### T033 [REFACTOR] Add type hints and docstrings
- **File**: src/trading_bot/auth/robinhood_auth.py
- **Action**: Add type hints to all methods, class-level docstring, method docstrings
- **Verify**: mypy src/trading_bot/auth/ passes with no errors
- **Pattern**: src/trading_bot/safety_checks.py (comprehensive type hints)
- **From**: spec.md NFR-006

### T034 [REFACTOR] Extract retry logic with exponential backoff
- **File**: src/trading_bot/auth/robinhood_auth.py
- **Method**: _retry_with_backoff(func, max_attempts=3, base_delay=1)
- **Use**: Wrap network calls to robin_stocks (login, refresh)
- **Pattern**: Exponential backoff (1s, 2s, 4s delays)
- **REUSE**: Consider creating src/trading_bot/utils/retry.py if pattern reused elsewhere
- **From**: spec.md NFR-003, plan.md [ERROR HANDLING]

---

## Phase 3.5: Integration & Testing

### T035 [RED] Write integration test: Bot startup with authentication
- **File**: tests/integration/test_auth_integration.py
- **Test**: test_bot_starts_with_valid_credentials()
- **Given**: Valid credentials in config, bot initialized
- **When**: bot.start() called (should trigger auth)
- **Then**: RobinhoodAuth.login() called, session authenticated, bot running
- **Mock**: robin_stocks.login() returns success
- **Pattern**: tests/integration/test_bot_safety_integration.py (bot startup tests)
- **From**: plan.md [INTEGRATION SCENARIOS]

### T036 [RED] Write integration test: Bot fails to start with invalid credentials
- **File**: tests/integration/test_auth_integration.py
- **Test**: test_bot_fails_to_start_with_invalid_credentials()
- **Given**: Invalid password in config
- **When**: bot.start() called
- **Then**: AuthenticationError raised, bot NOT running, error logged
- **Mock**: robin_stocks.login() returns 401
- **From**: spec.md Scenario 5, plan.md [INTEGRATION SCENARIOS]

### T037 [RED] Write integration test: Session restored on bot restart
- **File**: tests/integration/test_auth_integration.py
- **Test**: test_session_restored_on_bot_restart()
- **Given**: Bot authenticated and running, .robinhood.pickle exists
- **When**: Bot stopped and restarted
- **Then**: Session restored from pickle, no re-authentication, login <2s
- **Mock**: Pickle file with valid session
- **From**: spec.md Scenario 2, plan.md [INTEGRATION SCENARIOS]

### T038 [GREEN→T035] Integrate RobinhoodAuth into bot.py startup
- **File**: src/trading_bot/bot.py
- **Action**:
  1. Import RobinhoodAuth
  2. In __init__(), create self.auth = RobinhoodAuth(self.config)
  3. In start(), call self.auth.login() before setting is_running = True
  4. Add error handling: catch AuthenticationError, log, raise RuntimeError
- **REUSE**: Existing bot.start() error handling pattern
- **Pattern**: src/trading_bot/bot.py:__init__ (initialization pattern)
- **From**: plan.md [INTEGRATION SCENARIOS], spec.md FR-005

### T039 [GREEN→T036] Add authentication failure handling in bot.py
- **File**: src/trading_bot/bot.py
- **Action**: Update start() to catch AuthenticationError
- **Logic**: If auth fails, log error, do NOT start bot (§Safety_First)
- **Raise**: RuntimeError("Authentication failed - check credentials")
- **From**: spec.md Scenario 5, plan.md [SECURITY]

### T040 [GREEN→T037] Integrate logout into bot.stop()
- **File**: src/trading_bot/bot.py
- **Action**: In stop() method, call self.auth.logout() before stopping
- **Exception**: Catch logout errors gracefully (don't block shutdown)
- **Log**: "Bot shutdown complete" after logout
- **From**: spec.md Scenario 6

---

## Phase 3.6: Error Handling & Resilience

### T041 [RED] Write test: Network error during login - retry with backoff
- **File**: tests/unit/test_robinhood_auth.py
- **Test**: test_network_error_retries_with_backoff()
- **Given**: robin_stocks.login() fails with network error on first 2 attempts
- **When**: RobinhoodAuth.login() called
- **Then**: Retries 3 times with exponential backoff (1s, 2s), succeeds on 3rd attempt
- **Mock**: robin_stocks.login() side_effect=[NetworkError, NetworkError, Success]
- **From**: spec.md NFR-003, plan.md [RISKS & MITIGATIONS]

### T042 [GREEN→T041] Add retry logic to _login_with_credentials()
- **File**: src/trading_bot/auth/robinhood_auth.py
- **Action**: Wrap robin_stocks.login() with _retry_with_backoff()
- **Max attempts**: 3
- **Delays**: 1s, 2s, 4s (exponential backoff)
- **Log**: logger.warning("Login attempt {N} failed, retrying...") on failure
- **From**: spec.md NFR-003

### T043 [REFACTOR] Add comprehensive error context to AuthenticationError
- **File**: src/trading_bot/auth/robinhood_auth.py
- **Action**: Update AuthenticationError to include error_code, context dict
- **Example**: AuthenticationError("Invalid credentials", error_code="AUTH_401", context={"username": masked_username})
- **Purpose**: Better debugging, user guidance
- **From**: spec.md NFR-003, plan.md [ERROR HANDLING]

---

## Phase 3.7: Security & Compliance

### T044 [P] Run security scan with bandit
- **Command**: bandit -r src/trading_bot/auth/ -f json -o bandit-report.json
- **Verify**: No HIGH or CRITICAL issues related to credential handling
- **Action**: Fix any issues found (hardcoded passwords, insecure file permissions)
- **From**: spec.md NFR-001, plan.md [SUCCESS CRITERIA]

### T045 [P] Verify pickle file permissions in manual test
- **Action**:
  1. Run bot with real credentials (test account)
  2. Check: ls -la .robinhood.pickle shows -rw------- (600)
  3. Verify: Other users cannot read file
- **Platform**: Test on Linux/Mac (Windows permissions different)
- **From**: spec.md NFR-001, plan.md [DEPLOYMENT ACCEPTANCE]

### T046 [P] Audit logs for credential leakage
- **Action**:
  1. Run full authentication flow (login, logout, errors)
  2. Scan logs: grep -rni "password\|secret\|token" logs/
  3. Verify: No actual credential values in logs (only masked/redacted)
- **From**: spec.md NFR-001, NFR-002

---

## Phase 3.8: Documentation & Deployment Prep

### T047 [P] Update requirements.txt with pyotp
- **File**: requirements.txt
- **Action**: Verify pyotp==2.9.0 added (from T001), run pip install -r requirements.txt
- **Verify**: import pyotp works in Python REPL
- **From**: plan.md [CI/CD IMPACT]

### T048 [P] Document authentication flow in NOTES.md
- **File**: specs/authentication-module/NOTES.md
- **Section**: Add "Implementation Notes" section
- **Content**:
  - Authentication flow diagram
  - MFA setup instructions for users
  - Troubleshooting common auth errors
  - Pickle file management (when to delete)
- **From**: plan.md [INTEGRATION SCENARIOS]

### T049 [P] Create rollback procedure in error-log.md
- **File**: specs/authentication-module/error-log.md
- **Section**: Add "Rollback Procedure" section
- **Steps**:
  1. Remove RobinhoodAuth import from bot.py
  2. Delete .robinhood.pickle
  3. Restart bot (falls back to no-auth mode)
- **From**: plan.md [DEPLOYMENT ACCEPTANCE]

### T050 [P] Add smoke test for authentication
- **File**: tests/smoke/test_authentication.py
- **Test**: test_authentication_succeeds_with_env_vars()
- **Logic**: Load real .env, attempt login, verify success, logout
- **Environment**: Only runs if SMOKE_TEST=1 env var set
- **Duration**: <10s (quick smoke test)
- **From**: plan.md [CI/CD IMPACT]

---

## TEST COVERAGE REQUIREMENTS

**Coverage Targets** (per spec.md NFR-005):
- Unit tests: ≥90% line coverage (src/trading_bot/auth/)
- Integration tests: ≥80% line coverage (bot.py integration)
- All new code: 100% coverage (no untested lines)

**Measurement**:
```bash
pytest tests/unit/test_robinhood_auth.py --cov=src.trading_bot.auth --cov-report=term-missing
pytest tests/integration/test_auth_integration.py --cov=src.trading_bot.bot --cov-report=term-missing
```

**Quality Gates**:
- All tests pass before merge
- Coverage thresholds enforced: ≥90% for auth module
- mypy passes with no errors
- bandit security scan clean (no HIGH/CRITICAL issues)

**Test Speed**:
- Unit tests: <2s total (fast, no external dependencies)
- Integration tests: <5s total (mocked robin_stocks)
- Smoke test: <10s (real API call, optional)

---

## TASK DEPENDENCIES

**Critical Path** (must be sequential):
1. Setup (T001-T003) → Write tests (T004-T018) → Implement (T019-T031) → Refactor (T032-T034)
2. Integration tests (T035-T037) → Bot integration (T038-T040)
3. All implementation → Security audit (T044-T046)

**Parallel Tasks** (can work simultaneously):
- T001, T002, T003 (setup tasks)
- T004-T018 (all RED tests can be written in parallel)
- T044-T046 (security audit tasks)
- T047-T050 (documentation and deployment prep)

**Blocking Tasks**:
- T019-T031 (GREEN) are blocked by T004-T018 (RED) - TDD requirement
- T038-T040 (bot integration) blocked by T030 (RobinhoodAuth.login complete)
- T044-T046 (security) blocked by T029 (credential masking implemented)

---

## TASK SUMMARY

- **Total Tasks**: 50
- **Setup**: 3 tasks (T001-T003)
- **RED (Tests)**: 20 tasks (T004-T018, T035-T037, T041)
- **GREEN (Implementation)**: 17 tasks (T019-T031, T038-T040, T042)
- **REFACTOR**: 5 tasks (T032-T034, T043)
- **Security**: 3 tasks (T044-T046)
- **Documentation**: 4 tasks (T047-T050)

**Estimated Time**: 7-10 hours (per plan.md)

**TDD Coverage**: 20 behaviors tested before implementation (100% TDD compliance)

**REUSE**: 6 existing components (Config, TradingLogger, .env.example, pytest, robin-stocks, python-dotenv)
