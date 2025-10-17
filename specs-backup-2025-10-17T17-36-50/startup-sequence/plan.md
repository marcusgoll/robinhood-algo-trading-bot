# Implementation Plan: Startup Sequence

## [RESEARCH DECISIONS]

### Decision: Dedicated Startup Orchestrator Module
- **Decision**: Create `src/trading_bot/startup.py` as a dedicated orchestrator module
- **Rationale**: Separation of concerns - startup logic is complex enough to warrant its own module rather than embedding in main.py or bot.py. Follows existing pattern where each major concern (config, validator, mode_switcher, logger, bot) has its own module.
- **Alternatives**: Could embed in bot.py (rejected - bot.py should focus on trading logic), or in main.py (rejected - main.py should be thin entry point)
- **Source**: Existing codebase patterns (config.py, validator.py, mode_switcher.py all separate modules)

### Decision: Reuse Existing Validation Infrastructure
- **Decision**: Use existing `ConfigValidator.validate_all()` from validator.py unchanged
- **Rationale**: validator.py already implements all required validation logic (credentials, config parameters, file paths, phase-mode conflicts). No need to duplicate or rewrite.
- **Alternatives**: Write new validation (rejected - DRY principle), extend validator (not needed - covers all requirements)
- **Source**: validator.py lines 46-73, implements Constitution v1.0.0 §Security, §Pre_Deploy, §Safety_First

### Decision: Component Initialization Order Based on Dependencies
- **Decision**: Initialize in this order: Config → Logging → Validation → Mode Switcher → Circuit Breakers → Bot
- **Rationale**: Dependency chain - logging depends on config (for logs_dir), validation depends on config, mode switcher depends on config, bot depends on mode switcher and circuit breakers
- **Alternatives**: Could initialize in different order (rejected - would violate dependencies), could lazy-load (rejected - fail-fast principle requires full initialization)
- **Source**: Constitution v1.0.0 §Safety_First (fail-fast), spec.md FR-001

### Decision: Fail-Fast Error Handling Strategy
- **Decision**: Stop immediately on any critical error (missing credentials, invalid config, component initialization failure) with no partial initialization
- **Rationale**: Constitution §Safety_First requires all safety systems active before trading. Partial initialization could leave safety gaps.
- **Alternatives**: Continue with degraded functionality (rejected - unsafe), retry failed components (rejected - likely same result, wastes time)
- **Source**: spec.md Design Decisions > Error Handling Strategy, Constitution §Safety_First

### Decision: Startup Log Separation from Trading Logs
- **Decision**: Create dedicated `logs/startup.log` separate from `logs/trading_bot.log`
- **Rationale**: Startup issues are distinct from trading issues. Separate log enables quick diagnosis of startup failures without wading through trading activity. Existing logger.py already supports multiple log files (trades.log, errors.log).
- **Alternatives**: Use trading_bot.log (rejected - mixes concerns), use stdout only (rejected - no audit trail)
- **Source**: spec.md FR-009, existing logger.py pattern (lines 59-62 shows TRADES_LOG and ERRORS_LOG separation)

### Decision: Machine-Readable Output via --json Flag
- **Decision**: Support `--json` flag for structured JSON status output
- **Rationale**: Enables monitoring/automation integration. JSON provides machine-parseable status for CI/CD, health checks, and automated testing.
- **Alternatives**: Text-only output (rejected - hard to parse), always output JSON (rejected - bad UX for human operators)
- **Source**: spec.md NFR-006, Design Decisions > JSON Output Mode

### Decision: Visual Progress Indicators Using Unicode
- **Decision**: Use Unicode characters for progress indicators: `[✓]` success, `[✗]` failure, `[⚠]` warnings
- **Rationale**: Universal cross-platform support (Windows/Linux/Mac), clear visual feedback, no ANSI color dependencies. Modern terminals support Unicode.
- **Alternatives**: ANSI color codes (rejected - not all terminals support, adds dependency), ASCII-only (rejected - less visual clarity)
- **Source**: spec.md Design Decisions > Display Format, existing mode_switcher.py uses Unicode (line 167: ⚠️)

---

## [ARCHITECTURE DECISIONS]

**Stack**:
- Language: Python 3.11+
- Framework: None (pure Python stdlib + existing modules)
- Logging: Python logging module (already configured in logger.py)
- Testing: pytest (existing test infrastructure)

