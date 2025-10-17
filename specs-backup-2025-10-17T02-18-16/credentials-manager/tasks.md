# Tasks: Secure Credentials Management

## [CODEBASE REUSE ANALYSIS]
Scanned: src/trading_bot/**/*.py, tests/**/*.py

## [EXISTING - REUSE]
- ConfigValidator (src/trading_bot/validator.py) - Extend with credential format validation
- RobinhoodAuth (src/trading_bot/auth/robinhood_auth.py) - Extend with device token persistence
- @with_retry decorator (src/trading_bot/error_handling/retry.py) - Apply to auth operations
- TradingLogger (src/trading_bot/logger.py) - Structured logging for auth events
- Config.from_env_and_json() (src/trading_bot/config.py) - Load credentials from .env
- dotenv.set_key() (python-dotenv) - Update .env file programmatically
- _mask_credential() (src/trading_bot/auth/robinhood_auth.py) - Extract to utils, extend patterns

## [NEW - CREATE]
- utils/security.py: Credential masking utilities (4 functions)
- ConfigValidator extensions: 2 validation methods
- RobinhoodAuth extensions: 2 token management methods

---

## Phase 3.1: Setup

T001 [P] Create utils/security.py module with credential masking utilities
- **File**: src/trading_bot/utils/security.py
- **Functions**: mask_username, mask_password, mask_mfa_secret, mask_device_token
- **Pattern**: Extract from src/trading_bot/auth/robinhood_auth.py (_mask_credential, lines 79-88)
- **From**: plan.md [NEW INFRASTRUCTURE - CREATE] section

T002 [P] Update .env.example with DEVICE_TOKEN field
- **File**: .env.example
- **Add**: DEVICE_TOKEN=  # Optional: Auto-populated after first successful authentication
- **Add**: Comment explaining auto-population behavior
- **Pattern**: Existing .env.example credential format
- **From**: plan.md [CI/CD IMPACT] section

T003 [P] Add DEVICE_TOKEN field to Config class
- **File**: src/trading_bot/config.py
- **Add**: device_token: Optional[str] field to Config dataclass
- **Add**: Load from environment variable DEVICE_TOKEN
- **Pattern**: Existing credential fields (robinhood_username, robinhood_password)
- **From**: plan.md [SCHEMA] section

---

## Phase 3.2: RED - Write Failing Tests

T004 [RED] Write test: mask_username returns first 3 chars plus asterisks
- **File**: tests/unit/test_utils/test_security.py (NEW)
- **Test**: test_mask_username_standard_format()
- **Assert**: "john@example.com" -> "joh***@example.com"
- **Pattern**: tests/unit/test_validator.py test structure
- **From**: plan.md [TESTING STRATEGY] section

T005 [RED] Write test: mask_password returns all asterisks
- **File**: tests/unit/test_utils/test_security.py
- **Test**: test_mask_password()
- **Assert**: Any password -> "*****"
- **Pattern**: tests/unit/test_validator.py test structure
- **From**: plan.md [TESTING STRATEGY] section

T006 [RED] Write test: mask_mfa_secret returns asterisks
- **File**: tests/unit/test_utils/test_security.py
- **Test**: test_mask_mfa_secret()
- **Assert**: "ABCDEFGHIJKLMNOP" -> "****"
- **Pattern**: tests/unit/test_validator.py test structure
- **From**: plan.md [TESTING STRATEGY] section

T007 [RED] Write test: mask_device_token returns first 8 chars plus asterisks
- **File**: tests/unit/test_utils/test_security.py
- **Test**: test_mask_device_token()
- **Assert**: "1a2b3c4d5e6f7g8h" -> "1a2b3c4d***"
- **Pattern**: tests/unit/test_validator.py test structure
- **From**: plan.md [TESTING STRATEGY] section

T008 [RED] Write test: ConfigValidator validates MFA secret format (16-char base32)
- **File**: tests/unit/test_validator.py
- **Test**: test_validate_mfa_secret_format_valid()
- **Given**: MFA_SECRET="ABCDEFGHIJKLMNOP" (16-char base32)
- **When**: ConfigValidator.validate()
- **Then**: Validation passes (no exception)
- **Pattern**: Existing validation tests in test_validator.py
- **From**: plan.md [TESTING STRATEGY] section

T009 [RED] Write test: ConfigValidator rejects invalid MFA secret length
- **File**: tests/unit/test_validator.py
- **Test**: test_validate_mfa_secret_format_invalid_length()
- **Given**: MFA_SECRET="ABCD" (too short)
- **When**: ConfigValidator.validate()
- **Then**: Raises ValidationError with message "MFA secret must be 16 characters"
- **Pattern**: Existing validation error tests in test_validator.py
- **From**: plan.md [TESTING STRATEGY] section

