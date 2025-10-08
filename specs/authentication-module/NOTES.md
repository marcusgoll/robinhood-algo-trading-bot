# Feature: authentication-module

## Overview
Robinhood authentication with MFA support using pyotp, session management, and error recovery.

## Research Findings

### Existing Infrastructure
- **Config System**: Dual configuration (config.py)
  - .env: Credentials (username, password, MFA secret, device token)
  - config.json: Trading parameters
  - Already supports: `robinhood_username`, `robinhood_password`, `robinhood_mfa_secret`, `robinhood_device_token`

- **Environment Variables** (.env.example):
  - ROBINHOOD_USERNAME
  - ROBINHOOD_PASSWORD
  - ROBINHOOD_MFA_SECRET (optional, for pyotp)
  - ROBINHOOD_DEVICE_TOKEN (optional, for faster auth)

- **Dependencies** (requirements.txt):
  - robin-stocks==3.0.5 (core trading library)
  - pyotp (for MFA) - needs to be added
  - python-dotenv==1.0.0 (env loading)

### Authentication Flow Pattern
Based on robin-stocks library:
1. Login with username/password
2. Handle MFA challenge using pyotp.TOTP(secret).now()
3. Store session in pickle file for persistence
4. Auto-refresh token on expiry
5. Handle logout gracefully

### Constitution Requirements
- §Security: No credentials in code, use environment variables ✓
- §Code_Quality: Type hints required ✓
- §Error_Handling: Graceful failure with retry logic
- §Audit_Everything: Log all authentication events
- §Pre_Deploy: Validate credentials before startup

## System Components Analysis
[Not applicable - backend/API feature]

## Feature Classification
- UI screens: false (backend/API only)
- Improvement: false (new feature)
- Measurable: false (internal authentication)
- Deployment impact: true (env vars, session management)

## Checkpoints
- Phase 0 (Specify): 2025-10-08

## Last Updated
2025-10-08