**Patterns**:
- **Orchestrator Pattern**: StartupOrchestrator class coordinates initialization sequence
- **Dataclass for State**: StartupStep dataclass tracks each initialization stage
- **Dependency Injection**: Pass Config instance through initialization chain
- **Fail-Fast Validation**: Exit immediately on critical errors with clear remediation
- **Separation of Concerns**: Startup orchestration separate from business logic

**Dependencies** (new packages required):
- None - uses only Python stdlib and existing project dependencies

**Reuse Opportunities** (6 existing components):
- `Config.from_env_and_json()` - Load configuration (config.py line 68)
- `ConfigValidator.validate_all()` - Comprehensive validation (validator.py line 46)
- `TradingLogger.setup()` - Initialize logging system (logger.py line 75)
- `ModeSwitcher` - Mode management and banner display (mode_switcher.py line 36)
- `CircuitBreaker` - Safety system for trading limits (bot.py line 18)
- `TradingBot` - Main bot instance (bot.py line 75)

---

## [STRUCTURE]

**Directory Layout** (follow existing patterns):

```
src/trading_bot/
├── startup.py              # NEW: Startup orchestrator
├── main.py                 # NEW: Entry point with argparse
├── config.py               # REUSE: Configuration loading
├── validator.py            # REUSE: Validation logic
├── logger.py               # EXTEND: Add startup logger
├── mode_switcher.py        # REUSE: Mode management
├── bot.py                  # REUSE: CircuitBreaker, TradingBot
└── ...

logs/
├── startup.log             # NEW: Startup audit trail
├── trading_bot.log         # EXISTING
├── trades.log              # EXISTING
└── errors.log              # EXISTING

tests/
├── unit/
│   ├── test_startup.py     # NEW: Startup orchestrator tests
│   └── test_main.py        # NEW: Entry point tests
└── integration/
    └── test_startup_flow.py # NEW: Full startup integration test
```

**Module Organization**:

**startup.py**:
- `StartupStep` dataclass: Tracks name, status, error_message for each step
- `StartupOrchestrator` class: Coordinates initialization sequence
  - `__init__(config, dry_run, json_output)`: Initialize orchestrator
  - `run() -> StartupResult`: Execute startup sequence
  - `_display_banner()`: Show startup banner with mode
  - `_load_config()`: Load configuration
  - `_validate_config()`: Run validation
  - `_initialize_logging()`: Set up logging
  - `_initialize_mode_switcher()`: Create mode switcher
  - `_initialize_circuit_breakers()`: Create circuit breakers
  - `_initialize_bot()`: Create trading bot instance
  - `_verify_health()`: Check all components ready
  - `_display_summary()`: Show final status
  - `_cleanup_on_failure()`: Gracefully clean up on error
- `StartupResult` dataclass: Return status, errors, warnings, component_states, duration

**main.py**:
- `parse_arguments()`: Handle --dry-run, --json flags
- `main()`: Entry point invoking StartupOrchestrator
- Exit code handling (0=success, 1=config error, 2=validation error, 3=initialization failure)

---

## [SCHEMA]

**No database changes** - Startup sequence does not modify database schema.

**Configuration Schema** (existing config.json):
```json
{
  "trading": {
    "mode": "paper|live",
    "hours": {
      "start_time": "07:00",
      "end_time": "10:00",
      "timezone": "America/New_York"
    }
  },
  "risk_management": {
    "max_position_pct": 5.0,
    "max_daily_loss_pct": 3.0,
    "max_consecutive_losses": 3,
    "position_size_shares": 100,
    "stop_loss_pct": 2.0,
    "risk_reward_ratio": 2.0
  },
  "phase_progression": {
    "current_phase": "experience|proof|trial|scaling",
    "experience": {
      "max_trades_per_day": 999
    },
    "proof": {
      "max_trades_per_day": 1
    }
  }
}
```

