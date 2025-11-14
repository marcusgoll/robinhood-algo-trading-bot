# Specification: Robinhood Authentication Module

**Feature**: authentication-module
**Type**: Backend / Authentication
**Area**: api
**Blocked by**: None
**Constitution**: v1.0.0

---

## Overview

Implements secure Robinhood authentication with MFA support, session management, and automatic token refresh. Enforces Constitution §Security and §Audit_Everything requirements by managing credentials via environment variables and logging all authentication events.

**Problem**: Bot cannot trade without authenticated Robinhood session. Current system lacks:
- Automated login with MFA support
- Session persistence across bot restarts
- Token refresh on expiry
- Graceful error handling for auth failures
- Credential validation before startup

**Solution**: Authentication service that handles login flow, MFA challenges using pyotp, session storage via pickle files, automatic token refresh, and comprehensive error recovery.

---

## User Scenarios

### Scenario 1: First-Time Login with MFA
**Given** valid credentials in .env (username, password, MFA secret)
**When** bot starts for the first time
**Then** authentication service:
- Logs in with username/password
- Handles MFA challenge using pyotp.TOTP(secret).now()
- Stores session in .robinhood.pickle
- Returns authenticated session
**And** logs "Authentication successful" to audit log

### Scenario 2: Session Reuse from Pickle
**Given** valid .robinhood.pickle exists from previous session
**And** token has not expired
**When** bot starts
**Then** authentication service:
- Loads session from pickle file
- Validates token is still valid
- Returns authenticated session without new login
**And** logs "Session restored from cache"

### Scenario 3: Expired Token Auto-Refresh
**Given** bot is running with active session
**And** access token expires
**When** API call returns 401 Unauthorized
**Then** authentication service:
- Automatically refreshes token using refresh token
- Updates pickle file with new session
- Retries failed API call
**And** logs "Token auto-refreshed"

### Scenario 4: MFA Challenge Failure
**Given** MFA secret is incorrect or expired
**When** bot attempts login
**Then** authentication service:
- Attempts MFA with pyotp
- Receives MFA failure from Robinhood
- Logs error "MFA challenge failed"
- Raises AuthenticationError with retry guidance
**And** bot fails to start (§Safety_First)

### Scenario 5: Invalid Credentials
**Given** username or password is incorrect
**When** bot attempts login
**Then** authentication service:
- Receives 401 Unauthorized
- Logs error "Invalid credentials"
- Raises AuthenticationError
**And** bot fails to start (§Safety_First)

### Scenario 6: Graceful Logout
**Given** authenticated session exists
**When** bot shutdown is initiated
**Then** authentication service:
- Calls robin_stocks.logout()
- Deletes .robinhood.pickle
- Logs "Logout successful"
**And** session is invalidated

### Scenario 7: Device Token Reuse (Optional)
**Given** ROBINHOOD_DEVICE_TOKEN set in .env
**When** bot logs in
**Then** authentication service:
- Passes device_token to robin_stocks
- Skips MFA challenge (faster auth)
- Stores session normally
**And** logs "Login via device token"

---

## Requirements

### Functional Requirements

**FR-001: Environment-Based Credentials (§Security)**
- MUST load credentials from environment variables only
- MUST support: ROBINHOOD_USERNAME, ROBINHOOD_PASSWORD
- MUST support optional: ROBINHOOD_MFA_SECRET, ROBINHOOD_DEVICE_TOKEN
- MUST NEVER store credentials in code or logs
- MUST validate all required credentials present before login attempt

**FR-002: MFA Support with pyotp**
- MUST handle MFA challenge using pyotp.TOTP(secret).now()
- MUST support time-based one-time password (TOTP)
- MUST handle MFA failure gracefully with error message
- SHOULD support device token for bypassing MFA (if available)

**FR-003: Session Persistence**
- MUST store authenticated session in .robinhood.pickle
- MUST restore session from pickle on bot restart
- MUST validate restored session before use
- MUST handle corrupt pickle files (delete and re-authenticate)

