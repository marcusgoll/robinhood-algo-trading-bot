# Feature: startup-sequence

## Overview

This feature formalizes the trading bot's startup sequence, transforming the current ad-hoc initialization process into a structured, observable, and safe orchestration workflow.

## Research Findings

### Finding 1: Existing startup validation scattered across multiple files
- **Source**: Code analysis (`validate_startup.py`, `bot.py`, `main.py` would be created)
- **Current State**: Validation exists but not integrated into startup flow
- **Decision**: Consolidate all startup logic into `StartupOrchestrator` class

### Finding 2: Constitution requires §Pre_Deploy validation
- **Source**: `.specify/memory/constitution.md`, README.md references
- **Requirement**: All safety checks must pass before trading begins
- **Implication**: Startup sequence must enforce Constitution rules programmatically

### Finding 3: Mode switcher already handles phase-based restrictions
- **Source**: `src/trading_bot/mode_switcher.py`, README.md documentation
- **Existing**: `ModeSwitcher.can_switch_to_live()` enforces phase rules
- **Integration**: Startup sequence should use existing mode switcher validation

### Finding 4: Logging system already has structured setup
- **Source**: `src/trading_bot/logger.py`, README.md logging section
- **Existing**: `setup_logging()`, `get_logger()`, rotation configured
- **Extension**: Add startup-specific log file (`logs/startup.log`)

### Finding 5: Circuit breaker integrated into bot class
- **Source**: `src/trading_bot/bot.py` (`CircuitBreaker` class)
- **Current**: Initialized within `TradingBot.__init__()`
- **Integration**: Startup sequence should verify circuit breaker activation

## System Components Analysis

**Reusable (existing components)**:
- `Config.from_env_and_json()` - Configuration loading
- `ConfigValidator.validate_all()` - Validation logic
- `ModeSwitcher` - Paper/live mode management
- `TradingBot` - Main bot with circuit breakers
- `setup_logging()` - Logging initialization
- `CircuitBreaker` - Safety system (inside `TradingBot`)

**New Components Needed**:
- `StartupOrchestrator` - Coordinates initialization sequence
- `StartupStep` - Dataclass representing initialization stage
- `main.py` - Entry point with argument parsing (may already exist as stub)

**Rationale**: Leverage existing validated components, add minimal orchestration layer.

## Feature Classification

- UI screens: false (CLI/console output only)
- Improvement: true (improves existing startup process)
- Measurable: false (internal tooling, no user metrics)
- Deployment impact: false (no platform changes, env vars, or migrations)

## Key Decisions

### Decision 1: Create dedicated `startup.py` module
- **Why**: Separation of concerns - keep orchestration logic separate from bot logic
- **Alternative**: Add to `main.py` directly
- **Chosen**: Separate module for testability and clarity

### Decision 2: Fail-fast error handling
- **Why**: Safety-first principle - never partially initialize trading systems
- **Alternative**: Degrade gracefully and continue with limited functionality
- **Chosen**: Fail-fast to prevent trading with incomplete initialization

### Decision 3: Dedicated startup log file
- **Why**: Separate initialization audit trail from trading logs
- **Location**: `logs/startup.log`
- **Alternative**: Reuse `logs/trading_bot.log`
- **Chosen**: Separate file for easier debugging and compliance

### Decision 4: Support `--dry-run` and `--json` flags
- **Why**: Enable automation, testing, and monitoring use cases
- **Use Cases**: CI/CD validation, health checks, config testing
- **Alternative**: Console output only
- **Chosen**: Multi-mode output for flexibility

### Decision 5: Visual progress indicators using Unicode
- **Why**: At-a-glance status during startup (human-readable)
- **Characters**: `[✓]` success, `[✗]` failure, `[⚠]` warning
- **Alternative**: Plain text "OK", "FAIL"
- **Chosen**: Unicode for modern terminal UX

## Implementation Priority

1. **P0 (Must Have)**:
   - `StartupOrchestrator` class with step-by-step execution
   - Error handling and remediation messages
   - Integration with existing `Config`, `ConfigValidator`, `TradingBot`
   - Console output with progress indicators

2. **P1 (Should Have)**:
   - `--dry-run` mode for validation-only
   - Dedicated `logs/startup.log`
   - Startup duration timing and reporting

3. **P2 (Nice to Have)**:
   - `--json` output mode for automation
   - Color-coded output (ANSI colors)
   - Directory creation for missing `logs/`, `data/` dirs

## Testing Checklist