**Startup State Schema** (in-memory):
```python
@dataclass
class StartupStep:
    name: str                    # e.g., "Loading configuration"
    status: Literal["pending", "running", "success", "failed"]
    error_message: Optional[str] = None
    duration_seconds: float = 0.0

@dataclass
class StartupResult:
    status: Literal["ready", "blocked"]
    mode: str                    # "paper" or "live"
    phase: str                   # "experience", "proof", "trial", "scaling"
    steps: List[StartupStep]
    errors: List[str]
    warnings: List[str]
    component_states: Dict[str, Dict]
    startup_duration_seconds: float
    timestamp: str               # ISO 8601 UTC
```

**JSON Output Schema** (--json flag):
```json
{
  "status": "ready|blocked",
  "mode": "paper|live",
  "phase": "experience|proof|trial|scaling",
  "startup_duration_seconds": 2.3,
  "timestamp": "2025-10-08T14:23:45Z",
  "components": {
    "config": {
      "status": "ready",
      "errors": []
    },
    "logging": {
      "status": "ready",
      "logs_dir": "logs/"
    },
    "validation": {
      "status": "ready",
      "errors": [],
      "warnings": ["MFA secret not configured"]
    },
    "mode_switcher": {
      "status": "ready",
      "mode": "paper",
      "phase": "experience"
    },
    "circuit_breaker": {
      "status": "ready",
      "max_daily_loss_pct": 3.0,
      "max_consecutive_losses": 3
    },
    "trading_bot": {
      "status": "ready",
      "is_running": false
    }
  },
  "errors": [],
  "warnings": ["MFA secret not configured - manual authentication required"]
}
```

---

## [PERFORMANCE TARGETS]

**From spec.md NFRs**:
- NFR-001: Startup sequence completes in <5 seconds on standard hardware
  - Breakdown: Config load <0.1s, Validation <0.5s, Logging init <0.5s, Component init <1s, Health check <0.5s, Display <0.5s, Buffer 2s
  - Measured from command invocation to "Ready to trade" message

**No Lighthouse targets** - This is a CLI application, not a web application

**Resource Usage**:
- Memory: <50MB for startup orchestrator
- CPU: Minimal (I/O bound, not compute bound)
- Disk: Log files with rotation (10MB max per log file, 5 backups = 50MB total)

---

## [SECURITY]

**Authentication Strategy**:
- Credentials loaded from .env file (existing pattern)
- No API authentication in startup sequence (handled in future authentication-module)
- Validation ensures credentials present before proceeding

**Authorization Model**:
- N/A - No authorization in startup sequence
- Phase-based mode restrictions enforced by ConfigValidator (experience phase = paper only)

**Input Validation**:
- All configuration validated by ConfigValidator.validate_all()
- Phase values validated against whitelist: ["experience", "proof", "trial", "scaling"]
- Risk parameters validated for ranges (max_position_pct 0-100, etc.)

**Data Protection**:
- Credentials never logged or displayed in output
- Startup log contains no PII or sensitive data
- JSON output excludes credentials (only shows component status)

**Secrets Management**:
- Follow existing pattern: .env file for credentials (not in git)
- .env.example provides template without actual secrets
- Startup fails fast if credentials missing (no defaults, no prompts)

---

## [EXISTING INFRASTRUCTURE - REUSE] (6 components)

**Configuration**:
- `src/trading_bot/config.py`: Config dataclass and from_env_and_json() loader
  - Line 68: `Config.from_env_and_json()` - Dual config system (.env + config.json)
  - Line 149: `Config.validate()` - Built-in parameter validation
  - Line 213: `Config.ensure_directories()` - Create required directories

**Validation**:
- `src/trading_bot/validator.py`: ConfigValidator class
  - Line 46: `validate_all()` - Comprehensive validation (credentials, params, paths)
  - Line 75: `_validate_credentials()` - Check .env file and required credentials
  - Line 115: `_validate_config_parameters()` - Validate all config values
  - Line 145: Phase-mode conflict detection (experience + live = blocked)

**Logging**:
- `src/trading_bot/logger.py`: TradingLogger system
  - Line 75: `TradingLogger.setup()` - Initialize logging with rotation
  - Line 23: `UTCFormatter` - UTC timestamps (Constitution §Data_Integrity)
  - Line 59-62: Multiple log files (trading_bot.log, trades.log, errors.log)

**Mode Management**:
- `src/trading_bot/mode_switcher.py`: ModeSwitcher class
  - Line 36: `ModeSwitcher(config)` - Initialize with configuration
  - Line 141: `display_mode_banner()` - Visual mode indicator
  - Line 71: `get_status()` - Current mode and switch permissions

