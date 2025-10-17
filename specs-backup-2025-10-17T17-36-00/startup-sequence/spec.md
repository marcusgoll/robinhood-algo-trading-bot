# Feature Specification: Startup Sequence

## Overview

**Feature**: Startup Sequence
**Status**: Draft
**Created**: 2025-10-08
**Last Updated**: 2025-10-08

### Purpose

Formalize and enhance the trading bot's startup sequence to ensure all critical components are initialized, validated, and ready before any trading activity begins. This specification defines the complete startup workflow from initial invocation through the first trade-ready state.

### Context

Currently, the bot has basic configuration validation (`validate_startup.py`) and component initialization (`bot.py`), but lacks a formalized, comprehensive startup sequence that:
- Orchestrates component initialization in the correct order
- Provides clear feedback at each stage
- Handles startup failures gracefully
- Ensures all safety systems are active before trading
- Supports both automated and manual startup modes

### Hypothesis

**Problem**: Ad-hoc startup process leads to inconsistent initialization, unclear error states, and potential safety gaps when components fail to load.

**Solution**: Implement a structured startup sequence orchestrator that validates, initializes, and verifies all components in dependency order with clear status reporting.

**Prediction**: A formalized startup sequence will reduce initialization errors by 80%, provide 100% visibility into startup state, and prevent trading with partially-initialized systems.

## User Scenarios

### Scenario 1: Successful startup (Paper trading mode)

**Given** the user has valid credentials in `.env` and `config.json` configured for paper trading
**When** the user runs `python -m src.trading_bot.main`
**Then** the system should:
1. Display startup banner with mode indicator
2. Load and validate configuration
3. Initialize logging system
4. Initialize mode switcher
5. Initialize circuit breakers
6. Verify all components are ready
7. Display "Ready to trade" confirmation
8. Wait for trading hours or user command

**Expected Output**:
```
════════════════════════════════════════════════════════════
         ROBINHOOD TRADING BOT - STARTUP SEQUENCE
════════════════════════════════════════════════════════════
Mode: PAPER TRADING (Simulation - No Real Money)
Constitution: v1.0.0
════════════════════════════════════════════════════════════

[✓] Loading configuration...
[✓] Validating credentials...
[✓] Initializing logging system...
[✓] Initializing mode switcher (PAPER mode)...
[✓] Initializing circuit breakers...
[✓] Verifying component health...

════════════════════════════════════════════════════════════
✅ STARTUP COMPLETE - Ready to trade
════════════════════════════════════════════════════════════
Current Phase: experience
Max Trades Today: 999
Circuit Breaker: Active (Max Loss: 3%, Max Consecutive: 3)

Waiting for market hours (7:00 AM - 10:00 AM EST)...
```

### Scenario 2: Startup failure (Missing credentials)

**Given** the user has not configured `.env` file
**When** the user runs `python -m src.trading_bot.main`
**Then** the system should:
1. Display startup banner
2. Attempt to load configuration
3. Detect missing credentials
4. Display clear error message with remediation steps
5. Exit with non-zero status code
6. NOT initialize any trading components

**Expected Output**:
```
════════════════════════════════════════════════════════════
         ROBINHOOD TRADING BOT - STARTUP SEQUENCE
════════════════════════════════════════════════════════════

[✓] Loading configuration...
[✗] Validation failed: Missing required credentials

❌ STARTUP BLOCKED

Error: ROBINHOOD_USERNAME not found in .env file

Remediation steps:
  1. Copy .env.example to .env
  2. Set ROBINHOOD_USERNAME in .env
  3. Set ROBINHOOD_PASSWORD in .env
  4. Re-run: python -m src.trading_bot.main

For help, see: README.md (Security section)
```

### Scenario 3: Live trading mode attempted in "experience" phase

**Given** the user has `config.json` set to `"mode": "live"` and `"current_phase": "experience"`
**When** the user runs `python -m src.trading_bot.main`
**Then** the system should:
1. Load configuration
2. Detect phase-mode conflict during validation
3. Block startup with clear error
4. Suggest phase advancement or mode change
5. Exit without initializing trading components

**Expected Output**:
```
════════════════════════════════════════════════════════════
         ROBINHOOD TRADING BOT - STARTUP SEQUENCE
════════════════════════════════════════════════════════════

[✓] Loading configuration...
[✗] Validation failed: Phase-mode conflict

❌ STARTUP BLOCKED

Error: Live trading not allowed in "experience" phase

Remediation steps:
  1. Change mode to "paper" in config.json, OR
  2. Advance to "proof" phase (requires 10-20 profitable sessions)

Safety: Constitution §Safety_First blocks live trading in experience phase
```

