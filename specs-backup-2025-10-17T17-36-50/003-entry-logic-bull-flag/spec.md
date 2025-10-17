# Feature Specification: Bull Flag Pattern Detection

**Feature ID**: 003-entry-logic-bull-flag
**Status**: Draft
**Created**: 2025-10-17
**Last Updated**: 2025-10-17

---

## Overview

Implement bull flag pattern detection logic to identify high-probability entry signals in stock price movements. A bull flag is a continuation pattern where a strong upward price movement (flagpole) is followed by a consolidation period (flag) that leads to a breakout in the direction of the initial trend.

**User Value**: Automates detection of bull flag patterns to generate precise entry signals, reducing manual chart analysis and improving entry timing for momentum trades.

**In Scope**:
- Bull flag pattern detection logic
- Entry signal generation based on pattern characteristics
- Risk/reward parameter calculation
- Integration with existing technical indicators module
- Comprehensive test coverage

**Out of Scope**:
- Bear flag or other chart patterns
- Real-time UI visualization of patterns
- Historical pattern backtesting framework
- Multi-timeframe pattern analysis

---

## User Scenarios

### Scenario 1: Detect Bull Flag Pattern
**Given** a stock has completed a strong upward price movement
**When** the price consolidates in a downward or sideways channel
**And** the consolidation volume decreases relative to the flagpole volume
**Then** the system identifies this as a potential bull flag pattern

### Scenario 2: Confirm Entry Signal
**Given** a bull flag pattern has been detected
**When** the price breaks above the upper boundary of the flag channel
**And** the breakout occurs with increased volume
**And** MACD is positive and price is above VWAP
**Then** the system generates a confirmed entry signal

### Scenario 3: Calculate Risk Parameters
**Given** a confirmed bull flag entry signal
**When** calculating position sizing parameters
**Then** the system calculates stop-loss at the flag's lower boundary
**And** calculates target price based on flagpole height projection
**And** provides risk/reward ratio (minimum 2:1)

### Scenario 4: Reject Invalid Patterns
**Given** a potential consolidation is detected
**When** the consolidation period is too short (less than 3 bars)
**Or** the flagpole gain is insufficient (less than 5%)
**Or** the consolidation retraces more than 50% of the flagpole
**Then** the system does not generate an entry signal

---

## Functional Requirements

### FR-001: Flagpole Detection
**Priority**: P0 (Critical)
**Description**: Detect the initial strong upward price movement (flagpole)

**Acceptance Criteria**:
- System identifies upward price movement with minimum 5% gain
- Flagpole duration is between 3-15 bars
- Volume during flagpole is above 20-bar average volume
- Price closes above starting price of flagpole on final bar

### FR-002: Flag Consolidation Detection
**Priority**: P0 (Critical)
**Description**: Detect the consolidation period following the flagpole

**Acceptance Criteria**:
- System identifies consolidation lasting 3-10 bars
- Consolidation forms downward or sideways channel (retracement 20-50% of flagpole)
- Volume during consolidation decreases by at least 20% compared to flagpole
- Consolidation stays within defined upper/lower boundaries

### FR-003: Breakout Confirmation
**Priority**: P0 (Critical)
**Description**: Confirm breakout above flag resistance to trigger entry signal