**Safety Systems**:
- `src/trading_bot/bot.py`: CircuitBreaker class
  - Line 18: `CircuitBreaker(max_daily_loss_pct, max_consecutive_losses)`
  - Line 28: `check_and_trip()` - Safety checks
  - Line 68: `reset_daily()` - Reset counters

**Trading Bot**:
- `src/trading_bot/bot.py`: TradingBot class
  - Line 75: `TradingBot(paper_trading, max_position_pct, max_daily_loss_pct, max_consecutive_losses)`
  - Line 122: `start()` - Start trading (checks circuit breaker)
  - Line 131: `stop()` - Emergency stop

---

## [NEW INFRASTRUCTURE - CREATE] (3 components)

**Startup Orchestrator**:
- `src/trading_bot/startup.py`: StartupOrchestrator class
  - Dataclasses: StartupStep, StartupResult
  - Methods: run(), _display_banner(), _load_config(), _validate_config(), _initialize_logging(), _initialize_mode_switcher(), _initialize_circuit_breakers(), _initialize_bot(), _verify_health(), _display_summary(), _cleanup_on_failure()
  - ~300 lines

**Entry Point**:
- `src/trading_bot/main.py`: Main entry point script
  - Functions: parse_arguments(), main()
  - Argument parsing: --dry-run, --json
  - Exit code handling
  - ~100 lines

**Startup Logger**:
- Extend `src/trading_bot/logger.py`: Add startup logger
  - New log file: logs/startup.log
  - New method: TradingLogger.get_startup_logger()
  - ~30 lines added

---

## [CI/CD IMPACT]

**From spec.md deployment considerations:**
- Platform: Local-only trading bot, no web deployment
- Deployment: Manual installation on user's machine
- CI: No CI/CD pipeline currently (local development)

**Build Commands**:
- No changes to build process
- Installation: `pip install -e .` (existing)

**Environment Variables** (no new variables):
- Uses existing ROBINHOOD_USERNAME, ROBINHOOD_PASSWORD from .env
- Optional: ROBINHOOD_MFA_SECRET, ROBINHOOD_DEVICE_TOKEN (already documented)

**Database Migrations**:
- No database changes
- No migrations required

**Testing**:
- Unit tests: pytest tests/unit/test_startup.py
- Integration tests: pytest tests/integration/test_startup_flow.py
- Run all tests: pytest tests/

**Platform Coupling**:
- Pure Python, no platform-specific dependencies
- Cross-platform: Windows, Linux, macOS
- Terminal Unicode support assumed (modern terminals)

---

## [DEPLOYMENT ACCEPTANCE]

**Production Invariants** (must hold true):
- Startup sequence must complete successfully before any trading activity
- All circuit breakers must be initialized and active
- Mode must match phase restrictions (experience = paper only)
- All required directories must exist (logs/, data/, backtests/)
- Credentials must be present in .env file

**Startup Smoke Tests** (Given/When/Then):
```gherkin
Given valid .env and config.json files exist
When user runs `python -m src.trading_bot.main`
Then startup completes in <5 seconds
  And displays "STARTUP COMPLETE - Ready to trade"
  And creates logs/startup.log
  And exit code is 0
  And all components show [✓] status

Given .env file is missing
When user runs `python -m src.trading_bot.main`
Then startup fails immediately
  And displays "Missing required credentials" error
  And shows remediation steps
  And exit code is 1
  And no trading components initialized

Given config.json has mode=live and phase=experience
When user runs `python -m src.trading_bot.main`
Then startup fails at validation
  And displays "Phase-mode conflict" error
  And references Constitution §Safety_First
  And exit code is 2
  And no trading components initialized
```

**Rollback Plan**:
- Simple git revert (no database, no external state)
- Startup sequence is new feature, no backward compatibility concerns
- Rollback: `git revert <commit-sha>`

---

## [INTEGRATION SCENARIOS]

**From quickstart perspective:**