- [ ] Unit tests for `StartupOrchestrator` class
- [ ] Unit tests for each initialization step
- [ ] Integration test: Happy path (valid config, all components initialize)
- [ ] Integration test: Missing `.env` file
- [ ] Integration test: Invalid `config.json`
- [ ] Integration test: Phase-mode conflict (live mode in experience phase)
- [ ] Integration test: Component initialization failure (mocked)
- [ ] Integration test: `--dry-run` mode exits without trading loop
- [ ] Integration test: `--json` output format validation
- [ ] Manual test: Verify console output readability
- [ ] Manual test: Verify `logs/startup.log` content

## Dependencies

### Blocked By
- None (all components exist)

### Blocks
- None (startup sequence enhancement is self-contained)

### Related Features
- Error handling framework (`specs/error-handling-framework/`) - Could integrate startup errors
- Authentication module (`specs/authentication-module/`) - Startup validates auth
- Market data module (`specs/market-data-module/`) - Could add market data checks to startup

## Checkpoints

- Phase 0 (Spec-flow): 2025-10-08
- Phase 1 (Plan): 2025-10-08
- Phase 2 (Tasks): 2025-10-08

## Phase 1 Summary (Plan)

**Research Depth**: 7 key decisions documented
**Architecture Decisions**:
- Dedicated StartupOrchestrator module (orchestrator pattern)
- Fail-fast error handling strategy
- Reuse 6 existing components unchanged
- Create 3 new components (startup.py, main.py, startup.log)
**Components to Reuse**: 6 (Config, ConfigValidator, TradingLogger, ModeSwitcher, CircuitBreaker, TradingBot)
**New Components**: 3 (StartupOrchestrator, main.py entry point, startup logger)
**Migration Needed**: No

**Artifacts Created**:
- plan.md (comprehensive architecture + design)
- contracts/api.yaml (internal API specs for CLI + Python interfaces)
- error-log.md (initialized error tracking)

**Key Architectural Patterns**:
- Orchestrator Pattern: StartupOrchestrator coordinates dependency-ordered initialization
- Dependency Injection: Config instance passed through component chain
- Dataclass State Tracking: StartupStep and StartupResult for observable state
- Fail-Fast Validation: Stop immediately on critical errors, no partial initialization
- Separation of Concerns: Startup logic isolated from trading logic

**Performance Target**: <5 seconds startup time on standard hardware

**Next Phase**: /tasks (generate implementation tasks from plan)

## Phase 2 Summary (Tasks)

**Total Tasks Generated**: 50
**Task Breakdown by TDD Cycle**:
- RED (write failing tests): 17 tasks
- GREEN (implement to pass): 18 tasks
- REFACTOR: 0 tasks
- Parallel (independent): 11 tasks
- Extension (modify existing): 1 task
- Integration (combined): 4 tasks

**Task Categories**:
- Backend (Python): 42 tasks
- Testing (unit + integration): 20 tasks
- Documentation: 4 tasks
- Configuration: 4 tasks

**Implementation Phases**:
1. Phase 3.0: Test Infrastructure Setup (2 tasks)
2. Phase 3.1: Core Data Structures (4 tasks - 2 RED/GREEN pairs)
3. Phase 3.2: Configuration Loading (6 tasks - 3 RED/GREEN pairs)
4. Phase 3.3: Component Initialization (9 tasks - 5 RED/GREEN pairs)
5. Phase 3.4: Display & Output (6 tasks - 3 RED/GREEN pairs)
6. Phase 3.5: Main Orchestration (4 tasks - 2 RED/GREEN pairs)
7. Phase 3.6: Error Handling (4 tasks - 2 RED/GREEN pairs)
8. Phase 3.7: Entry Point & CLI (5 tasks - 2 RED/GREEN pairs + 1 parallel)
9. Phase 3.8: Integration Testing (6 tasks - 3 RED/GREEN pairs)
10. Phase 3.9: Documentation & Polish (4 tasks - all parallel)

**Key Task Decisions**:
- TDD approach enforced: Every feature has RED test first, then GREEN implementation
- Concrete file paths: All tasks specify exact files (no placeholders)
- REUSE markers: 8 existing components identified and referenced in tasks
- Pattern references: Each task references similar existing code
- Dependencies documented: Task ordering follows dependency chain (Config → Logging → Validation → Components → Bot)

**Estimated Duration**: 10-15 hours
- Phases 3.0-3.1: 1 hour (test infrastructure + data structures)
- Phases 3.2-3.3: 4 hours (config loading + component init)
- Phases 3.4-3.5: 2 hours (display + orchestration)
- Phases 3.6-3.7: 2 hours (error handling + CLI)
- Phase 3.8: 3 hours (integration testing)
- Phase 3.9: 1 hour (documentation)

**Artifacts Created**:
- tasks.md (50 concrete implementation tasks with TDD phases)

**Next Phase**: /analyze (cross-artifact consistency check)

## Last Updated

2025-10-08T23:30:00Z
