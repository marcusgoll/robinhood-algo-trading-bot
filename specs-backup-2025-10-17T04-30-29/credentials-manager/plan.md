# Implementation Plan: Secure Credentials Management

## [RESEARCH DECISIONS]

### Decision: Extend ConfigValidator for MFA/Token Validation
- **Decision**: Extend existing `ConfigValidator` class (src/trading_bot/validator.py) with credential validation methods
- **Rationale**: Reuse existing validation infrastructure, maintain consistency with environment-config pattern
- **Alternatives**: Create new CredentialsValidator class (rejected: introduces duplication)
- **Source**: src/trading_bot/validator.py (lines 25-255)

### Decision: Enhance RobinhoodAuth for Device Token Persistence
- **Decision**: Extend `RobinhoodAuth.login()` to save device token to .env after successful authentication
- **Rationale**: RobinhoodAuth already handles authentication flow, natural place for token management
- **Alternatives**: Create separate TokenManager service (rejected: over-engineering for simple feature)
- **Source**: src/trading_bot/auth/robinhood_auth.py (lines 180-261)

### Decision: Reuse Existing Credential Masking Pattern
- **Decision**: Extract `_mask_credential()` from RobinhoodAuth to shared utility module
- **Rationale**: Already implemented for email masking, extend to support username/password/token/MFA patterns
- **Alternatives**: Create new masking library (rejected: existing pattern sufficient)
- **Source**: src/trading_bot/auth/robinhood_auth.py (lines 79-88)

### Decision: Leverage Error Handling Framework for Retry Logic
- **Decision**: Use existing `@with_retry` decorator for authentication retry logic
- **Rationale**: Exponential backoff already implemented, tested, and integrated with circuit breaker
- **Alternatives**: Implement custom retry logic in RobinhoodAuth (rejected: duplication)
- **Source**: src/trading_bot/error_handling/retry.py (lines 30-147)

### Decision: Store Device Token in .env File
- **Decision**: Add DEVICE_TOKEN field to .env, auto-populate after first successful auth
- **Rationale**: Consistent with existing credential storage pattern, no new dependencies
- **Alternatives**: Store in .robinhood.pickle (rejected: security risk, credentials should be in .env)
- **Source**: .env.example, src/trading_bot/config.py (lines 39, 116)

---

## [ARCHITECTURE DECISIONS]

**Stack**:
- Backend: Python 3.11+ (existing)
- Configuration: python-dotenv (existing)
- MFA: pyotp library (existing)
- Auth: robin_stocks (existing)
- Logging: structured logging with TradingLogger (existing)

**Patterns**:
- Validation Strategy: Extend ConfigValidator with credential-specific validators
- Token Persistence: Update .env file programmatically via dotenv.set_key()
- Credential Masking: Extract to src/trading_bot/utils/security.py for reuse
- Error Handling: Leverage @with_retry decorator for auth operations

**Dependencies** (new packages required):
- None - all required libraries already installed (python-dotenv, pyotp, robin_stocks)

---

## [STRUCTURE]

**Directory Layout** (follow existing patterns):

```
src/trading_bot/
├── config.py                    # Config class (existing)
├── validator.py                 # ConfigValidator (extend)
├── auth/
│   ├── __init__.py             # (existing)
│   └── robinhood_auth.py       # RobinhoodAuth (extend)
├── utils/
│   ├── __init__.py             # (existing)
│   └── security.py             # NEW: Credential masking utilities
└── error_handling/             # (existing - reuse)
    └── retry.py

tests/
├── unit/
│   ├── test_validator.py       # Extend with credential tests
│   ├── test_robinhood_auth.py  # Extend with token persistence tests
│   └── test_utils/
│       └── test_security.py    # NEW: Masking tests
└── integration/
    └── test_auth_integration.py # Extend with end-to-end auth flow
```

**Module Organization**:
- `utils/security.py`: Credential masking utilities (mask_username, mask_password, mask_mfa_secret, mask_device_token)
- `validator.py`: Extended validation methods (_validate_mfa_secret_format, _validate_device_token_format)
- `auth/robinhood_auth.py`: Enhanced token persistence (save_device_token_to_env, fallback_to_mfa_auth)

---

## [SCHEMA]

**No Database Changes** - Backend-only feature using .env file storage

**API Schemas** (Internal validation only):

```python
# ConfigValidator additions
class ConfigValidator:
    def _validate_mfa_secret_format(self) -> None:
        """Validate MFA secret is 16-char base32 string."""
        # Pattern: ^[A-Z2-7]{16}$

    def _validate_device_token_format(self) -> None:
        """Validate device token format (optional field)."""
        # Token exists -> check non-empty

# RobinhoodAuth additions
class RobinhoodAuth:
    def save_device_token_to_env(self, token: str) -> None:
        """Save device token to .env file."""
        # Use dotenv.set_key()

    def login_with_device_token(self) -> bool:
        """Attempt auth with device token, fallback to MFA on failure."""
        # Try device token -> 401 -> MFA fallback
```