### Scenario 4: Component initialization failure

**Given** all configuration is valid
**When** a component (e.g., logger) fails to initialize due to filesystem permissions
**Then** the system should:
1. Progress through startup steps until failure
2. Detect component initialization failure
3. Display error with context
4. Attempt graceful cleanup of initialized components
5. Exit with diagnostic information

### Scenario 5: Startup in dry-run mode (validation only)

**Given** the user wants to test configuration without starting the bot
**When** the user runs `python -m src.trading_bot.main --dry-run`
**Then** the system should:
1. Run all validation steps
2. Initialize all components
3. Report readiness status
4. Exit successfully without entering trading loop

## Requirements

### Functional Requirements

- **FR-001**: Startup orchestrator shall execute initialization steps in dependency order
  - Configuration → Logging → Validation → Mode Switcher → Circuit Breakers → Trading Bot

- **FR-002**: Each startup step shall report success/failure with clear visual indicators
  - `[✓]` for success, `[✗]` for failure, `[⚠]` for warnings

- **FR-003**: Startup shall display comprehensive configuration summary before trading begins
  - Current mode (PAPER/LIVE), phase, max trades, circuit breaker settings, trading hours

- **FR-004**: Startup shall support `--dry-run` flag for validation-only mode
  - All validation and initialization performed, but no trading loop entered

- **FR-005**: Startup shall handle all failure scenarios gracefully
  - Missing credentials, invalid config, component failures, phase-mode conflicts

- **FR-006**: Startup shall provide remediation guidance for all error states
  - Clear steps to fix configuration, environment, or permissions issues

- **FR-007**: Startup shall enforce Constitution safety rules during initialization
  - Block live trading in experience phase, require credentials, activate circuit breakers

- **FR-008**: Startup shall create all required directories if missing
  - `logs/`, `data/`, `backtests/results/` with proper permissions

- **FR-009**: Startup shall log all initialization events to startup log file
  - Separate `logs/startup.log` with detailed initialization audit trail

- **FR-010**: Startup shall display startup duration and readiness timestamp
  - "Startup completed in 2.3s at 2025-10-08 14:23:45 UTC"

### Non-Functional Requirements

- **NFR-001**: Startup sequence shall complete in <5 seconds on standard hardware
  - Measured from command invocation to "Ready to trade" message

- **NFR-002**: All startup messages shall be written to stdout for operator visibility
  - AND logged to `logs/startup.log` for audit trail

- **NFR-003**: Startup errors shall exit with appropriate status codes
  - 0 = success, 1 = configuration error, 2 = validation error, 3 = initialization failure

- **NFR-004**: Startup shall be idempotent (can be run multiple times safely)
  - No side effects from repeated startup attempts

- **NFR-005**: Startup output shall be human-readable with clear visual hierarchy
  - Banners, sections, indentation, color coding (if terminal supports)

- **NFR-006**: Startup shall provide machine-readable status output via `--json` flag
  - JSON object with status, errors, warnings, component states

## Design Decisions

### Startup Sequence Order

1. **Display Banner** - Visual confirmation of bot launch
2. **Load Configuration** - Read `.env` and `config.json`
3. **Validate Configuration** - Run all validation checks
4. **Initialize Logging** - Set up log files and handlers
5. **Initialize Mode Switcher** - Set paper/live mode
6. **Initialize Circuit Breakers** - Activate safety systems
7. **Initialize Trading Bot** - Create bot instance
8. **Verify Component Health** - Check all systems ready
9. **Display Readiness Summary** - Final status report
10. **Enter Trading Loop** - Begin market monitoring (unless dry-run)

**Rationale**: Dependencies dictate order (config before validation, logging before component init, etc.)

### Error Handling Strategy

- **Fail Fast**: Stop immediately on critical errors (missing credentials, invalid config)
- **Graceful Cleanup**: If component fails to initialize, clean up previously initialized components
- **Clear Remediation**: Every error includes specific steps to fix
- **No Partial Initialization**: Either fully ready or fully failed (no in-between states)

### Display Format