**FR-004: Automatic Token Refresh**
- MUST detect expired access tokens (401 responses)
- MUST automatically refresh using refresh token
- MUST update pickle file after refresh
- MUST retry original API call after refresh
- MUST fail gracefully if refresh token also expired

**FR-005: Login Flow Management**
- MUST attempt pickle-based login first (if file exists)
- MUST fall back to username/password login if pickle invalid
- MUST handle MFA challenge during login
- MUST return authenticated session object
- MUST raise AuthenticationError on failure

**FR-006: Logout and Cleanup**
- MUST provide logout() method
- MUST call robin_stocks.logout()
- MUST delete .robinhood.pickle on logout
- MUST handle logout errors gracefully

**FR-007: Credential Validation (§Pre_Deploy)**
- MUST validate credentials before attempting login
- MUST check username format (email)
- MUST check password not empty
- MUST check MFA secret format (if provided)
- MUST raise ValueError for invalid credentials

### Non-Functional Requirements

**NFR-001: Security (§Security)**
- MUST NOT log credentials (username, password, MFA secret)
- MUST store pickle file with restricted permissions (600)
- MUST handle credentials in memory securely
- MUST clear credentials from memory after use
- MUST validate all inputs to prevent injection

**NFR-002: Auditability (§Audit_Everything)**
- MUST log all authentication events (login, logout, refresh)
- MUST log authentication failures with reason
- MUST include timestamps (UTC) in all logs
- MUST NOT log sensitive data (credentials, tokens)