**Acceptance Criteria**:
- Price closes above upper boundary of consolidation channel
- Breakout volume exceeds consolidation average volume by 30%
- Price moves at least 1% above resistance within 2 bars
- No false breakout (price doesn't fall back below resistance within 3 bars)

### FR-004: Technical Indicator Validation
**Priority**: P0 (Critical)
**Description**: Validate entry using existing technical indicators

**Acceptance Criteria**:
- MACD is positive at breakout
- Price is above VWAP at breakout
- Price is within 2% of 9-period EMA or above it
- System integrates with TechnicalIndicatorsService without modification

### FR-005: Risk Parameter Calculation
**Priority**: P1 (High)
**Description**: Calculate stop-loss, target price, and risk/reward ratio

**Acceptance Criteria**:
- Stop-loss is set at flag's lower boundary minus 0.5% buffer
- Target price equals breakout price plus flagpole height
- Risk/reward ratio is calculated and must be minimum 2:1
- System rejects signals with risk/reward below 2:1

### FR-006: Pattern Quality Scoring
**Priority**: P1 (High)
**Description**: Assign quality score to detected patterns

**Acceptance Criteria**:
- Scoring considers: flagpole strength, consolidation tightness, volume profile, indicator alignment
- Score ranges from 0-100
- Patterns below score of 60 are flagged as low-quality
- High-quality patterns (80+) are prioritized for entry

### FR-007: Configuration Management
**Priority**: P2 (Medium)
**Description**: Allow configuration of pattern detection parameters

**Acceptance Criteria**:
- Configurable: flagpole minimum gain, consolidation depth, breakout threshold
- Configuration validation prevents invalid parameter combinations
- Default values are provided based on industry standards
- Configuration changes don't require code deployment

---

## Non-Functional Requirements

### NFR-001: Performance
**Description**: Pattern detection executes efficiently for real-time scanning
**Target**: Process 100 stocks for pattern detection in under 5 seconds
**Measure**: Execution time benchmarks in test suite

### NFR-002: Accuracy
**Description**: Pattern detection minimizes false positives
**Target**: False positive rate below 15% based on historical validation
**Measure**: Backtesting accuracy metrics against known patterns

### NFR-003: Maintainability
**Description**: Code follows established project patterns and is well-documented
**Target**: Test coverage above 90% for pattern detection logic
**Measure**: Coverage reports from pytest

### NFR-004: Integration
**Description**: Seamless integration with existing technical indicators module
**Target**: Zero breaking changes to TechnicalIndicatorsService
**Measure**: All existing indicator tests pass after integration

---

## Success Criteria

1. **Pattern Detection Accuracy**: System correctly identifies bull flag patterns with at least 85% true positive rate (validated against manually identified patterns in historical data)

2. **Signal Generation Speed**: Entry signals are generated within 2 seconds of breakout confirmation during live market scanning

3. **Risk Management**: All generated signals include stop-loss and target calculations with minimum 2:1 risk/reward ratio

4. **Test Coverage**: Pattern detection module achieves minimum 90% code coverage with comprehensive unit and integration tests

5. **Integration Success**: System integrates with existing TechnicalIndicatorsService without requiring modifications to indicator calculation logic

---

## Context Strategy

### Data Requirements
- OHLCV bars: Minimum 30 bars of historical data for reliable pattern detection
- Volume data: Required for validating flagpole strength and breakout confirmation
- Technical indicators: VWAP, MACD, EMA (9-period) from existing service

### State Management
- Pattern state tracking: Current phase (scanning, consolidation, breakout)
- Detected patterns cache: Store active patterns with metadata
- Signal history: Track generated signals to prevent duplicates

### Error Handling
- Insufficient data: Return clear error when fewer than 30 bars available
- Invalid configuration: Validate parameters on initialization
- Calculation failures: Log errors and continue to next symbol

---

## Signal Design

### Entry Signal Structure
```
{
  "type": "bull_flag_entry",
  "symbol": "AAPL",
  "timestamp": "2025-10-17T14:30:00Z",
  "pattern_details": {
    "flagpole_gain": 8.5,  // percentage
    "consolidation_bars": 7,
    "breakout_price": 185.50,
    "quality_score": 82
  },
  "risk_parameters": {
    "entry_price": 185.50,
    "stop_loss": 182.25,
    "target_price": 192.00,
    "risk_reward_ratio": 2.0
  },
  "indicators": {
    "vwap": 184.20,
    "macd": 0.45,
    "ema_9": 184.80
  }
}
```

### Signal Validation Rules
- MACD must be positive (> 0)
- Price must be above VWAP
- Breakout volume must exceed consolidation average by 30%
- Risk/reward ratio must be minimum 2:1

---

## Technical Constraints

### Dependencies
- Existing TechnicalIndicatorsService (VWAP, MACD, EMA calculators)
- OHLCV market data source
- Decimal precision for financial calculations

### Performance Considerations
- Pattern detection must be computationally efficient for scanning multiple stocks
- Avoid recalculating indicators already computed by TechnicalIndicatorsService
- Use rolling window calculations to minimize memory usage

### Data Quality Requirements
- Bar data must be complete (no missing OHLCV values)
- Volume data must be non-zero
- Timestamps must be sequential

---

## Integration Points

### TechnicalIndicatorsService Integration
**Interface**: Use existing `TechnicalIndicatorsService` methods
- `get_vwap(bars)`: Validate price above VWAP
- `get_macd(bars)`: Confirm MACD positive
- `get_emas(bars)`: Check price near 9-period EMA

**Integration Pattern**:
- Instantiate TechnicalIndicatorsService in BullFlagDetector
- Pass bars to indicator methods for validation
- No modifications to indicator service required

### Market Data Integration
**Interface**: Receive OHLCV bars from existing data providers
- Format: List of dictionaries with keys: open, high, low, close, volume, timestamp
- Minimum bars: 30 for reliable detection
- Bar interval: 5-minute or 15-minute (configurable)

### Signal Output Integration
**Interface**: Emit signals to existing signal processing pipeline
- Format: Structured signal dictionary (see Signal Design)
- Delivery: Return signal from detection method or emit to queue
- Downstream consumers: Order management, risk management modules

---

## Assumptions

1. **Market Data Quality**: OHLCV data is accurate, complete, and timely
2. **Indicator Accuracy**: Existing TechnicalIndicatorsService provides correct calculations
3. **Volume Reliability**: Volume data is available and reliable for all stocks
4. **Pattern Universality**: Bull flag characteristics are consistent across different stocks and market conditions
5. **Bar Interval**: Default detection uses 5-minute bars unless configured otherwise
6. **Entry Execution**: Generated signals will be acted upon within 1-2 bars after breakout

---

## Open Questions

None. All critical decisions have been made with reasonable defaults based on industry standards and existing codebase patterns.

---

## References

- Existing Technical Indicators: `src/trading_bot/indicators/calculators.py`
- Indicator Service: `src/trading_bot/indicators/service.py`
- Industry Standards: Bull flag patterns typically consolidate 20-50% of flagpole gain
- Risk Management: Minimum 2:1 risk/reward is standard for momentum trades