### Scenario 1: First-Time Setup
```bash
# Clone repository
git clone <repo-url>
cd trading-bot

# Install dependencies
pip install -e .

# Configure credentials
cp .env.example .env
# Edit .env: Set ROBINHOOD_USERNAME and ROBINHOOD_PASSWORD

# Configure trading parameters
cp config.example.json config.json
# Edit config.json: Set trading hours, risk parameters

# Run startup validation
python -m src.trading_bot.main --dry-run

# Expected output:
# ════════════════════════════════════════════════════════════
#          ROBINHOOD TRADING BOT - STARTUP SEQUENCE
# ════════════════════════════════════════════════════════════
# Mode: PAPER TRADING (Simulation - No Real Money)
# ════════════════════════════════════════════════════════════
#
# [✓] Loading configuration...
# [✓] Validating credentials...
# [✓] Initializing logging system...
# [✓] Initializing mode switcher (PAPER mode)...
# [✓] Initializing circuit breakers...
# [✓] Verifying component health...
#
# ════════════════════════════════════════════════════════════
# ✅ STARTUP COMPLETE - Ready to trade
# ════════════════════════════════════════════════════════════
# Current Phase: experience
# Max Trades Today: 999
# Circuit Breaker: Active (Max Loss: 3%, Max Consecutive: 3)
#
# [DRY RUN] Exiting without starting trading loop
```

### Scenario 2: Troubleshooting Failed Startup
```bash
# Run with JSON output for debugging
python -m src.trading_bot.main --json

# Expected output (if credentials missing):
# {
#   "status": "blocked",
#   "errors": ["Missing ROBINHOOD_USERNAME in .env file"],
#   "warnings": [],
#   "components": {
#     "config": {
#       "status": "failed",
#       "errors": ["Missing credentials"]
#     }
#   },
#   "startup_duration_seconds": 0.2,
#   "timestamp": "2025-10-08T14:23:45Z"
# }

# Check startup log for details
cat logs/startup.log

# Fix credentials
nano .env

# Retry startup
python -m src.trading_bot.main --dry-run
```

### Scenario 3: Normal Startup (Paper Trading)
```bash
# Start bot in paper trading mode
python -m src.trading_bot.main

# Startup sequence runs
# Bot waits for trading hours (7:00 AM - 10:00 AM EST)
# Enters main trading loop
# Ctrl+C to stop
```

### Scenario 4: Validation Tests
```bash
# Run unit tests
pytest tests/unit/test_startup.py -v

# Run integration tests
pytest tests/integration/test_startup_flow.py -v

# Run all tests
pytest tests/ -v --cov=src/trading_bot/startup
```

---

## [ERROR SCENARIOS]

**Error 1: Missing .env File**
- **Detection**: Config.from_env_and_json() raises ValueError
- **Display**: `[✗] Validation failed: Missing required credentials`
- **Remediation**: "1. Copy .env.example to .env\n2. Set ROBINHOOD_USERNAME and ROBINHOOD_PASSWORD"
- **Exit Code**: 1 (configuration error)

**Error 2: Invalid config.json**
- **Detection**: json.JSONDecodeError during config load
- **Display**: `[✗] Loading configuration failed: Invalid JSON syntax`
- **Remediation**: "Check config.json for syntax errors (trailing commas, missing quotes)"
- **Exit Code**: 1 (configuration error)

**Error 3: Phase-Mode Conflict**
- **Detection**: ConfigValidator detects mode=live + phase=experience
- **Display**: `[✗] Validation failed: Phase-mode conflict`
- **Remediation**: "1. Change mode to 'paper' in config.json, OR\n2. Advance to 'proof' phase"
- **Exit Code**: 2 (validation error)

**Error 4: Filesystem Permissions**
- **Detection**: OSError when creating logs/ directory
- **Display**: `[✗] Initialization failed: Cannot create logs directory`
- **Remediation**: "Check filesystem permissions: mkdir logs/"
- **Exit Code**: 3 (initialization failure)

**Error 5: Component Initialization Failure**
- **Detection**: Exception during component init (e.g., TradingBot.__init__)
- **Display**: `[✗] Initializing trading bot failed: <error message>`
- **Remediation**: "Check logs/startup.log for details"
- **Exit Code**: 3 (initialization failure)
- **Cleanup**: Call _cleanup_on_failure() to release any resources

---

## [TESTING STRATEGY]

**Unit Tests** (tests/unit/test_startup.py):
- Test each startup step in isolation with mocks
- Test error handling for each failure scenario
- Test cleanup on failure
- Test JSON output formatting
- Test dry-run mode
- Coverage target: >90%