T010 [RED] Write test: ConfigValidator rejects invalid MFA secret characters
- **File**: tests/unit/test_validator.py
- **Test**: test_validate_mfa_secret_format_invalid_chars()
- **Given**: MFA_SECRET="ABCDEFGH12345678" (contains invalid base32 chars 8,9)
- **When**: ConfigValidator.validate()
- **Then**: Raises ValidationError with message "MFA secret must contain only base32 characters"
- **Pattern**: Existing validation error tests in test_validator.py
- **From**: plan.md [TESTING STRATEGY] section

T011 [RED] Write test: ConfigValidator accepts empty device token (optional field)
- **File**: tests/unit/test_validator.py
- **Test**: test_validate_device_token_optional()
- **Given**: DEVICE_TOKEN="" (empty)
- **When**: ConfigValidator.validate()
- **Then**: Validation passes (device token is optional)
- **Pattern**: Existing optional field validation tests in test_validator.py
- **From**: plan.md [TESTING STRATEGY] section

T012 [RED] Write test: RobinhoodAuth saves device token to .env file
- **File**: tests/unit/test_robinhood_auth.py
- **Test**: test_save_device_token_to_env()
- **Given**: Device token "test_token_123"
- **When**: RobinhoodAuth.save_device_token_to_env("test_token_123")
- **Then**: dotenv.set_key called with ("DEVICE_TOKEN", "test_token_123")
- **Mock**: dotenv.set_key
- **Pattern**: Existing RobinhoodAuth tests in test_robinhood_auth.py
- **From**: plan.md [TESTING STRATEGY] section

T013 [RED] Write test: RobinhoodAuth authenticates with device token successfully
- **File**: tests/unit/test_robinhood_auth.py
- **Test**: test_login_with_device_token_success()
- **Given**: Valid device token in config
- **When**: RobinhoodAuth.login_with_device_token()
- **Then**: robin_stocks.login called with device_token, returns True
- **Mock**: robin_stocks.robinhood.authentication.login
- **Pattern**: Existing RobinhoodAuth.login tests in test_robinhood_auth.py
- **From**: plan.md [TESTING STRATEGY] section

T014 [RED] Write test: RobinhoodAuth falls back to MFA on device token failure
- **File**: tests/unit/test_robinhood_auth.py
- **Test**: test_login_with_device_token_fallback()
- **Given**: Invalid device token (401 error from robin_stocks)
- **When**: RobinhoodAuth.login_with_device_token()
- **Then**: Falls back to MFA authentication, saves new device token
- **Mock**: robin_stocks.login (raises 401), then succeeds with MFA
- **Pattern**: Existing error handling tests in test_robinhood_auth.py
- **From**: plan.md [TESTING STRATEGY] section

---

## Phase 3.3: GREEN - Minimal Implementation

T015 [GREEN->T004,T005,T006,T007] Implement credential masking functions
- **File**: src/trading_bot/utils/security.py
- **Functions**:
  - mask_username(username: str) -> str: Return first 3 chars + "***" + domain
  - mask_password(password: str) -> str: Return "*****"
  - mask_mfa_secret(secret: str) -> str: Return "****"
  - mask_device_token(token: str) -> str: Return first 8 chars + "***"
- **REUSE**: Pattern from src/trading_bot/auth/robinhood_auth.py (_mask_credential)
- **From**: plan.md [NEW INFRASTRUCTURE - CREATE] section

T016 [GREEN->T008,T009,T010] Implement ConfigValidator MFA secret format validation
- **File**: src/trading_bot/validator.py
- **Method**: _validate_mfa_secret_format(self) -> None
- **Logic**: Check pattern ^[A-Z2-7]{16}$ (16-char base32)
- **Error**: Raise ValidationError if invalid
- **Call from**: _validate_credentials() method
- **REUSE**: Existing validation pattern from ConfigValidator class
- **From**: plan.md [NEW INFRASTRUCTURE - CREATE] section

T017 [GREEN->T011] Implement ConfigValidator device token validation
- **File**: src/trading_bot/validator.py
- **Method**: _validate_device_token_format(self) -> None
- **Logic**: If device_token present, check non-empty; if empty, skip (optional)
- **Call from**: _validate_credentials() method
- **REUSE**: Existing optional field validation pattern
- **From**: plan.md [NEW INFRASTRUCTURE - CREATE] section

