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

- State persistence in phase_state.json
- JSONL audit logging for phase transitions
- Backward compatibility with existing trading logic

---

*This file will be updated throughout the workflow phases.*