**State Shape** (internal):
```python
AuthState = {
    "auth_method": "device_token" | "mfa",
    "device_token": Optional[str],
    "mfa_required": bool,
    "authenticated": bool
}
```

---

## [PERFORMANCE TARGETS]

**From spec.md NFRs**:
- NFR-002: Credential validation <500ms
- NFR-003: Exponential backoff (1s, 2s, 4s) for auth retries

**Lighthouse Targets**: N/A (backend-only feature)

**Performance Benchmarks**:
- MFA format validation: <10ms (regex check)
- Device token validation: <5ms (presence check)
- .env file update: <50ms (dotenv.set_key)
- Full auth flow: <5s (including API roundtrip)

---

## [SECURITY]

**Authentication Strategy**:
- Extend existing RobinhoodAuth service
- No changes to authentication mechanism (robin_stocks)

**Authorization Model**:
- N/A - Local credential storage only

**Input Validation**:
- MFA secret: Base32 format (^[A-Z2-7]{16}$)
- Device token: Non-empty string if present
- Username: Email format (existing validation)
- Password: Non-empty string (existing validation)

**Data Protection**:
- PII handling: Mask all credentials in logs (FR-007)
  - Username: first 3 chars + *** (e.g., "joh***")
  - Password: ***** (never log)
  - MFA secret: **** (never log)
  - Device token: first 8 chars + *** (e.g., "1a2b3c4d***")
- Encryption: .env file with 600 permissions (read/write owner only)
- Audit trail: Log all auth events with masked credentials

**Rate Limiting**:
- Inherit from error-handling-framework (@with_retry)
- No additional rate limiting needed

**CORS**: N/A - Backend-only feature

---

## [EXISTING INFRASTRUCTURE - REUSE] (7 components)

**Services/Modules**:
- `src/trading_bot/config.py`: Config.from_env_and_json() - load credentials from .env
- `src/trading_bot/validator.py`: ConfigValidator._validate_credentials() - extend with format checks
- `src/trading_bot/auth/robinhood_auth.py`: RobinhoodAuth.login() - extend with device token logic
- `src/trading_bot/error_handling/retry.py`: @with_retry decorator - apply to auth operations

**Utilities**:
- `src/trading_bot/auth/robinhood_auth.py`: _mask_credential() - extract to utils/security.py, extend patterns
- `src/trading_bot/logger.py`: TradingLogger - structured logging for auth events
- `python-dotenv`: dotenv.set_key() - update .env file programmatically

---

## [NEW INFRASTRUCTURE - CREATE] (3 components)

**Backend**:
- `src/trading_bot/utils/security.py`: Credential masking utilities
  - `mask_username(username: str) -> str`: first 3 chars + ***
  - `mask_password(password: str) -> str`: *****
  - `mask_mfa_secret(secret: str) -> str`: ****
  - `mask_device_token(token: str) -> str`: first 8 chars + ***

**Validation Extensions**:
- `ConfigValidator._validate_mfa_secret_format()`: Validate 16-char base32
- `ConfigValidator._validate_device_token_format()`: Validate non-empty if present

**Auth Extensions**:
- `RobinhoodAuth.save_device_token_to_env(token: str)`: Save token to .env
- `RobinhoodAuth.login_with_device_token()`: Auth with token, fallback to MFA

---

## [CI/CD IMPACT]

**From spec.md deployment considerations:**
- Platform: Local-only (no deployment platform)
- Env vars: Add DEVICE_TOKEN to .env.example
- Breaking changes: No - DEVICE_TOKEN is optional
- Migration: No database changes

**Build Commands**:
- No changes - Python project with existing test suite

**Environment Variables** (update .env.example):
- New optional: `DEVICE_TOKEN` (auto-populated after first auth)
- Changed: None
- Staging values: (empty initially, auto-populated)
- Production values: (empty initially, auto-populated)

**Schema Update Required**:
```bash
# .env.example additions
DEVICE_TOKEN=  # Optional: Device token for faster auth (auto-populated)

# Add comment explaining auto-population:
# Note: DEVICE_TOKEN is automatically saved after first successful authentication.
# Leave empty initially - the bot will populate this field on first run.
```

**Database Migrations**: No

**Smoke Tests** (for test suite):
- Unit tests: Credential masking, MFA format validation, device token validation
- Integration tests: End-to-end auth flow with device token persistence
- Manual test: First-time auth -> verify DEVICE_TOKEN saved to .env

**Platform Coupling**: None - local-only feature

---

## [DEPLOYMENT ACCEPTANCE]

**Production Invariants**:
- .env file must exist before bot startup (FR-008)
- ROBINHOOD_USERNAME and ROBINHOOD_PASSWORD required (existing)
- DEVICE_TOKEN optional, auto-populated after first successful auth (FR-003)
- MFA secret validated as 16-char base32 if provided (FR-001)

