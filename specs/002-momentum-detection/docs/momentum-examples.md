# Momentum Detection - Usage Examples

Complete guide to using the momentum detection system with concrete, executable examples.

**Feature**: 002-momentum-detection
**Created**: 2025-10-16
**Status**: Production Ready
**Version**: 1.0.0

---

## Table of Contents

1. [Environment Setup](#environment-setup)
2. [CatalystDetector Standalone](#catalystdetector-standalone)
3. [PreMarketScanner Standalone](#premarketscanner-standalone)
4. [BullFlagDetector Standalone](#bullflagdetector-standalone)
5. [Momentum Engine Full Scan](#momentumengine-full-scan)
6. [API Usage (curl examples)](#api-usage-curl-examples)
7. [Troubleshooting](#troubleshooting)

---

## Environment Setup

### Required Environment Variables

Create a `.env` file in your project root:

```bash
# News API for catalyst detection (optional - graceful degradation if missing)
NEWS_API_KEY=your_news_api_key_here

# Market data provider (default: alpaca)
MARKET_DATA_SOURCE=alpaca

# Alpaca API credentials (for market data)
ALPACA_API_KEY=your_alpaca_api_key
ALPACA_SECRET_KEY=your_alpaca_secret_key
ALPACA_BASE_URL=https://paper-api.alpaca.markets

# Database connection (optional, for persistence)
DATABASE_URL=sqlite:///momentum_signals.db

# Logging configuration
LOG_LEVEL=INFO
LOG_DIR=logs
```

### Install Dependencies

```bash
# Using pip
pip install -r requirements.txt

# Or using uv (faster)
uv pip install -r requirements.txt
```

### Verify Setup

```python
from trading_bot.momentum.config import MomentumConfig

# Load configuration from environment
config = MomentumConfig.from_env()

# Verify NEWS_API_KEY is loaded (optional)
if config.news_api_key:
    print("✓ NEWS_API_KEY configured")
else:
    print("⚠ NEWS_API_KEY not set - catalyst detection will be skipped")

# Verify thresholds
print(f"Min catalyst strength: {config.min_catalyst_strength}")
print(f"Min pre-market change: {config.min_premarket_change_pct}%")
print(f"Min volume ratio: {config.min_volume_ratio}%")
print(f"Min pole gain: {config.pole_min_gain_pct}%")
```

---

## CatalystDetector Standalone

Scan breaking news for fundamental events (earnings, FDA approvals, mergers, etc.).

### Basic Usage

```python
import asyncio
from trading_bot.momentum.config import MomentumConfig
from trading_bot.momentum.catalyst_detector import CatalystDetector

async def scan_catalysts():
    # Load configuration
    config = MomentumConfig.from_env()

    # Create detector
    detector = CatalystDetector(config)

    # Scan for catalysts in last 24 hours
    symbols = ["AAPL", "GOOGL", "TSLA", "NVDA", "META"]
    signals = await detector.scan(symbols)

    # Print results
    print(f"Found {len(signals)} catalyst signals:")
    for signal in signals:
        print(f"\n{signal.symbol}:")
        print(f"  Type: {signal.details['catalyst_type']}")
        print(f"  Headline: {signal.details['headline']}")
        print(f"  Strength: {signal.strength:.1f}/100")
        print(f"  Published: {signal.details['published_at']}")
        print(f"  Source: {signal.details['source']}")

# Run async function
asyncio.run(scan_catalysts())
```

### Expected Output

```
Found 2 catalyst signals:

AAPL:
  Type: earnings
  Headline: Apple announces Q4 earnings beat with record iPhone sales
  Strength: 78.5/100
  Published: 2025-10-16T14:30:00Z
  Source: Reuters

NVDA:
  Type: product
  Headline: NVIDIA unveils next-gen AI chip for data centers
  Strength: 68.2/100
  Published: 2025-10-16T16:45:00Z
  Source: Bloomberg
```

### Categorization Examples

The detector uses keyword matching to categorize news:

```python
from trading_bot.momentum.catalyst_detector import CatalystDetector
from trading_bot.momentum.config import MomentumConfig

detector = CatalystDetector(MomentumConfig())

# Test categorization
headlines = [
    "Company announces Q4 earnings beat",  # → EARNINGS
    "FDA approves new cancer drug",         # → FDA
    "Tech giant acquires AI startup",       # → MERGER
    "Apple unveils new iPhone model",       # → PRODUCT
    "Analyst upgrades stock to Buy",        # → ANALYST
]

for headline in headlines:
    catalyst_type = detector.categorize(headline)
    print(f"{headline[:40]:<40} → {catalyst_type.value}")
```

---

## PreMarketScanner Standalone

Identify stocks with significant pre-market price movement (>5%) and unusual volume (>200%).

### Basic Usage

```python
import asyncio
from trading_bot.momentum.config import MomentumConfig
from trading_bot.momentum.premarket_scanner import PreMarketScanner
from trading_bot.market_data.market_data_service import MarketDataService
from trading_bot.auth.alpaca_auth import AlpacaAuth

async def scan_premarket():
    # Setup authentication and services
    auth = AlpacaAuth()
    config = MomentumConfig.from_env()
    market_data = MarketDataService(auth, config)

    # Create scanner
    scanner = PreMarketScanner(config, market_data)

    # Check if in pre-market hours (4:00-9:30 AM EST)
    if not scanner.is_premarket_hours():
        print("⚠ Not in pre-market hours (4:00-9:30 AM EST)")
        print("Scanner will return empty results")

    # Scan for pre-market movers
    symbols = ["AAPL", "TSLA", "NVDA", "AMD", "META"]
    signals = await scanner.scan(symbols)

    # Print results
    print(f"\nFound {len(signals)} pre-market movers:")
    for signal in signals:
        print(f"\n{signal.symbol}:")
        print(f"  Change: {signal.details['change_pct']:+.2f}%")
        print(f"  Volume Ratio: {signal.details['volume_ratio']:.1f}x")
        print(f"  Current Price: ${signal.details['current_price']:.2f}")
        print(f"  Previous Close: ${signal.details['previous_close']:.2f}")
        print(f"  Strength: {signal.strength:.1f}/100")
        print(f"  Detected: {signal.details['timestamp_est']}")

# Run async function
asyncio.run(scan_premarket())
```

### Expected Output (During Pre-Market Hours)

```
Found 2 pre-market movers:

TSLA:
  Change: +7.35%
  Volume Ratio: 3.2x
  Current Price: $245.80
  Previous Close: $229.00
  Strength: 72.4/100
  Detected: 2025-10-16 08:15:00 EDT

NVDA:
  Change: -5.82%
  Volume Ratio: 2.8x
  Current Price: $485.20
  Previous Close: $515.00
  Strength: 65.1/100
  Detected: 2025-10-16 08:15:00 EDT
```

---

## BullFlagDetector Standalone

Scan stocks for bull flag chart patterns (strong upward move followed by consolidation).

### Basic Usage

```python
import asyncio
from trading_bot.momentum.config import MomentumConfig
from trading_bot.momentum.bull_flag_detector import BullFlagDetector
from trading_bot.market_data.market_data_service import MarketDataService
from trading_bot.auth.alpaca_auth import AlpacaAuth

async def scan_bull_flags():
    # Setup authentication and services
    auth = AlpacaAuth()
    config = MomentumConfig.from_env()
    market_data = MarketDataService(auth, config)

    # Create detector
    detector = BullFlagDetector(config, market_data)

    # Scan for bull flag patterns (uses 100 days of historical data)
    symbols = ["AAPL", "TSLA", "NVDA", "AMD", "META"]
    signals = await detector.scan(symbols)

    # Print results
    print(f"Found {len(signals)} bull flag patterns:")
    for signal in signals:
        print(f"\n{signal.symbol}:")
        print(f"  Pole Gain: {signal.details['pole_gain_pct']:.2f}%")
        print(f"  Flag Range: {signal.details['flag_range_pct']:.2f}%")
        print(f"  Breakout Price: ${signal.details['breakout_price']:.2f}")
        print(f"  Price Target: ${signal.details['price_target']:.2f}")
        upside = ((signal.details['price_target'] / signal.details['breakout_price']) - 1) * 100
        print(f"  Potential Gain: {upside:.1f}%")
        print(f"  Strength: {signal.strength:.1f}/100")

# Run async function
asyncio.run(scan_bull_flags())
```

---

## MomentumEngine Full Scan

Unified interface to run all detectors.

### Basic Usage

```python
import asyncio
from trading_bot.momentum.config import MomentumConfig
from trading_bot.momentum.engine import MomentumEngine
from trading_bot.market_data.market_data_service import MarketDataService
from trading_bot.auth.alpaca_auth import AlpacaAuth

async def full_momentum_scan():
    # Setup authentication and services
    auth = AlpacaAuth()
    config = MomentumConfig.from_env()
    market_data = MarketDataService(auth, config)

    # Create engine (initializes all detectors)
    engine = MomentumEngine(config, market_data)

    # Run full scan across all detectors
    symbols = ["AAPL", "TSLA", "NVDA", "AMD", "META", "GOOGL", "MSFT", "AMZN"]
    all_signals = await engine.scan(symbols)

    # Group signals by type
    signals_by_type = {
        "CATALYST": [],
        "PREMARKET": [],
        "PATTERN": [],
    }

    for signal in all_signals:
        signals_by_type[signal.signal_type.value].append(signal)

    # Print summary
    print(f"\n=== Momentum Scan Results ===")
    print(f"Total Signals: {len(all_signals)}")
    print(f"  Catalysts: {len(signals_by_type['CATALYST'])}")
    print(f"  Pre-Market Movers: {len(signals_by_type['PREMARKET'])}")
    print(f"  Bull Flag Patterns: {len(signals_by_type['PATTERN'])}")

    # Print top signals by strength
    print(f"\n=== Top 5 Signals by Strength ===")
    top_signals = sorted(all_signals, key=lambda s: s.strength, reverse=True)[:5]

    for i, signal in enumerate(top_signals, 1):
        print(f"\n{i}. {signal.symbol} - {signal.signal_type.value}")
        print(f"   Strength: {signal.strength:.1f}/100")

# Run async function
asyncio.run(full_momentum_scan())
```

---

## API Usage (curl examples)

If you have the FastAPI backend running, you can use the REST API.

### Start API Server

```bash
# From api/ directory
cd api
uvicorn app.main:app --reload --port 8000
```

### Scan All Momentum Signals

```bash
# POST request with symbols in body
curl -X POST http://localhost:8000/api/v1/momentum/scan \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["AAPL", "TSLA", "NVDA", "AMD", "META"]
  }' | jq
```

### Health Check

```bash
# Check API health
curl http://localhost:8000/api/v1/health/healthz | jq
```

---

## Troubleshooting

### Issue: "NEWS_API_KEY not configured" warning

**Solution**: This is graceful degradation - other detectors will still run.

```bash
# Set NEWS_API_KEY in .env file
echo "NEWS_API_KEY=your_key_here" >> .env
```

### Issue: "Invalid symbol format: 'aapl': must be uppercase"

**Solution**: Always use uppercase symbols

```python
# Correct
symbols = ["AAPL", "GOOGL", "TSLA"]

# Incorrect - raises ValueError
symbols = ["aapl", "googl", "tsla"]
```

---

**Last Updated**: 2025-10-16
**Version**: 1.0.0
**Feature**: momentum-detection (002)
