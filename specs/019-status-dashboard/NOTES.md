# Feature: status-dashboard

## Overview
CLI status dashboard for displaying trading performance metrics and current positions in real-time.

**From Roadmap**: Yes
**Roadmap Context**:
- Title: CLI status dashboard & performance metrics
- Area: infra
- Role: all
- Dependencies: account-data-module, performance-tracking, trade-logging

## Research Findings

### Finding 1: Existing Implementation
**Source**: Codebase grep for dashboard code
**Discovery**: Full dashboard implementation already exists at `src/trading_bot/dashboard/`:
- dashboard.py - Live refresh loop with command controls (R/E/H/Q)
- display_renderer.py - Rich library terminal rendering
- metrics_calculator.py - Performance statistics (win rate, R:R, streaks)
- data_provider.py - Account data + trade log aggregation
- export_generator.py - JSON/MD export functionality
- models.py - DashboardSnapshot, DashboardTargets data models
**Decision**: New spec will document existing implementation and identify any gaps from roadmap requirements

### Finding 2: Existing Specification
**Source**: specs/status-dashboard/spec.md
**Discovery**: Comprehensive spec already exists (created 2025-10-09) covering:
- Complete HEART metrics framework
- 16 functional requirements (FR-001 to FR-016)
- 8 non-functional requirements (NFR-001 to NFR-008)
- Hypothesis with quantified predictions (-96% time reduction)
- Target comparison feature with color coding
**Decision**: This iteration will validate completeness against roadmap and update if needed

### Finding 3: Constitution Constraints
**Source**: .spec-flow/memory/constitution.md
**Key Principles Applied**:
- §Code_Quality: Type hints required, ≥90% test coverage, KISS, DRY
- §Safety_First: Audit everything (log all exports), fail safe not fail open
- §Data_Integrity: All timestamps UTC, validate data completeness
- §Testing_Requirements: Unit tests, integration tests required
**Implication**: Spec must emphasize testing and error handling

### Finding 4: Performance Tracking Dependency
**Source**: specs/performance-tracking/spec.md
**Discovery**: Performance tracking module provides:
- TradeQueryHelper for log parsing
- MetricsCalculator for win rate, R:R, streaks
- Automated daily/weekly/monthly summaries
- Alert system for target breaches
**Decision**: Dashboard leverages these components (confirmed by roadmap dependencies)

## Feature Classification
- UI screens: false (CLI interface, not web UI)
- Improvement: false (new feature)
- Measurable: true (displays performance metrics)
- Deployment impact: false (no schema changes or breaking changes)

## System Components Analysis
[Populated during system component check]

## Checkpoints
- Phase 0 (Spec-flow): 2025-10-19

## Last Updated
2025-10-19T17:30:00Z