T018 [GREEN->T012] Implement RobinhoodAuth save_device_token_to_env method
- **File**: src/trading_bot/auth/robinhood_auth.py
- **Method**: save_device_token_to_env(self, token: str) -> None
- **Logic**: Call dotenv.set_key(".env", "DEVICE_TOKEN", token)
- **Logging**: Log masked token using mask_device_token()
- **REUSE**: dotenv.set_key() from python-dotenv library
- **From**: plan.md [NEW INFRASTRUCTURE - CREATE] section

T019 [GREEN->T013,T014] Implement RobinhoodAuth login_with_device_token method
- **File**: src/trading_bot/auth/robinhood_auth.py
- **Method**: login_with_device_token(self) -> bool
- **Logic**:
  1. Try robin_stocks.login with device_token
  2. If success (200): Return True
  3. If failure (401): Log "Device token invalid, falling back to MFA"
  4. Call existing login() method with MFA
  5. On MFA success: Call save_device_token_to_env() with new token
  6. Return authentication status
- **REUSE**: Existing login() method, @with_retry decorator
- **From**: plan.md [NEW INFRASTRUCTURE - CREATE] section

T020 [GREEN->T019] Update RobinhoodAuth.login to use device token first
- **File**: src/trading_bot/auth/robinhood_auth.py
- **Method**: login(self) -> bool (modify existing)
- **Logic**:
  1. If device_token exists: Call login_with_device_token()
  2. If no device_token OR device_token fails: Use MFA authentication
  3. On MFA success: Save device token to .env
- **REUSE**: Existing login() method flow
- **From**: plan.md [ARCHITECTURE DECISIONS] section

---

## Phase 3.4: REFACTOR - Clean Up

T021 [REFACTOR] Update RobinhoodAuth to use utils/security masking functions
- **File**: src/trading_bot/auth/robinhood_auth.py
- **Change**: Replace inline _mask_credential() with utils.security functions
- **Import**: from trading_bot.utils.security import mask_username, mask_device_token
- **Update**: All log statements to use new masking functions
- **Remove**: Old _mask_credential() method (lines 79-88)
- **Test**: All existing tests still pass (behavior unchanged)
- **From**: plan.md [RESEARCH DECISIONS] section

T022 [REFACTOR] Extract validation logic to separate methods for clarity
- **File**: src/trading_bot/validator.py
- **Change**: Ensure _validate_mfa_secret_format and _validate_device_token_format are separate methods
- **Update**: _validate_credentials() to call both new methods
- **Test**: All validation tests still pass
- **From**: plan.md [ARCHITECTURE DECISIONS] section

T023 [REFACTOR] Add type hints to all new functions and methods
- **Files**: src/trading_bot/utils/security.py, src/trading_bot/validator.py, src/trading_bot/auth/robinhood_auth.py
- **Change**: Add complete type hints (args, return types)
- **Verify**: mypy passes with no errors
- **Pattern**: Existing type hint style in codebase
- **From**: Python 3.11+ best practices

---

## Phase 3.5: Integration & Testing

T024 [RED] Write integration test: First-time auth saves device token to .env
- **File**: tests/integration/test_auth_integration.py
- **Test**: test_first_time_auth_saves_token()
- **Given**: No DEVICE_TOKEN in .env
- **When**: RobinhoodAuth.login() succeeds with MFA
- **Then**: DEVICE_TOKEN field added to .env file
- **Mock**: robin_stocks API (return valid token)
- **Pattern**: Existing integration tests in test_auth_integration.py
- **From**: plan.md [INTEGRATION SCENARIOS] Scenario 1

T025 [RED] Write integration test: Subsequent auth uses device token (skip MFA)
- **File**: tests/integration/test_auth_integration.py
- **Test**: test_subsequent_auth_uses_token()
- **Given**: Valid DEVICE_TOKEN in .env
- **When**: RobinhoodAuth.login() called
- **Then**: Authenticates with device token (MFA not called)
- **Mock**: robin_stocks.login (device_token auth succeeds)
- **Pattern**: Existing integration tests in test_auth_integration.py
- **From**: plan.md [INTEGRATION SCENARIOS] Scenario 3

T026 [RED] Write integration test: Invalid device token triggers MFA fallback
- **File**: tests/integration/test_auth_integration.py
- **Test**: test_auth_fallback_updates_token()
- **Given**: Invalid DEVICE_TOKEN in .env (expired/revoked)
- **When**: RobinhoodAuth.login() called
- **Then**: Device token fails (401), falls back to MFA, updates token in .env
- **Mock**: robin_stocks.login (device_token fails, MFA succeeds)
- **Pattern**: Existing integration tests in test_auth_integration.py
- **From**: plan.md [INTEGRATION SCENARIOS] Scenario 4

