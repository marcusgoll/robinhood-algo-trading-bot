# Momentum Detection Usage Examples

**Feature**: 002-momentum-detection
**Created**: 2025-10-16
**Status**: Draft

## Purpose

This document provides practical code examples and usage patterns for the momentum detection system, including setup, common workflows, and integration scenarios.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Catalyst Detection Examples](#catalyst-detection-examples)
3. [Pre-Market Scanner Examples](#pre-market-scanner-examples)
4. [Bull Flag Detection Examples](#bull-flag-detection-examples)
5. [Composite Signal Examples](#composite-signal-examples)
6. [API Integration Examples](#api-integration-examples)
7. [Testing Examples](#testing-examples)

---

## Quick Start

*To be populated with quick start guide*

**Installation**:
```bash
# Clone repository
git clone <repo-url>
cd stocks-trading-bot

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export NEWS_API_KEY="your-key-here"
export MARKET_DATA_API_KEY="your-alpaca-key"

# Run tests
pytest tests/unit/services/momentum/ -v

# Start bot
python -m trading_bot
```

**Reference**: [plan.md](../plan.md#integration-scenarios) for detailed setup instructions

---

## Catalyst Detection Examples

*To be populated with catalyst detection code examples*

**Example 1: Basic catalyst scan**
```python
from trading_bot.momentum import CatalystDetector

async def scan_for_catalysts():
    detector = CatalystDetector()
    signals = await detector.scan(["AAPL", "GOOGL", "TSLA"])

    for signal in signals:
        print(f"Catalyst found: {signal.symbol}")
        print(f"Type: {signal.metadata['catalyst_type']}")
        print(f"Headline: {signal.metadata['headline']}")
```

**Example 2: Filter by catalyst type**
```python
# Filter for earnings announcements only
earnings_signals = [
    s for s in signals
    if s.metadata['catalyst_type'] == 'earnings'
]
```

**Reference**: [spec.md](../spec.md#user-stories-prioritized) - US1 for catalyst detection requirements

---

## Pre-Market Scanner Examples

*To be populated with pre-market scanner code examples*

**Example 1: Scan pre-market movers**
```python
from trading_bot.momentum import PreMarketScanner

async def scan_premarket():
    scanner = PreMarketScanner()

    # Check if currently in pre-market hours
    if not await scanner.is_premarket_hours():
        print("Not in pre-market hours (4:00-9:30 AM EST)")
        return

    signals = await scanner.scan(["AAPL", "GOOGL", "TSLA"])

    for signal in signals:
        print(f"Pre-market mover: {signal.symbol}")
        print(f"Price change: {signal.metadata['price_change_pct']:.2f}%")
        print(f"Volume ratio: {signal.metadata['volume_ratio']:.2f}x")
```

**Example 2: Filter by magnitude**
```python
# Find stocks with >10% pre-market move
big_movers = [
    s for s in signals
    if s.metadata['price_change_pct'] > 10.0
]
```

**Reference**: [spec.md](../spec.md#user-stories-prioritized) - US2 for pre-market requirements

---

## Bull Flag Detection Examples

*To be populated with bull flag pattern detection examples*

**Example 1: Detect bull flag patterns**
```python
from trading_bot.momentum import BullFlagDetector

async def find_bull_flags():
    detector = BullFlagDetector()
    signals = await detector.scan(["AAPL", "GOOGL", "TSLA"])

    for signal in signals:
        pattern = signal.metadata['pattern']
        print(f"Bull flag detected: {signal.symbol}")
        print(f"Pole gain: {pattern['pole_gain_pct']:.2f}%")
        print(f"Breakout price: ${pattern['breakout_price']:.2f}")
        print(f"Price target: ${pattern['price_target']:.2f}")
```

**Example 2: Calculate risk/reward**
```python
# Calculate potential reward vs risk
for signal in signals:
    pattern = signal.metadata['pattern']
    current_price = pattern['current_price']
    breakout_price = pattern['breakout_price']
    price_target = pattern['price_target']

    risk = breakout_price - current_price
    reward = price_target - breakout_price
    risk_reward_ratio = reward / risk if risk > 0 else 0

    print(f"{signal.symbol}: R/R = {risk_reward_ratio:.2f}")
```

**Reference**: [spec.md](../spec.md#user-stories-prioritized) - US3 for pattern detection requirements

---

## Composite Signal Examples

*To be populated with composite signal ranking examples*

**Example 1: Rank signals by strength**
```python
from trading_bot.momentum import MomentumEngine

async def find_top_opportunities():
    engine = MomentumEngine()

    # Scan all detection methods
    signals = await engine.scan(["AAPL", "GOOGL", "TSLA", "MSFT", "AMZN"])

    # Signals already ranked by composite strength
    top_signals = signals[:5]  # Top 5

    for signal in top_signals:
        print(f"{signal.symbol}: {signal.strength:.1f}/100")
        print(f"Types: {signal.metadata['signal_types']}")
```

**Example 2: Filter multi-signal stocks**
```python
# Find stocks with 3+ confluent signals
strong_signals = [
    s for s in signals
    if len(s.metadata['signal_types']) >= 3
]
```

**Reference**: [spec.md](../spec.md#user-stories-prioritized) - US4 for composite scoring

---

## API Integration Examples

*To be populated with API endpoint usage examples*

**Example 1: Query signals via API**
```python
import requests

# Get high-strength signals from last 24 hours
response = requests.get(
    "http://localhost:8000/api/v1/momentum/signals",
    params={
        "min_strength": 70,
        "limit": 20
    },
    headers={"Authorization": f"Bearer {token}"}
)

signals = response.json()["signals"]
print(f"Found {len(signals)} high-strength signals")
```

**Example 2: Trigger manual scan**
```python
# Start a momentum scan for specific symbols
response = requests.post(
    "http://localhost:8000/api/v1/momentum/scan",
    json={
        "symbols": ["AAPL", "GOOGL", "TSLA"],
        "scan_types": ["catalyst", "premarket", "bull_flag"]
    },
    headers={"Authorization": f"Bearer {token}"}
)

scan_id = response.json()["scan_id"]
print(f"Scan started: {scan_id}")
```

**Reference**: [plan.md](../plan.md#integration-scenarios) for API integration details

---

## Testing Examples

*To be populated with testing code examples*

**Example 1: Unit test for catalyst detector**
```python
import pytest
from trading_bot.momentum import CatalystDetector

@pytest.mark.asyncio
async def test_catalyst_detection():
    detector = CatalystDetector()
    signals = await detector.scan(["AAPL"])

    assert len(signals) >= 0
    for signal in signals:
        assert signal.signal_type == "catalyst"
        assert 0 <= signal.strength <= 100
        assert "catalyst_type" in signal.metadata
```

**Example 2: Integration test for momentum engine**
```python
@pytest.mark.asyncio
async def test_momentum_engine_integration():
    engine = MomentumEngine()
    signals = await engine.scan(["AAPL", "GOOGL"])

    # Verify signals are ranked
    strengths = [s.strength for s in signals]
    assert strengths == sorted(strengths, reverse=True)
```

**Reference**: [plan.md](../plan.md#project-structure) for test file locations

---

## Common Workflows

*To be populated with end-to-end workflow examples*

**Workflow 1: Daily morning scan**
```python
async def morning_momentum_scan():
    """Run daily pre-market momentum scan"""
    engine = MomentumEngine()

    # Define watchlist
    watchlist = ["AAPL", "GOOGL", "TSLA", "MSFT", "AMZN"]

    # Execute scan
    signals = await engine.scan(watchlist)

    # Filter for actionable signals
    actionable = [s for s in signals if s.strength >= 75]

    # Log results
    for signal in actionable:
        print(f"Action: {signal.symbol} - {signal.strength:.1f}/100")
        print(f"Signals: {', '.join(signal.metadata['signal_types'])}")
```

**Workflow 2: Real-time monitoring**
```python
import asyncio

async def monitor_momentum():
    """Continuously monitor for new signals"""
    engine = MomentumEngine()

    while True:
        signals = await engine.scan(watchlist)

        # Alert on new high-strength signals
        for signal in signals:
            if signal.strength >= 80:
                print(f"ALERT: {signal.symbol} - {signal.strength:.1f}/100")

        # Wait 5 minutes before next scan
        await asyncio.sleep(300)
```

**Reference**: [spec.md](../spec.md#user-scenarios) for user scenario context

---

## Related Documentation

- [momentum-architecture.md](./momentum-architecture.md) - System architecture
- [momentum-api.md](./momentum-api.md) - API endpoint reference
- [spec.md](../spec.md) - Feature specification
- [plan.md](../plan.md) - Implementation plan
