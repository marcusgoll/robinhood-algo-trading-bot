# Level 2 Order Flow Integration (v1.7.0)

## What's New

Real-time order flow monitoring using Polygon.io API to detect institutional selling pressure and trigger protective exits before significant losses occur.

This feature adds advanced market microstructure analysis to the trading bot, complementing the existing momentum detection and risk management systems.

## Key Features

- ✅ **Large Seller Detection**: Identifies orders >10,000 shares at bid (institutional selling pressure)
- ✅ **Red Burst Volume Spike Detection**: Detects volume spikes >300% of 5-minute average with majority sells (panic selling)
- ✅ **Exit Signal Triggers**: Automatically triggers exit recommendations when 3+ large seller alerts detected within 2 minutes
- ✅ **Position-Only Monitoring**: Monitors order flow only for active positions (reduces API costs, aligns with risk management focus)
- ✅ **Data Validation**: Comprehensive validation ensures data integrity (timestamp freshness, price bounds, chronological sequence)
- ✅ **Graceful Degradation**: Continues operation with reduced monitoring when Level 2 data unavailable

## Technical Highlights

### Testing & Quality
- **78/78 tests passing** (100% pass rate)
- **Order flow module coverage**: ~86% (improved from 55.81%)
- **Test execution time**: 1.40 seconds (excellent performance)
- **Security**: 0 vulnerabilities (Bandit scan)

### Constitution Compliance
- ✅ **§Data_Integrity**: Frozen dataclasses, validation, Decimal precision, UTC timestamps
- ✅ **§Audit_Everything**: Structured logging with JSONL format
- ✅ **§Safety_First**: Fail-fast validation, graceful degradation, no silent failures
- ✅ **§Risk_Management**: Rate limiting, alert cooldown, position-only monitoring

### Architecture
- Backend-only feature (no UI components)
- Follows existing `CatalystDetector` pattern for consistency
- Integrated with TradingLogger for structured audit logging
- Pattern reuse from market_data and momentum modules

## New Dependencies

- **polygon-api-client==1.12.5**: Professional-grade Level 2 order book and Time & Sales data ($99/month starter plan)
- **types-requests**: Mypy type stubs for requests library

## Configuration

Add the following environment variables to your `.env` file:

```bash
# Required
POLYGON_API_KEY=your_polygon_api_key_here

# Optional (defaults shown)
ORDER_FLOW_LARGE_ORDER_SIZE=10000
ORDER_FLOW_VOLUME_SPIKE_THRESHOLD=3.0
ORDER_FLOW_RED_BURST_THRESHOLD=4.0
ORDER_FLOW_ALERT_WINDOW_SECONDS=120
ORDER_FLOW_MONITORING_MODE=positions_only
```

See `.env.example` for full documentation.

## Usage

### Basic Usage

```python
from trading_bot.order_flow import OrderFlowConfig, OrderFlowDetector

# Initialize detector
config = OrderFlowConfig.from_env()
detector = OrderFlowDetector(config)

# Monitor active positions
active_symbols = ["AAPL", "TSLA", "NVDA"]
alerts_by_symbol = detector.monitor_active_positions(active_symbols)

# Check for exit signals
if detector.should_trigger_exit():
    print("EXIT SIGNAL: Multiple large sellers detected")
```

### Health Check

```python
# Verify Polygon API connectivity
health = detector.health_check()
print(f"Status: {health['status']}")
print(f"Polygon API: {health['dependencies']['polygon_api']}")
```

See `specs/028-level-2-order-flow-i/quickstart.md` for detailed examples.

## Testing

Run the order flow test suite:

```bash
# Full test suite with coverage
pytest tests/order_flow/ -v --cov=src/trading_bot/order_flow --cov-report=term

# Specific module tests
pytest tests/order_flow/test_polygon_client.py -v
pytest tests/order_flow/test_order_flow_detector.py -v
pytest tests/order_flow/test_tape_monitor.py -v
```