**NFR-003: Error Handling (§Error_Handling)**
- MUST handle network failures gracefully
- MUST handle Robinhood API errors with retry logic
- MUST provide clear error messages for troubleshooting
- MUST fail safely (bot doesn't start if auth fails)

**NFR-004: Performance**
- Login with pickle SHOULD complete in <2 seconds
- Login with username/password SHOULD complete in <10 seconds
- Token refresh SHOULD complete in <5 seconds
- MUST NOT block trading operations during refresh

**NFR-005: Test Coverage**
- MUST achieve ≥90% test coverage (§Code_Quality)
- MUST test all authentication flows
- MUST test error scenarios (invalid creds, MFA failure, network errors)
- MUST test session persistence and restoration

**NFR-006: Type Safety**
- MUST use type hints on all functions
- MUST pass `mypy` strict mode

---

## Technical Design

### Architecture

```
RobinhoodAuth Class
├── __init__(config)
├── login() → bool
├── logout() → None
├── get_session() → Optional[Session]
├── refresh_token() → bool
├── is_authenticated() → bool
├── _login_with_pickle() → Optional[Session]
├── _login_with_credentials() → Session
├── _handle_mfa_challenge() → str
├── _save_session(session) → None
└── _validate_credentials() → None
```

### Data Models

```python
@dataclass
class AuthConfig:
    """Authentication configuration from environment variables."""
    username: str
    password: str
    mfa_secret: Optional[str] = None
    device_token: Optional[str] = None
    pickle_path: str = ".robinhood.pickle"

@dataclass
class AuthResult:
    """Result of authentication attempt."""
    success: bool
    session: Optional[Any] = None  # robin_stocks session object
    error_message: Optional[str] = None
```

### Dependencies

**External Libraries**:
- `robin-stocks==3.0.5` (already in requirements.txt)
- `pyotp` (NEW - must add to requirements.txt)
- `python-dotenv==1.0.0` (already in requirements.txt)

**Internal Modules**:
- `config.py`: For loading environment variables
- `logger.py`: For audit logging

### Authentication Flow

```
1. Bot Startup
   ↓
2. Load credentials from .env
   ↓
3. Validate credentials format
   ↓
4. Check if .robinhood.pickle exists
   ↓
   YES → Load pickle → Validate session → Success or continue
   ↓
   NO or INVALID
   ↓
5. robin_stocks.login(username, password)
   ↓
6. If MFA challenge → pyotp.TOTP(mfa_secret).now() → Submit code
   ↓
7. If device_token → Pass to robin_stocks → Skip MFA
   ↓
8. Save session to .robinhood.pickle
   ↓
9. Return authenticated session
```

### Session Management

**Pickle File Structure** (`.robinhood.pickle`):
- Stores robin_stocks session object (opaque)
- Contains access token, refresh token, expiry
- Updated automatically on token refresh
- Permissions: 600 (owner read/write only)

**Token Refresh Logic**:
```python
def refresh_token() -> bool:
    """Refresh expired access token."""
    try:
        # robin_stocks handles refresh internally
        # Just need to update pickle after successful API call
        session = rh.account.build_user_profile()
        self._save_session(session)
        return True
    except Exception as e:
        logger.error(f"Token refresh failed: {e}")
        return False
```

---

## Implementation Plan

### Phase 1: Core Authentication (Intra: Yes - single session)
1. Create `src/trading_bot/auth/robinhood_auth.py`
2. Implement AuthConfig dataclass
3. Implement credential loading from environment
4. Implement credential validation

### Phase 2: Login Flow
1. Implement `login()` method with pickle fallback
2. Implement `_login_with_pickle()`
3. Implement `_login_with_credentials()`
4. Implement `_handle_mfa_challenge()` with pyotp

### Phase 3: Session Management
1. Implement `_save_session()` with pickle
2. Implement `get_session()` for session access
3. Implement `is_authenticated()` status check
4. Implement `refresh_token()` for auto-refresh

### Phase 4: Logout & Cleanup
1. Implement `logout()` method
2. Implement pickle deletion on logout
3. Handle cleanup on bot shutdown

### Phase 5: Integration & Testing
1. Write comprehensive unit tests (target: 90% coverage)
2. Write integration tests with mocked robin_stocks
3. Test all error scenarios
4. Integrate with bot.py startup sequence

---

## Testing Strategy

### Unit Tests (test_robinhood_auth.py)

**Credential Loading Tests**:
- ✅ Valid credentials → load successfully
- ✅ Missing username → raise ValueError
- ✅ Missing password → raise ValueError
- ✅ Invalid email format → raise ValueError
- ✅ Optional MFA secret → load successfully
- ✅ Optional device token → load successfully

**Login Tests**:
- ✅ Valid pickle exists → restore session
- ✅ Invalid pickle → delete and re-authenticate
- ✅ No pickle → username/password login
- ✅ MFA challenge → handle with pyotp
- ✅ Device token provided → skip MFA
- ✅ Invalid credentials → raise AuthenticationError

**Session Persistence Tests**:
- ✅ Save session to pickle → file created with 600 permissions
- ✅ Load session from pickle → session restored
- ✅ Corrupt pickle → delete and return None
- ✅ Pickle permissions → verify 600

**Token Refresh Tests**:
- ✅ Expired token → auto-refresh
- ✅ Refresh successful → update pickle
- ✅ Refresh failed → raise error
- ✅ Multiple refresh attempts → backoff logic

**Logout Tests**:
- ✅ Logout → robin_stocks.logout() called
- ✅ Logout → pickle file deleted
- ✅ Logout error → handle gracefully

**Error Handling Tests**:
- ✅ Network error during login → retry
- ✅ MFA failure → clear error message
- ✅ API error → log and raise
- ✅ Pickle I/O error → handle gracefully

### Integration Tests

**End-to-End Authentication Flow**:
- Mock robin_stocks responses
- Test complete login flow with MFA
- Test session restoration from pickle
- Test token refresh on expiry
- Test logout and cleanup

### Security Tests

**Credential Leakage Prevention**:
- Verify credentials NOT in logs
- Verify credentials NOT in error messages
- Verify pickle file has correct permissions
- Verify credentials cleared from memory

---

## Configuration

**Environment Variables (.env)**:
```bash
# Required
ROBINHOOD_USERNAME=your_email@example.com
ROBINHOOD_PASSWORD=your_secure_password

# Optional (for MFA - recommended)
ROBINHOOD_MFA_SECRET=BASE32_ENCODED_SECRET

# Optional (for faster auth - bypasses MFA)
ROBINHOOD_DEVICE_TOKEN=your_device_token_if_available
```

**In config.py**:
```python
class Config:
    """Configuration loaded from environment variables."""

    def __init__(self):
        load_dotenv()  # Load .env file

        # Authentication (required)
        self.robinhood_username = os.getenv("ROBINHOOD_USERNAME")
        self.robinhood_password = os.getenv("ROBINHOOD_PASSWORD")

        # MFA (optional but recommended)
        self.robinhood_mfa_secret = os.getenv("ROBINHOOD_MFA_SECRET")

        # Device token (optional, for faster auth)
        self.robinhood_device_token = os.getenv("ROBINHOOD_DEVICE_TOKEN")

        # Validate required credentials
        if not self.robinhood_username or not self.robinhood_password:
            raise ValueError("Missing required credentials: ROBINHOOD_USERNAME and ROBINHOOD_PASSWORD")
```

---

## Deployment Considerations

### Dependencies

**New Dependency**:
- `pyotp` - Must add to requirements.txt
  ```
  pyotp==2.9.0
  ```

**Existing Dependencies**:
- ✅ `robin-stocks==3.0.5` (already in requirements.txt)
- ✅ `python-dotenv==1.0.0` (already in requirements.txt)

### Breaking Changes
- ❌ **No breaking changes** (new module, additive only)
- ✅ Bot startup will now require authentication
- ✅ Existing bot.py will need to integrate RobinhoodAuth

### Environment Setup
- ✅ Users must create .env file with credentials
- ✅ .env.example already documents required variables
- ✅ Bot fails safely if credentials missing (§Pre_Deploy)

### Security Considerations
- ✅ .env file must be in .gitignore (already is)
- ✅ .robinhood.pickle must be in .gitignore (add if needed)
- ✅ Pickle file permissions set to 600 automatically
- ✅ Credentials never logged or exposed

### Migration
- ❌ **No database migration** (uses pickle file)
- ✅ .robinhood.pickle created on first successful login
- ✅ Can delete pickle to force re-authentication

### Rollback
- ✅ Standard rollback (remove auth module import from bot.py)
- ✅ Delete .robinhood.pickle if needed
- ✅ No state to clean up (stateless auth)

---

## Success Criteria

### Acceptance Criteria
- [ ] All 7 functional requirements implemented
- [ ] Test coverage ≥90% (NFR-005)
- [ ] Successful login with username/password + MFA
- [ ] Session restored from pickle on bot restart
- [ ] Token auto-refresh on expiry
- [ ] Logout cleans up session and pickle
- [ ] Credentials never logged or exposed (NFR-001)
- [ ] mypy passes with no errors (NFR-006)

### Quality Gates (§Pre_Deploy)
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] bandit security scan clean (no credential leaks)
- [ ] Manual testing: First-time login with MFA
- [ ] Manual testing: Session restoration from pickle
- [ ] Manual testing: Token refresh on expiry
- [ ] Manual testing: Logout and cleanup
- [ ] Manual testing: Invalid credentials rejection

---

## Open Questions

None - Spec is clear based on roadmap requirements and robin-stocks documentation.

---

## References

- Constitution: `.specify/memory/constitution.md` (§Security, §Audit_Everything, §Pre_Deploy)
- Roadmap: `.specify/memory/roadmap.md` (authentication-module feature)
- Config: `config.py` (credential loading)
- Logger: `src/trading_bot/logger.py` (audit logging)
- robin-stocks: https://robin-stocks.readthedocs.io/ (API reference)
- pyotp: https://pyotp.readthedocs.io/ (MFA TOTP generation)
- Environment: `.env.example` (credential template)