**Staging Smoke Tests** (Manual validation):
```gherkin
Given bot is run for first time (no DEVICE_TOKEN)
When authentication succeeds with MFA
Then DEVICE_TOKEN is saved to .env file
  And subsequent runs use device token (skip MFA)
  And all credentials are masked in logs
  And validation completes in <500ms
```

**Rollback Plan**:
- Standard rollback: Revert commits, remove DEVICE_TOKEN from .env
- No special considerations: Backward compatible (DEVICE_TOKEN optional)
- Data migration: None required

**Artifact Strategy**: N/A - Local-only feature, no deployment artifacts

---

## [INTEGRATION SCENARIOS]

**From quickstart perspective:**

### Scenario 1: First-Time Setup
```bash
# Copy .env.example to .env
cp .env.example .env

# Edit .env - add credentials
# ROBINHOOD_USERNAME=user@example.com
# ROBINHOOD_PASSWORD=secure_password
# ROBINHOOD_MFA_SECRET=ABCDEFGHIJKLMNOP  # 16-char base32
# DEVICE_TOKEN=  # Leave empty

# Run bot - first authentication
python -m trading_bot

# Expected behavior:
# 1. ConfigValidator checks MFA secret format (16-char base32)
# 2. RobinhoodAuth.login() authenticates with username/password/MFA
# 3. On success, device token saved to .env (DEVICE_TOKEN=...)
# 4. Bot starts normally
```

### Scenario 2: Validation Checks
```bash
# Run validation script
python validate_startup.py

# Expected checks:
# ✓ .env file exists
# ✓ ROBINHOOD_USERNAME present
# ✓ ROBINHOOD_PASSWORD present
# ✓ ROBINHOOD_MFA_SECRET format valid (16-char base32)
# ✓ DEVICE_TOKEN present (after first run) or empty (before first run)
# ✓ All credentials masked in logs
```

### Scenario 3: Subsequent Runs (Device Token Reuse)
```bash
# Run bot after first successful auth
python -m trading_bot

# Expected behavior:
# 1. ConfigValidator checks all credentials
# 2. RobinhoodAuth.login_with_device_token() tries device token
# 3. If token valid -> auth succeeds (skip MFA)
# 4. If token invalid (401) -> fallback to MFA, update token
# 5. Bot starts normally
```

### Scenario 4: MFA Fallback
```bash
# Simulate invalid device token
# (Edit .env: DEVICE_TOKEN=invalid_token)
python -m trading_bot

# Expected behavior:
# 1. RobinhoodAuth.login_with_device_token() tries device token
# 2. robin_stocks returns 401 error
# 3. Fallback to MFA authentication (FR-005)
# 4. On success, update DEVICE_TOKEN in .env (FR-006)
# 5. Bot starts normally
```

### Scenario 5: Credential Masking Verification
```bash
# Run bot and check logs
python -m trading_bot
tail -f logs/trading_bot.log

# Expected log entries (masked):
# "Authenticating user joh***@example.com"
# "Session saved to cache for joh***@example.com"
# "Authentication successful for joh***@example.com"
# "Device token saved: 1a2b3c4d***"
```

---

## [TESTING STRATEGY]

**Unit Tests** (test coverage >90%):
- `test_security.py`: Credential masking functions
  - `test_mask_username()`: Verify first 3 chars + ***
  - `test_mask_password()`: Verify *****
  - `test_mask_mfa_secret()`: Verify ****
  - `test_mask_device_token()`: Verify first 8 chars + ***

- `test_validator.py` (extend):
  - `test_validate_mfa_secret_format_valid()`: 16-char base32 passes
  - `test_validate_mfa_secret_format_invalid_length()`: Reject non-16-char
  - `test_validate_mfa_secret_format_invalid_chars()`: Reject non-base32
  - `test_validate_device_token_optional()`: Accept empty token

- `test_robinhood_auth.py` (extend):
  - `test_save_device_token_to_env()`: Verify dotenv.set_key called
  - `test_login_with_device_token_success()`: Token auth succeeds
  - `test_login_with_device_token_fallback()`: 401 triggers MFA fallback

**Integration Tests**:
- `test_auth_integration.py` (extend):
  - `test_first_time_auth_saves_token()`: End-to-end first auth
  - `test_subsequent_auth_uses_token()`: Device token reuse
  - `test_auth_fallback_updates_token()`: MFA fallback flow
  - `test_credentials_masked_in_logs()`: Log masking verification

**Manual Tests** (pre-production):
- First-time setup with real Robinhood credentials
- Device token persistence verification
- MFA fallback simulation (invalid token)
- Log file inspection for masked credentials

---

## [QUALITY GATES]

**Must Pass Before Implementation**:
- All existing tests pass (no regressions)
- New unit tests achieve >90% coverage
- Integration tests cover all 5 acceptance scenarios
- Manual smoke test with real credentials succeeds

**Must Pass Before Production**:
- Code review approved (security focus)
- No plaintext credentials in logs (audit all log files)
- .env.example updated with DEVICE_TOKEN field
- Documentation updated (README with setup instructions)