**Test Cases**:
1. `test_successful_startup_paper_mode()` - Happy path with paper trading
2. `test_missing_credentials_error()` - Missing .env file
3. `test_invalid_config_json()` - Malformed JSON
4. `test_phase_mode_conflict()` - Experience + live mode
5. `test_filesystem_permission_error()` - Cannot create directories
6. `test_component_init_failure()` - Component initialization fails
7. `test_dry_run_mode()` - Validation only, no trading loop
8. `test_json_output_format()` - Structured JSON output
9. `test_cleanup_on_failure()` - Graceful cleanup when failed
10. `test_startup_duration_measurement()` - Performance tracking

**Integration Tests** (tests/integration/test_startup_flow.py):
- Test complete startup sequence with real config files
- Test .env.example → .env → successful startup
- Test config.example.json → config.json → successful startup
- Test end-to-end error scenarios (missing files, invalid config)

**Fixtures** (tests/fixtures/):
- `.env.valid` - Valid credentials for testing
- `.env.missing_username` - Missing ROBINHOOD_USERNAME
- `config.valid.json` - Valid configuration
- `config.phase_conflict.json` - mode=live, phase=experience
- `config.invalid.json` - Malformed JSON syntax

**Manual Testing Checklist**:
- [ ] Startup completes in <5 seconds
- [ ] Banner displays correctly with mode indicator
- [ ] All steps show [✓] on success
- [ ] Error messages include remediation steps
- [ ] logs/startup.log created with audit trail
- [ ] --dry-run exits without entering trading loop
- [ ] --json outputs valid JSON
- [ ] Ctrl+C during startup cleans up gracefully
- [ ] Works on Windows, Linux, macOS

---

## [MIGRATION PLAN]

**No migration required** - Startup sequence is a new feature with no database changes.

**User Impact**:
- Users will see new startup banner and progress indicators
- Startup may be slightly slower (~1-2 seconds) due to comprehensive checks
- New command-line flags available: --dry-run, --json
- No breaking changes to existing workflow

**Backward Compatibility**:
- Existing bot.py, config.py, validator.py unchanged (only reused)
- validate_startup.py script remains functional (can be deprecated later)
- Old manual startup method still works (bot.py can be imported and run directly)

---

## [DOCUMENTATION UPDATES]

**README.md**:
- Update "Usage" section with new startup command
- Document --dry-run and --json flags
- Add troubleshooting section referencing logs/startup.log

**CONTRIBUTING.md**:
- Add testing guidelines for startup tests
- Document startup sequence architecture

**CHANGELOG.md**:
- Add entry for startup-sequence feature

**New Documentation**:
- No new docs required - inline code documentation sufficient

---

## [FUTURE ENHANCEMENTS]

**Not in scope for initial implementation, but possible later:**

1. **Interactive Mode**: Prompt user to fix configuration errors instead of exiting
2. **Health Check Dashboard**: Real-time component status in terminal UI (using Rich library)
3. **Startup Metrics**: Track and visualize startup performance over time
4. **Dependency Graph Visualization**: Show component initialization dependencies
5. **Rollback on Failure**: Automatic rollback to last known good configuration
6. **Startup Hooks**: Allow plugins to register custom initialization steps
7. **Remote Monitoring**: Send startup status to monitoring service (e.g., Datadog)
8. **Configuration Wizard**: Interactive first-time setup for new users

These can be added incrementally without breaking existing startup sequence.

---

## [IMPLEMENTATION CHECKLIST]

**Phase 1: Core Infrastructure** (2-3 hours)
- [ ] Create startup.py with dataclasses (StartupStep, StartupResult)
- [ ] Implement StartupOrchestrator class skeleton
- [ ] Implement _display_banner() with mode indicator
- [ ] Implement _load_config() using Config.from_env_and_json()
- [ ] Implement _validate_config() using ConfigValidator

**Phase 2: Component Initialization** (2-3 hours)
- [ ] Implement _initialize_logging() using TradingLogger.setup()
- [ ] Implement _initialize_mode_switcher() using ModeSwitcher
- [ ] Implement _initialize_circuit_breakers() using CircuitBreaker
- [ ] Implement _initialize_bot() using TradingBot
- [ ] Implement _verify_health() to check all components ready

