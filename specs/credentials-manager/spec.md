# Feature Specification: Secure Credentials Management

**Branch**: `credentials-manager`
**Created**: 2025-10-08
**Status**: Draft

## User Scenarios

### Primary User Story
As a bot operator, I need to securely store and manage my Robinhood credentials (username, password, MFA secret, device token) so that the bot can authenticate automatically while protecting sensitive data from exposure.

### Acceptance Scenarios

1. **Given** I am setting up the bot for the first time, **When** I provide credentials in .env file, **Then** the system validates credential format and tests authentication before allowing bot startup

2. **Given** I have successfully authenticated once, **When** the bot starts on subsequent runs, **Then** the system uses the stored device token to skip MFA verification

3. **Given** I provide an invalid MFA secret format, **When** the system validates credentials, **Then** I receive a clear error message explaining the required format (16-character base32 string)

4. **Given** the bot is running, **When** credentials are logged, **Then** sensitive data is masked (username first 3 chars + ***, password *****, MFA ****, token first 8 chars + ***)

5. **Given** authentication fails with stored device token, **When** the system detects 401 error, **Then** the system falls back to MFA authentication and updates the device token on success

### Edge Cases

- What happens when MFA secret is valid format but incorrect value? System attempts auth, logs failure with masked credentials, provides clear error message
- What happens when device token is corrupted? System detects invalid token format, falls back to MFA authentication
- What happens when .env file has missing required fields? ConfigValidator blocks startup with specific missing field error
- What happens when credentials are correct but API is down? Retry logic with exponential backoff (from error-handling-framework)

## Success Metrics (HEART Framework)

> **Note**: Backend-only feature with security/reliability focus

| Dimension | Goal | Signal | Metric | Target | Guardrail |
|-----------|------|--------|--------|--------|-----------|
| **Happiness** | Reduce auth errors | Failed auth attempts | Error rate from logs | <2% failure rate | Alert if >5% failures |
| **Engagement** | Streamline auth flow | Device token reuse | Token hit rate | >95% use device token | N/A |
| **Adoption** | Enable secure setup | First-time setup success | Initial config completion | 100% setup success | <5min setup time |
| **Retention** | Maintain auth state | Session persistence | Token refresh frequency | <1 reauth/week | Alert if >1/day |
| **Task Success** | Successful authentication | Auth completion | Auth success rate | >98% success | <30s auth time |

**Measurement Sources**:
- Error rate: `grep '"event":"auth_failed"' logs/errors.log | wc -l`
- Token hit rate: `grep '"auth_method":"device_token"' logs/trading_bot.log | wc -l` / total auth attempts
- Auth success rate: `grep '"event":"auth_success"' logs/trading_bot.log | wc -l` / total auth attempts

## Context Strategy & Signal Design

- **System prompt altitude**: Mid-level (secure credential handling patterns, validation requirements)
- **Tool surface**: File I/O (read .env), validation utilities, logging (masked output)
- **Examples in scope**: MFA format validation, device token persistence, credential masking
- **Context budget**: 15k tokens (small focused feature)
- **Retrieval strategy**: JIT - load existing Config/ConfigValidator on demand
- **Memory artifacts**: NOTES.md updated with integration decisions
- **Compaction cadence**: Not needed (small feature)
- **Sub-agents**: None (single focused component)

## Requirements

### Functional (testable only)

- **FR-001**: System MUST validate MFA secret is 16-character base32 string before attempting authentication
- **FR-002**: System MUST test authentication on first run (when DEVICE_TOKEN is empty or missing)
- **FR-003**: System MUST store device token in .env file after successful first authentication
- **FR-004**: System MUST use device token for authentication on subsequent runs (skip MFA if token exists)
- **FR-005**: System MUST fall back to MFA authentication if device token authentication fails
- **FR-006**: System MUST update device token in .env after successful MFA fallback
- **FR-007**: System MUST mask credentials in all log output (username: first 3 + ***, password: *****, MFA: ****, token: first 8 + ***)
- **FR-008**: System MUST validate all required credential fields exist in .env before startup
- **FR-009**: System MUST block startup if credential validation fails
- **FR-010**: System MUST integrate with existing ConfigValidator for credential checks

### Non-Functional

- **NFR-001**: Security: Credentials MUST NOT appear in plaintext logs (§Security compliance)
- **NFR-002**: Performance: Credential validation MUST complete in <500ms
- **NFR-003**: Reliability: Authentication retry logic MUST use exponential backoff (1s, 2s, 4s) from error-handling-framework
- **NFR-004**: Auditability: All credential operations MUST be logged with masked values (§Audit_Everything)
- **NFR-005**: Error Handling: Validation errors MUST provide clear remediation guidance

### Key Entities

- **Credentials**: Username, password, MFA secret, device token (optional)
  - Attributes: username (string), password (string), mfa_secret (string, base32), device_token (string, optional)
  - Storage: .env file (environment-config pattern)
  - Validation: Format checks via ConfigValidator

- **DeviceToken**: Persistent authentication token to skip MFA
  - Attributes: token (string), created_at (timestamp)
  - Storage: .env DEVICE_TOKEN field
  - Lifecycle: Created on first auth, refreshed on MFA fallback, used for subsequent auth