- **Banners**: Use box-drawing characters for visual separation
- **Progress Indicators**: `[✓]`, `[✗]`, `[⚠]` for at-a-glance status
- **Indentation**: Two spaces for nested information
- **Color Coding**: Green (success), Red (error), Yellow (warning) - if terminal supports ANSI

### Dry-Run Mode

- **Purpose**: Validate configuration without entering trading loop
- **Usage**: `python -m src.trading_bot.main --dry-run`
- **Behavior**: Complete all initialization, report status, exit 0 if ready or non-zero if errors

### JSON Output Mode

- **Purpose**: Machine-readable startup status for monitoring/automation
- **Usage**: `python -m src.trading_bot.main --json`
- **Format**:
```json
{
  "status": "ready|blocked",
  "mode": "paper|live",
  "phase": "experience|proof|trial|scaling",
  "startup_duration_seconds": 2.3,
  "timestamp": "2025-10-08T14:23:45Z",
  "components": {
    "config": {"status": "ready", "errors": []},
    "logging": {"status": "ready", "errors": []},
    "mode_switcher": {"status": "ready", "mode": "paper"},
    "circuit_breaker": {"status": "ready", "max_loss": 3.0},
    "trading_bot": {"status": "ready", "is_running": false}
  },
  "errors": [],
  "warnings": ["MFA secret not configured - manual authentication required"]
}
```

## Implementation Notes

### Components to Create

1. **`src/trading_bot/startup.py`** - Startup orchestrator class
   - `StartupOrchestrator` class with step-by-step initialization
   - `StartupStep` dataclass for each initialization stage
   - `display_banner()`, `display_summary()`, `cleanup_on_failure()` methods

2. **`src/trading_bot/main.py`** - Entry point script
   - Argument parsing (`--dry-run`, `--json`)
   - Invokes `StartupOrchestrator.run()`
   - Handles exit codes

3. **`logs/startup.log`** - Dedicated startup log file
   - All initialization events logged here
   - Separate from `trading_bot.log` for clarity

### Integration Points

- **Uses Existing**:
  - `Config.from_env_and_json()` - Configuration loading
  - `ConfigValidator.validate_all()` - Validation logic
  - `ModeSwitcher` - Mode management
  - `TradingBot` - Main bot instance
  - `setup_logging()` - Logging initialization

- **Extends**:
  - Add startup-specific logging to `logger.py`
  - Add `--dry-run` and `--json` argument parsing to entry point

### Testing Strategy

- **Unit Tests**: Test each startup step in isolation
  - Mock file system, config loading, component initialization
  - Test error paths (missing files, invalid config, permission errors)

- **Integration Tests**: Test complete startup sequence
  - Happy path (all valid)
  - Error paths (missing .env, invalid config, phase conflicts)
  - Dry-run mode
  - JSON output mode

- **Test Fixtures**:
  - `tests/fixtures/config/` - Sample .env and config.json files
  - `tests/fixtures/logs/` - Temporary log directory for tests

## Deployment Considerations

### Platform Dependencies

- **None** - Pure Python implementation, no external services required

### Environment Variables

- **No new variables** - Uses existing `ROBINHOOD_*` variables from `.env`

### Breaking Changes

- **No** - Startup sequence is new orchestration of existing components
- **Backward Compatible** - Existing bot still works, just better organized

### Migration Required

- **No** - No database changes, no schema updates

### Rollback Considerations

- **Standard** - If startup sequence has issues, rollback to previous commit
- **No data loss** - No persistent state changes during startup

## Success Criteria

1. **Clarity**: 100% of operators understand startup status from console output
2. **Reliability**: Startup sequence completes successfully 99%+ of the time with valid config
3. **Safety**: 0 instances of trading with partially-initialized systems
4. **Debuggability**: All startup issues diagnosable from `logs/startup.log`
5. **Performance**: Startup completes in <5 seconds
6. **Coverage**: All error paths tested and documented

## Open Questions

None - Specification is clear and actionable.

## References

- **Constitution**: `.specify/memory/constitution.md` (§Safety_First, §Pre_Deploy)
- **Existing Validation**: `validate_startup.py`
- **Bot Implementation**: `src/trading_bot/bot.py`
- **Config System**: `src/trading_bot/config.py`, `src/trading_bot/validator.py`
- **Mode Switcher**: `src/trading_bot/mode_switcher.py`
- **README**: Installation and configuration guide

## Changelog

- **2025-10-08**: Initial specification created
