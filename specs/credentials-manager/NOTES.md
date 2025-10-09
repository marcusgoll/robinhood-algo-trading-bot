# Feature: credentials-manager

## Overview
Secure credentials management system for Robinhood trading bot. Provides secure storage, validation, and testing of credentials including username, password, MFA secret, and device token.

## Research Findings

### Finding 1: Security Requirements from Constitution
- Source: .spec-flow/memory/constitution.md (§Security)
- Requirements: No credentials in code, API keys encrypted, minimal permissions
- Implication: Must use secure storage mechanism (environment variables or vault)

### Finding 2: Existing Environment Configuration
- Source: Roadmap - environment-config shipped (2025-10-07)
- Delivered: .env.example with credentials fields, Config.from_env_and_json() loader
- Integration point: Build on existing config system

### Finding 3: Existing Configuration Validator
- Source: Roadmap - configuration-validator shipped (2025-10-07)
- Delivered: ConfigValidator class with credential checks
- Integration point: Extend validation for MFA format and device token

### Finding 4: Authentication Module
- Source: Roadmap - authentication-module shipped (2025-01-08)
- Delivered: RobinhoodAuth service with MFA support, device token support
- Integration point: Test authentication on first run, store device token

### Finding 5: Blocker Resolved
- Source: Roadmap - credentials-manager was [BLOCKED: environment-config]
- Status: Unblocked (environment-config shipped 2025-10-07)
- Action: Proceed with implementation

## System Components Analysis

**Backend-Only Feature**: No UI components

**Existing Components to Reuse**:
- Config.from_env_and_json() - Dual-source configuration loader
- ConfigValidator - Credential validation framework
- RobinhoodAuth - Authentication service with MFA support
- TradingLogger - Structured logging for audit trail

**New Components Needed**:
- CredentialsManager - Secure storage and retrieval
- MFA validator - Validate TOTP secret format
- Device token persistence - Store token after successful auth

**Rationale**: Integrates with existing infra to provide secure credential lifecycle management.

## Feature Classification
- UI screens: false
- Improvement: false
- Measurable: true (error rates, auth success rates)
- Deployment impact: false (extends existing .env pattern)

## Key Decisions

1. **Storage mechanism**: Use .env file (consistent with environment-config feature)
   - Rationale: Already established pattern, .gitignore'd, simple
   - Alternative rejected: Keyring (adds dependency, overkill for local bot)

2. **MFA validation**: Check TOTP secret format before first auth attempt
   - Rationale: Fail fast with clear error vs cryptic API error
   - Format: 16-character base32 string (pyotp standard)

3. **Device token workflow**: Test auth on first run, save token on success
   - Rationale: Reduces MFA fatigue for subsequent runs
   - Storage: .env DEVICE_TOKEN field (auto-updated)

4. **Credential masking**: Never log full credentials
   - Rationale: §Security compliance, §Audit_Everything
   - Pattern: username (first 3 chars + ***), password (*****), MFA (****), token (first 8 chars + ***)

5. **Integration point**: Extend ConfigValidator with new checks
   - Rationale: Reuse existing validation framework
   - New checks: MFA format, device token format (if provided)

## Checkpoints
- Phase 0 (Spec): 2025-10-08
- Phase 1 (Plan): 2025-10-08
- Phase 2 (Tasks): 2025-10-08

## Phase 2 Summary (Tasks)
- Total tasks: 34
- TDD trios: 16 behaviors (RED -> GREEN -> REFACTOR)
- Parallel tasks: 7 (setup, config, documentation)
- Test tasks: 21 (unit + integration)
- Backend tasks: 26 (implementation)
- Task file: specs/credentials-manager/tasks.md

**Key Task Breakdown**:
- Phase 3.1 Setup: 3 tasks (utils/security.py module, .env.example update, Config field)
- Phase 3.2 RED: 11 tasks (credential masking, validation, token persistence tests)
- Phase 3.3 GREEN: 6 tasks (implementation to pass tests)
- Phase 3.4 REFACTOR: 3 tasks (extract masking, clean validation, type hints)
- Phase 3.5 Integration: 5 tasks (end-to-end auth flows with device token)
- Phase 3.6 Error Handling: 3 tasks (performance targets, retry logic)
- Phase 3.7 Documentation: 3 tasks (README, docstrings, coverage)

**Reuse Opportunities**:
- ConfigValidator: Extend with 2 validation methods
- RobinhoodAuth: Extend with 2 token management methods
- @with_retry: Apply to auth operations
- utils/security.py: Extract credential masking (4 functions)

**Dependencies**:
- RED tasks (T004-T014) independent, can run in parallel
- GREEN tasks depend on corresponding RED tests
- Integration tests (T024-T027) depend on unit implementations
- Documentation (T032-T034) final phase

**Ready for**: /analyze

## Last Updated
2025-10-08T23:25:00-05:00