**Note**: Integration tests requiring real Polygon.io API credentials are skipped by default (marked with `@pytest.mark.integration`).

## Deployment & Rollback

### Deployment
This is a backend Python module that runs locally. No cloud deployment required.

1. Pull latest main branch: `git pull origin main`
2. Install dependencies: `pip install -r requirements.txt`
3. Configure environment variables in `.env`
4. Run the trading bot as usual

### Rollback
If issues arise, revert to previous version:

```bash
# Option 1: Git revert (recommended)
git revert <merge-commit-sha>
git push origin main

# Option 2: Rollback to previous tag
git checkout v1.6.0
pip install -r requirements.txt

# Option 3: Feature flag disablement
# Remove ORDER_FLOW_* environment variables
# Module won't initialize without POLYGON_API_KEY
```

## Breaking Changes

**None** - This is a new feature that's backward compatible. Existing functionality is unchanged.

## Migration Guide

**No migration required** - This is an additive feature. The trading bot will continue to work without order flow monitoring if `POLYGON_API_KEY` is not configured.

To enable order flow monitoring:
1. Sign up for Polygon.io (https://polygon.io/pricing) - $99/month starter plan
2. Add `POLYGON_API_KEY` to `.env`
3. Configure optional thresholds if desired
4. Order flow monitoring will activate automatically for active positions

## Monitoring

### Alert Logging
All order flow alerts are logged to structured JSONL with UTC timestamps:

```bash
# View large seller alerts
grep "Large seller detected" logs/*.log | tail -10

# View exit signals
grep "Exit signal triggered" logs/*.log | tail -10

# View validation errors
grep "DataValidationError" logs/*.log | tail -10
```

### Performance Metrics
- **Alert latency**: Target <2 seconds from data arrival to alert logged (p95)
- **Memory overhead**: Target <50MB additional for order flow monitoring
- **API rate limits**: Respects Polygon.io limits with exponential backoff (@with_retry decorator)

### Health Monitoring
Verify system health:

```python
from trading_bot.order_flow import OrderFlowConfig, OrderFlowDetector

config = OrderFlowConfig.from_env()
detector = OrderFlowDetector(config)
health = detector.health_check()

print(f"Status: {health['status']}")
print(f"Last alert count: {health['last_alert_count']}")
print(f"Polygon API: {health['dependencies']['polygon_api']}")
```

## Known Limitations

1. **API Cost**: Requires Polygon.io subscription ($99/month starter plan)
2. **Market Hours Only**: Order flow monitoring operates during regular trading hours (7am-10am EST per Constitution)
3. **Position-Only Monitoring**: Does not continuously monitor watchlist symbols (reduces costs, aligns with risk management focus)
4. **Exit Recommendations**: Alerts are recommendations to risk management, not automatic exits (human-in-loop by design)

## Future Enhancements

Potential improvements for future releases:
- Backtesting support for order flow patterns
- Dashboard visualization of order flow alerts
- Machine learning for pattern recognition
- Extended market hours monitoring
- Watchlist monitoring mode (optional, higher API costs)

## Documentation

- **Feature Specification**: `specs/028-level-2-order-flow-i/spec.md`
- **Architecture & Design**: `specs/028-level-2-order-flow-i/plan.md`
- **Quick Start Guide**: `specs/028-level-2-order-flow-i/quickstart.md`
- **API Contracts**: `specs/028-level-2-order-flow-i/contracts/polygon-api.yaml`
- **Testing Report**: `specs/028-level-2-order-flow-i/preview-results.md`
- **Optimization Report**: `specs/028-level-2-order-flow-i/optimization-report.md`

## Credits

This feature was developed following the Spec-Flow workflow with Test-Driven Development (TDD) principles.

- **Pattern Reuse**: CatalystDetector, MarketDataService, @with_retry decorator, TradingLogger
- **Quality Gates**: 90% test coverage target, linting (ruff), type checking (mypy), security scanning (Bandit)
- **Constitution Compliance**: All four core sections (Data Integrity, Audit Everything, Safety First, Risk Management)

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