**Phase 3: Display and Output** (1-2 hours)
- [ ] Implement _display_summary() with configuration details
- [ ] Implement _cleanup_on_failure() for graceful shutdown
- [ ] Implement JSON output formatting for --json flag
- [ ] Add startup logger to logger.py

**Phase 4: Entry Point** (1 hour)
- [ ] Create main.py with argparse for --dry-run, --json
- [ ] Implement main() function with exit code handling
- [ ] Test command-line invocation: python -m src.trading_bot.main

**Phase 5: Testing** (3-4 hours)
- [ ] Write unit tests for each startup step
- [ ] Write integration tests for full startup flow
- [ ] Create test fixtures (.env, config.json variants)
- [ ] Test all error scenarios (missing .env, invalid config, etc.)
- [ ] Test dry-run mode
- [ ] Test JSON output mode

**Phase 6: Documentation and Polish** (1-2 hours)
- [ ] Add docstrings to all functions
- [ ] Update README.md with new startup instructions
- [ ] Add error-log.md entry for common startup errors
- [ ] Manual testing on Windows, Linux, macOS
- [ ] Performance testing (ensure <5 second startup)

**Total Estimated Time**: 10-15 hours

---

## [RISKS AND MITIGATIONS]

**Risk 1: Performance Degradation**
- **Risk**: Startup takes >5 seconds on slow hardware
- **Mitigation**: Profile startup sequence, optimize slow steps (e.g., lazy-load imports)
- **Fallback**: Add --quick flag to skip non-critical checks

**Risk 2: Unicode Display Issues**
- **Risk**: Progress indicators (✓, ✗) don't display on some terminals
- **Fallback**: Detect terminal capabilities, use ASCII fallback ([OK], [FAIL])

**Risk 3: Incomplete Cleanup on Failure**
- **Risk**: Component cleanup may leave resources locked (e.g., log file handles)
- **Mitigation**: Implement robust _cleanup_on_failure() with try/except for each component
- **Fallback**: Document manual cleanup steps in logs/startup.log

**Risk 4: Testing Challenges**
- **Risk**: Hard to test filesystem errors, permission issues
- **Mitigation**: Use pytest tmpdir fixture, mock filesystem operations
- **Fallback**: Manual testing on different platforms

---

## [SUCCESS METRICS]

**Quantitative**:
- Startup completes in <5 seconds (95th percentile)
- Test coverage >90% for startup.py
- Zero startup failures in paper trading mode with valid config
- 100% of error scenarios have remediation guidance

**Qualitative**:
- Operators understand startup status from console output
- Error messages are clear and actionable
- logs/startup.log provides sufficient debugging information
- JSON output is machine-parseable and useful for automation

**User Feedback**:
- Survey users after 1 week: "Is startup status clear?" (target: >90% yes)
- Measure time-to-resolution for startup issues (target: <10 minutes)

---

## [APPENDIX: EXISTING VALIDATION LOGIC]

**From validator.py** (reused, not reimplemented):

```python
def validate_all(test_api: bool = False) -> Tuple[bool, List[str], List[str]]:
    """
    Run all validation checks.

    Returns:
        Tuple of (is_valid, errors, warnings)
    """
    # 1. Validate credentials exist (§Security)
    self._validate_credentials()

    # 2. Validate config parameters (§Data_Integrity)
    self._validate_config_parameters()

    # 3. Validate file paths
    self._validate_file_paths()

    # 4. Test API connection (optional, only before live trading)
    if test_api:
        self._test_api_connection()

    is_valid = len(self.errors) == 0
    return is_valid, self.errors, self.warnings
```

**Validation Checks Performed**:
1. .env file exists
2. ROBINHOOD_USERNAME present
3. ROBINHOOD_PASSWORD present
4. ROBINHOOD_MFA_SECRET present (warning if missing)
5. ROBINHOOD_DEVICE_TOKEN present (warning if missing)
6. Config parameters valid (ranges, types)
7. Phase-mode conflict check (experience + live = error)
8. Directories exist or can be created
9. Optional: API connection test (not implemented yet)

**Exit Criteria**:
- `is_valid == True` → Proceed to component initialization
- `is_valid == False` → Display errors, remediation, exit with code 1