T027 [RED] Write integration test: All credentials masked in logs
- **File**: tests/integration/test_auth_integration.py
- **Test**: test_credentials_masked_in_logs()
- **Given**: Full auth flow with username, password, MFA, device token
- **When**: Authentication completes
- **Then**: Check log output contains masked values only (no plaintext credentials)
- **Assert**: "joh***" in logs, "ABCDEFGHIJKLMNOP" NOT in logs, "*****" for password
- **Pattern**: Log inspection pattern from existing tests
- **From**: plan.md [INTEGRATION SCENARIOS] Scenario 5

T028 [GREEN->T024,T025,T026,T027] Fix integration test failures
- **Action**: Run integration tests, fix any implementation issues
- **Verify**: All 4 integration tests pass
- **Debug**: Check .env file updates, log output, API call mocking
- **From**: TDD cycle (make tests pass)

---

## Phase 3.6: Error Handling & Resilience

T029 [RED] Write test: Validation fails fast on invalid MFA format (<500ms)
- **File**: tests/unit/test_validator.py
- **Test**: test_validation_performance()
- **Given**: Invalid MFA secret format
- **When**: ConfigValidator.validate()
- **Then**: Raises ValidationError in <500ms (NFR-002)
- **Measure**: Use time.perf_counter() to measure execution time
- **From**: plan.md [PERFORMANCE TARGETS] NFR-002

T030 [GREEN->T029] Optimize validation to meet performance target
- **File**: src/trading_bot/validator.py
- **Change**: Ensure regex validation completes in <10ms
- **Verify**: Performance test passes
- **From**: plan.md [PERFORMANCE TARGETS]

T031 [P] Apply @with_retry decorator to authentication methods
- **File**: src/trading_bot/auth/robinhood_auth.py
- **Change**: Add @with_retry decorator to login() and login_with_device_token()
- **Config**: Exponential backoff (1s, 2s, 4s) per NFR-003
- **REUSE**: Existing @with_retry from src/trading_bot/error_handling/retry.py
- **From**: plan.md [ARCHITECTURE DECISIONS] section

---

## Phase 3.7: Documentation & Polish

T032 [P] Update README with credential setup instructions
- **File**: README.md
- **Section**: Add "Credentials Setup" section
- **Content**:
  - Copy .env.example to .env
  - Add ROBINHOOD_USERNAME, ROBINHOOD_PASSWORD, ROBINHOOD_MFA_SECRET
  - Explain DEVICE_TOKEN auto-population behavior
  - Link to Robinhood MFA setup guide
- **Pattern**: Existing README sections
- **From**: plan.md [DEPLOYMENT ACCEPTANCE] section

T033 [P] Add docstrings to all new functions and methods
- **Files**: src/trading_bot/utils/security.py, validator.py additions, robinhood_auth.py additions
- **Format**: Google-style docstrings (existing pattern in codebase)
- **Include**: Args, Returns, Raises, Examples
- **Pattern**: Existing docstrings in src/trading_bot/auth/robinhood_auth.py
- **From**: Python docstring best practices

T034 [P] Run full test suite and verify coverage >90%
- **Command**: pytest --cov=src/trading_bot --cov-report=term-missing
- **Target**: >90% line coverage for new code
- **Verify**: All tests pass (unit + integration)
- **From**: plan.md [TESTING STRATEGY] section

---

## Summary

**Total Tasks**: 34
- Setup: 3 tasks (T001-T003)
- RED tests: 14 tasks (T004-T014, T024-T027, T029)
- GREEN implementation: 7 tasks (T015-T020, T028, T030)
- REFACTOR: 3 tasks (T021-T023)
- Error handling: 1 task (T031)
- Documentation: 3 tasks (T032-T034)

**TDD Coverage**: 21 behaviors (RED -> GREEN -> REFACTOR cycle)

**Reuse Leveraged**: 7 existing components (ConfigValidator, RobinhoodAuth, @with_retry, TradingLogger, dotenv, Config)

**Dependencies**:
- All RED tasks independent (can run in parallel)
- GREEN tasks depend on corresponding RED tasks
- Integration tests (T024-T027) depend on all unit test implementations
- Documentation (T032-T034) should be last

**Estimated Duration**: 6-8 hours (including testing and documentation)
