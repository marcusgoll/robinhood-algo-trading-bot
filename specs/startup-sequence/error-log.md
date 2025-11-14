# Error Log: Startup Sequence

## Planning Phase (Phase 0-2)
None.

## Implementation Phase (Phase 3-4)
Completed successfully with TDD approach (T001-T046).

## Testing Phase (Phase 5)
Integration tests passing (3/3). Ready for deployment.

## Deployment Phase (Phase 6-7)

### Common Startup Errors and Remediation

**Error ID**: ERR-001
**Phase**: Deployment
**Date**: 2025-10-09
**Component**: Configuration
**Severity**: High

**Description**:
Startup fails with "Missing .env file" error during configuration loading phase.

**Root Cause**:
User has not created .env file from .env.example template, or .env file was deleted/moved.

**Resolution**:
1. Copy .env.example to .env
2. Add required credentials: ROBINHOOD_USERNAME and ROBINHOOD_PASSWORD
3. Optionally add ROBINHOOD_MFA_SECRET and ROBINHOOD_DEVICE_TOKEN

**Prevention**:
- Update installation docs to emphasize .env file creation
- Add validation in validate_startup.py to check for .env existence before bot starts

**Related**:
- Spec: specs/startup-sequence/spec.md (Requirement R1)
- Code: src/trading_bot/validator.py:84-88
- Remediation: README.md Troubleshooting section

---

**Error ID**: ERR-002
**Phase**: Deployment
**Date**: 2025-10-09
**Component**: Configuration
**Severity**: High

**Description**:
Startup fails with JSON parsing error or "Invalid configuration" when loading config.json.

**Root Cause**:
config.json has invalid JSON syntax (trailing commas, unquoted keys, missing braces) or invalid parameter values (negative numbers, out-of-range percentages).

**Resolution**:
1. Validate JSON syntax: `python -m json.tool config.json`
2. If invalid, copy from example: `cp config.example.json config.json`
3. Edit config.json with valid values
4. Run dry run to validate: `python -m src.trading_bot --dry-run`

**Prevention**:
- Use JSON schema validation in ConfigValidator
- Add config.json validation to pre-commit hooks
- Provide better error messages with line numbers for JSON errors

**Related**:
- Spec: specs/startup-sequence/spec.md (Requirement R2)
- Code: src/trading_bot/config.py:100-102
- Remediation: README.md Troubleshooting section

---

**Error ID**: ERR-003
**Phase**: Deployment
**Date**: 2025-10-09
**Component**: Validation
**Severity**: Critical

**Description**:
Startup blocked with "Cannot use live trading in 'experience' phase" error.

**Root Cause**:
Phase-mode conflict: config.json has `"mode": "live"` but `"current_phase": "experience"`. Constitution v1.0.0 Safety_First principle prohibits live trading in experience phase.

**Resolution**:
Edit config.json and either:
- Change mode to paper: `"mode": "paper"` (recommended)
- OR change phase to proof/trial/scaling: `"current_phase": "proof"` (only if ready for live trading)

**Prevention**:
- ConfigValidator enforces this rule (already implemented)
- Add warning when switching to live mode in experience phase
- Document phase progression requirements clearly in README

**Related**:
- Spec: specs/startup-sequence/spec.md (Requirement R3)
- Code: src/trading_bot/validator.py:145-149
- Constitution: .specify/memory/constitution.md (Safety_First)
- Remediation: README.md Troubleshooting section

---

**Error ID**: ERR-004
**Phase**: Deployment
**Date**: 2025-10-09
**Component**: Filesystem
**Severity**: Medium

**Description**:
Startup fails with "Failed to create directories" or "Permission denied" error when creating logs/, data/, or backtests/ directories.

**Root Cause**:
Insufficient filesystem permissions in working directory, or parent directory doesn't exist.

**Resolution**:
1. Check directory permissions: `ls -la logs/ data/ backtests/`
2. Create directories manually: `mkdir -p logs data backtests`
3. Set proper permissions: `chmod 755 logs data backtests`
4. Ensure working directory is writable

**Prevention**:
- Add filesystem permission check to validate_startup.py
- Create directories during installation step
- Document required permissions in README

**Related**:
- Spec: specs/startup-sequence/spec.md (Requirement R4)
- Code: src/trading_bot/config.py:213-217
- Remediation: README.md Troubleshooting section

---

**Error ID**: ERR-005
**Phase**: Deployment
**Date**: 2025-10-09
**Component**: Initialization
**Severity**: High

**Description**:
Startup fails with "Component X initialization failed" error during component setup phase (logging, mode_switcher, circuit_breaker, or trading_bot).

**Root Cause**:
Multiple possible causes:
- Missing dependencies (robin_stocks, python-dotenv, etc.)
- Invalid configuration parameters preventing component initialization
- Import errors or module not found
- Logger handler creation failure

**Resolution**:
1. Check logs/startup.log for detailed error traceback
2. Verify all dependencies installed: `pip install -r requirements.txt`
3. Ensure .env and config.json are valid
4. Run dry run to isolate issue: `python -m src.trading_bot --dry-run`
5. Check Python version (requires 3.11+)

**Prevention**:
- Add dependency validation to validate_startup.py
- Improve error messages with specific remediation steps
- Add health check for each component after initialization
- Document required dependencies and versions

**Related**:
- Spec: specs/startup-sequence/spec.md (Requirement R5-R8)
- Code: src/trading_bot/startup.py:148-276
- Remediation: README.md Troubleshooting section

---

## Error Template

**Error ID**: ERR-[NNN]
**Phase**: [Planning/Implementation/Testing/Deployment]
**Date**: YYYY-MM-DD HH:MM
**Component**: [api/frontend/database/deployment]
**Severity**: [Critical/High/Medium/Low]

**Description**:
[What happened]

**Root Cause**:
[Why it happened]

**Resolution**:
[How it was fixed]

**Prevention**:
[How to prevent in future]

**Related**:
- Spec: [link to requirement]
- Code: [file:line]
- Commit: [sha]
