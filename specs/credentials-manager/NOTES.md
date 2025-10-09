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

## Last Updated
2025-10-08T23:20:00-05:00