## Deployment Considerations

> **Skip**: No platform dependencies, uses existing .env pattern. Extends existing ConfigValidator.

### Platform Dependencies
None - extends existing configuration system

### Environment Variables

**Existing Variables** (from environment-config):
- `ROBINHOOD_USERNAME`: Robinhood account username
- `ROBINHOOD_PASSWORD`: Robinhood account password
- `ROBINHOOD_MFA_SECRET`: TOTP secret for MFA (16-char base32)

**New Variables**:
- `DEVICE_TOKEN`: Persistent auth token (auto-populated after first successful auth)
  - Staging value: (empty initially, auto-populated)
  - Production value: (empty initially, auto-populated)

**Schema Update Required**: Yes - Update .env.example with DEVICE_TOKEN field and validation rules in ConfigValidator

### Breaking Changes

**API Contract Changes**: No

**Database Schema Changes**: No

**Auth Flow Modifications**: No (extends existing RobinhoodAuth service)

**Client Compatibility**: Backward compatible (DEVICE_TOKEN is optional)

### Migration Requirements

**Database Migrations**: No

**Data Backfill**: No

**RLS Policy Changes**: No

**Reversibility**: Fully reversible (remove DEVICE_TOKEN from .env)

### Rollback Considerations

**Standard Rollback**: Yes - 3-command rollback via runbook/rollback.md

**Special Rollback Needs**: None

**Deployment Metadata**: Tracked in specs/credentials-manager/NOTES.md

---

## Measurement Plan

> **Purpose**: Monitor auth success rates and security compliance

### Data Collection

**Structured Logs** (Claude measurement):
```python
logger.info({
  "event": "auth_success",
  "auth_method": "device_token" | "mfa",
  "username": mask_username(username),
  "duration_ms": duration
})

logger.error({
  "event": "auth_failed",
  "auth_method": "device_token" | "mfa",
  "username": mask_username(username),
  "error": error_message
})
```

**Key Events to Track**:
1. `credentials.validated` - Config validation success
2. `credentials.validation_failed` - Config validation failure (with reason)
3. `auth.success` - Authentication success (with method: device_token | mfa)
4. `auth.failed` - Authentication failure (with method and error)
5. `device_token.stored` - New device token saved to .env
6. `device_token.refreshed` - Device token updated after MFA fallback

### Measurement Queries

**Logs** (`logs/trading_bot.log`, `logs/errors.log`):
```bash
# Auth success rate
SUCCESS=$(grep '"event":"auth_success"' logs/trading_bot.log | wc -l)
TOTAL=$(grep '"event":"auth' logs/trading_bot.log | wc -l)
echo "scale=2; $SUCCESS * 100 / $TOTAL" | bc

# Device token hit rate
TOKEN_AUTH=$(grep '"auth_method":"device_token"' logs/trading_bot.log | wc -l)
echo "scale=2; $TOKEN_AUTH * 100 / $TOTAL" | bc

# Error rate
ERRORS=$(grep '"event":"auth_failed"' logs/errors.log | wc -l)
echo "scale=2; $ERRORS * 100 / $TOTAL" | bc

# Average auth duration
grep '"event":"auth_success"' logs/trading_bot.log | \
  jq -r '.duration_ms' | \
  awk '{sum+=$1; count++} END {print sum/count}'
```

### Success Criteria

**Phase 1: Development** (Unit tests)
- All validation tests pass (MFA format, device token format)
- Credential masking verified in test logs
- Integration with ConfigValidator verified

**Phase 2: Paper Trading** (Integration tests)
- First-time auth with MFA completes successfully
- Device token stored after first auth
- Subsequent auth uses device token (no MFA prompt)
- MFA fallback triggers on invalid device token
- All credentials masked in logs

**Phase 3: Production** (Live monitoring)
- Auth success rate >98%
- Device token hit rate >95%
- Error rate <2%
- Average auth duration <5s

---

## Quality Gates *(all must pass before `/plan`)*

### Core Requirements
- [x] No implementation details (tech stack, APIs, code)
- [x] Requirements testable and unambiguous
- [x] Context strategy documented
- [x] No [NEEDS CLARIFICATION] markers
- [x] Constitution aligned (§Security, §Audit_Everything, §Pre_Deploy)

### Success Metrics (HEART)
- [x] All 5 HEART dimensions have targets defined
- [x] Metrics are Claude Code-measurable (logs)
- [x] Performance targets specified (auth <5s, validation <500ms)

### Screens (UI Features Only)
- [x] Skip - Backend-only feature

### Measurement Plan
- [x] Structured log events defined
- [x] Bash queries drafted for key metrics
- [x] Success criteria for dev/paper/prod phases
- [x] Measurement sources are Claude Code-accessible

### Deployment Considerations
- [x] Platform dependencies documented (None - extends existing)
- [x] Environment variables listed (DEVICE_TOKEN)
- [x] Breaking changes identified (None - backward compatible)
- [x] Migration requirements documented (None)
- [x] Rollback plan specified (Standard)
