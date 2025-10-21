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
- ✅ Ready for: /implement

**Estimated Effort**:
- MVP (US1-US3): ~28 hours (3.5 days)
- Full feature (US1-US6): ~46 hours (5.75 days)

---

## Phase 3: Cross-Artifact Validation (2025-10-21)

**Summary**:
- Artifacts validated: 6 (spec.md, plan.md, tasks.md, data-model.md, contracts/phase-api.yaml, error-log.md)
- Validation passes: 11/11
- Critical issues: 0
- Warnings: 3 (medium severity)
- Status: ✅ READY FOR IMPLEMENTATION

**Key Findings**:
- ✅ Constitution compliance: §Safety_First, §Risk_Management, §Code_Quality, §Audit_Everything
- ✅ 100% requirement coverage: All 8 FRs mapped to tasks
- ✅ TDD ordering enforced: 35 test-first tasks follow RED-GREEN-REFACTOR
- ✅ Code reuse validated: 57% reuse (8 existing components)
- ⚠️ Minor fixes needed: 3 warnings (emergency exits, JSONL atomic write, validator integration)

**Validation Results**:
1. Constitution Alignment: ✅ All 4 sections aligned
2. Coverage Gap Analysis: ✅ 100% FR coverage, 100% US coverage
3. Duplication Detection: ✅ No duplications (pattern reuse intentional)
4. Ambiguity Detection: ⚠️ "Emergency exits" needs definition in T076
5. Underspecification Check: ⚠️ JSONL corruption recovery needed in T056
6. Inconsistency Detection: ✅ No inconsistencies (spec ↔ plan ↔ tasks aligned)
7. Breaking Change Analysis: ⚠️ Validator pipeline integration (T165) requires test
8. TDD Ordering Validation: ✅ All phases follow test-first approach
9. Dependency Analysis: ✅ Critical path clear, 24 parallel tasks identified
10. Risk Assessment: ⚠️ Medium risk (JSONL atomic write, timezone issues)
11. Constitution References: ✅ Full alignment across artifacts

**Warnings to Address**:
1. **T076**: Define emergency exit flag (e.g., `emergency=True` parameter)
2. **T056**: Add atomic write logic (write to temp file, rename on success)
3. **T165**: Add backward compatibility test for validator integration

**Artifact Created**:
- analysis-report.md (680 lines) - Detailed validation findings

**Checkpoint**:
- ✅ Artifacts consistent: spec ↔ plan ↔ tasks aligned
- ✅ Constitution compliance: All sections validated
- ✅ Coverage complete: 100% FR and US coverage
- ⚠️ Minor fixes: 3 warnings documented
- ✅ Ready for: /implement

**Recommendation**: Proceed to implementation with 3 minor task updates (emergency exits, atomic write, integration test).

---

*This file is updated throughout the workflow phases.*
