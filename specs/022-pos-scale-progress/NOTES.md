# Notes: Position Scaling and Phase Progression

## Research Notes

This file captures research findings, design decisions, and context discovered during planning and implementation.

### Initial Context

- **Feature**: Four-phase progression system (Experience → PoC → Trial → Scaling)
- **Problem**: Need systematic approach to validate trading strategies before scaling position sizes
- **Constitution References**: §Safety_First, §Risk_Management, §Position_Sizing

### Design Decisions

Will be populated during planning phase with:
- Phase transition algorithm design
- Profitability calculation methodology
- Position size scaling formula
- Downgrade trigger logic

### Open Questions

- Should phase progression be per-symbol or account-wide?
- How to handle edge cases (e.g., extended periods without trades)?
- Integration with existing risk_manager.py strategy?

### Technical Considerations

- State persistence in config.json (phase_progression.current_phase)
- JSONL audit logging for phase transitions (logs/phase/)
- Backward compatibility with existing trading logic
- Extend existing Config, ModeSwitcher, PerformanceTracker (57% code reuse)

---

## Phase 1 Summary (Planning)

**Completed**: 2025-10-21

**Research Findings**:
- Found 8 reusable components (Config, ModeSwitcher, PerformanceTracker, CircuitBreaker, MetricsCalculator, TradeQueryHelper, StructuredLogger, QueryHelper)
- Identified 6 new components needed (PhaseManager, validators, trade_limiter, history_logger, models, CLI)
- Code reuse: 57% (8/14 components)
- Integration points: 5 (configuration, performance tracking, validation pipeline, logging, mode switching)

**Key Decisions**:
1. Extend existing phase configuration system (config.py lines 165-166, 221-252, 322-328)
2. Reuse PerformanceTracker for profitability validation (tracker.py get_summary())
3. Extend CircuitBreaker for consecutive loss detection
4. JSONL structured logging following existing patterns
5. Config.json for phase state persistence (no database migration)

**Artifacts Created**:
- research.md (261 lines) - Research decisions and component reuse analysis
- data-model.md (350 lines) - Entity definitions, relationships, JSONL schemas
- quickstart.md (280 lines) - Integration scenarios and testing workflows
- plan.md (450 lines) - Consolidated architecture and implementation plan
- contracts/phase-api.yaml (320 lines) - Python protocol contracts and JSON schemas
- error-log.md (95 lines) - Error tracking template

**Architecture**:
- Stack: Python 3.11+, dataclasses, JSONL files, config.json
- Patterns: Service layer (PhaseManager), Repository (HistoryLogger), Validator pattern
- Dependencies: No new packages (stdlib only)
- Performance: ≤50ms phase validation, ≤200ms metrics calculation

**Next Phase**: `/tasks position-scaling-logic` (generate 20-30 TDD tasks)

---

## Phase 2: Tasks (2025-10-21)

**Summary**:
- Total tasks: 77
- User story tasks: 58 (organized by US1-US6)
- Parallel opportunities: 24 tasks marked [P]
- TDD tasks: 35 tasks marked [TDD]
- MVP scope: 51 tasks (Phases 1-5, US1-US3)

**Task Breakdown**:
- Phase 1 (Setup): 3 tasks
- Phase 2 (Foundational): 13 tasks
- Phase 3 (US1 - Phase System): 22 tasks
- Phase 4 (US2 - Trade Limits): 13 tasks
- Phase 5 (US3 - Profitability): 13 tasks
- Phase 6 (US4 - Position Scaling): 7 tasks
- Phase 7 (US5 - Auto Downgrades): 12 tasks
- Phase 8 (US6 - Export CLI): 11 tasks
- Phase 9 (Polish): 12 tasks

**Checkpoint**:
- ✅ Tasks generated: 77 concrete tasks
- ✅ User story organization: Complete (6 stories)
- ✅ Dependency graph: Created
- ✅ MVP strategy: Defined (US1-US3, 51 tasks)
- ✅ TDD approach: 35 test-first tasks
- 📋 Ready for: /analyze

**Estimated Effort**:
- MVP (US1-US3): ~28 hours (3.5 days)
- Full feature (US1-US6): ~46 hours (5.75 days)

---

*This file is updated throughout the workflow phases.*
