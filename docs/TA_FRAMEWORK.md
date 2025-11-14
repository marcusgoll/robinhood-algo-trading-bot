```markdown
# Technical Analysis Framework

**"Informed and educated, not astrology with candles."**

A comprehensive technical analysis framework implementing 20 proven tools and concepts that actually work for stocks and crypto. Every signal is quantifiable, backtestable, and comes with proper risk management.

## Philosophy

1. **Specification first** — No trade without clear entry, stop, and target
2. **Quantifiable** — Every indicator can be measured and backtested
3. **Risk-first** — Position sizing and R-multiples calculated for every trade
4. **Regime-aware** — Different strategies for trending vs ranging markets
5. **Feedback-driven** — Track what works via journaling and performance review

No feelings. No hunches. Just math.

---

## The 20 Technical Tools

### **Trend & Structure (Core - Non-negotiable)**

#### 1. Multi-Timeframe Trend Analysis
- **What**: Check trend on higher TF (daily/weekly) before trading lower TF (1h/15m)
- **How**: Only long when higher TF trend is up, short when down
- **File**: `market_structure.py` → `MultiTimeframeAnalyzer`

#### 2. Market Structure (HH/HL / LH/LL)
- **What**: Price swing patterns that define trend
- **How**: Enter in direction of structure after pullbacks. Exit when structure breaks
- **File**: `market_structure.py` → `MarketStructureAnalyzer`

#### 3. Support & Resistance (S/R Zones)
- **What**: Price regions where buyers/sellers consistently react
- **How**: Look for confluence: S/R + trend + volume shift
- **File**: `enhanced_indicators.py` → Part of pattern detection

#### 4. Breakout vs. Mean Reversion Context
- **What**: Two different market regimes requiring different strategies
- **How**: Don't run mean-reversion in trending markets. Don't chase breakouts in choppy markets
- **File**: `regime_detector.py` → `RegimeDetector`

---

### **Indicators (Useful if you don't worship them)**

#### 5. Moving Averages (EMA/SMA)
- **What**: Smoothed price over time
- **How**: 20/50/200 EMA/SMA as dynamic S/R and trend filters
- **File**: `enhanced_indicators.py` → `calculate_moving_averages()`

#### 6. RSI (Relative Strength Index)
- **What**: Oscillator of momentum (0–100)
- **How**: Above 50 = bullish bias. Use divergence as warning, not instant reversal
- **File**: `enhanced_indicators.py` → `calculate_rsi()`

#### 7. MACD
- **What**: Trend + momentum indicator from EMAs
- **How**: Look for MACD line crossing signal line in direction of higher-TF trend
- **File**: `enhanced_indicators.py` → `calculate_macd()`

#### 8. Stochastic / Stoch RSI
- **What**: Overbought/oversold oscillator
- **How**: Better in ranging markets: buy oversold near support, sell overbought near resistance
- **File**: `enhanced_indicators.py` → `calculate_stochastic()`

#### 9. ATR (Average True Range)
- **What**: Measures volatility
- **How**: Position sizing (smaller size when ATR high), stop placement (1.5-3 × ATR)
- **File**: `enhanced_indicators.py` → `calculate_atr()`

#### 10. Bollinger Bands
- **What**: Moving average with upper/lower bands based on volatility
- **How**: Squeezes often precede large moves. In ranges, fade band extremes
- **File**: `enhanced_indicators.py` → `calculate_bollinger_bands()`

---

### **Volume & Order Flow**

#### 11. Raw Volume & Volume Spikes
- **What**: How much is trading
- **How**: Breakouts with rising volume are better than low-volume "fake" ones
- **File**: `enhanced_indicators.py` → `calculate_volume()`

#### 12. OBV (On-Balance Volume)
- **What**: Cumulative volume flow
- **How**: If price flat but OBV climbing = stealth accumulation
- **File**: `enhanced_indicators.py` → `calculate_obv()`

#### 13. Volume Profile / Market Profile
- **What**: Shows traded volume at different price levels
- **How**: High-volume nodes = acceptance zones; low-volume zones = rejection areas
- **File**: `enhanced_indicators.py` → `calculate_volume_profile()`

---

### **Pattern & Price Behavior**

#### 14. Consolidation & Breakout Patterns
- **What**: Tight ranges, flags, triangles before expansion
- **How**: Trade breakouts with trend & volume confirmation
- **File**: `pattern_detector.py` → `detect_consolidation()`, `detect_breakout()`

#### 15. Pullback Entries (Fibs / MA pullbacks / Prior S/R)
- **What**: Entering after a move, not at the initial breakout
- **How**: In uptrend, buy pullbacks into prior resistance → support, MA zones, or fib 38-61% areas
- **File**: `pattern_detector.py` → `detect_pullback()`

#### 16. Gaps (Stocks) / Imbalances (Crypto)
- **What**: Price jumps leaving untraded areas
- **How**: Gaps often act as magnets / S/R
- **File**: `pattern_detector.py` → `detect_gaps()`

---

### **Risk, Stats & System Edge (Where grown-ups live)**

#### 17. R-Multiple / Risk-Reward Ratio
- **What**: Reward compared to your risk per trade (R)
- **How**: Aim for at least 2R average reward if win rate ~40-50%
- **File**: `risk_calculator.py` → `calculate_risk_reward()`

#### 18. Position Sizing & Max Risk Per Trade
- **What**: How much you put on, based on account size and stop distance
- **How**: Risk 0.25-1% of equity per trade. Let volatility (ATR) influence position size
- **File**: `risk_calculator.py` → `calculate_position_size()`

#### 19. Backtesting & Forward-Testing
- **What**: Validate your rules on historical data, then in live/sim
- **How**: Code your rules and backtest over multiple market regimes
- **File**: `trading_journal.py` → `TradingJournal` (performance tracking)

#### 20. Trading Journal & Performance Review
- **What**: Logging trades, screenshots, reasons, emotions, outcomes
- **How**: Track setup type, R-multiple, adherence to rules, market context
- **File**: `trading_journal.py` → `TradingJournal`

---

## Quick Start

### Installation

```bash
# The framework is already part of the trading bot
cd /home/user/robinhood-algo-trading-bot

# Install dependencies (if not already installed)
pip install -r requirements.txt
```

### Basic Usage

```python
from trading_bot.technical_analysis import TACoordinator
import pandas as pd

# Initialize coordinator
ta = TACoordinator(
    account_size=10000,    # Your account size
    risk_per_trade=1.0,    # Risk 1% per trade
    min_confidence=60.0,   # Minimum confidence for signals
    min_r_multiple=2.0     # Minimum 2:1 risk-reward
)

# Analyze a symbol (assuming you have OHLCV data)
signal = ta.analyze_simple(
    symbol='BTCUSD',
    df=df  # pandas DataFrame with OHLCV data
)

# Print the signal
ta.print_signal(signal)

# Use the signal
if signal.signal == 'LONG' and signal.quality_score > 70:
    print(f"TAKE TRADE:")
    print(f"  Entry: ${signal.entry_price}")
    print(f"  Stop: ${signal.stop_loss}")
    print(f"  Target: ${signal.take_profit}")
    print(f"  Position Size: {signal.position_size_shares} shares")
    print(f"  Risk: ${signal.risk_amount_usd} ({signal.risk_pct_of_account}%)")
```

### Multi-Timeframe Analysis

```python
from trading_bot.technical_analysis import TACoordinator

ta = TACoordinator(account_size=10000)

# Analyze across multiple timeframes
signal = ta.analyze(
    symbol='BTCUSD',
    data={
        '15m': df_15m,  # DataFrames for each timeframe
        '1h': df_1h,
        '4h': df_4h,
        '1d': df_1d
    },
    primary_timeframe='1h'  # Use 1h for entry/exit
)

ta.print_signal(signal)
```

### Using Individual Components

```python
from trading_bot.technical_analysis import (
    EnhancedIndicators,
    MarketStructureAnalyzer,
    RegimeDetector,
    RiskCalculator
)

# 1. Calculate indicators
indicators = EnhancedIndicators()
ma_result = indicators.calculate_moving_averages(df)
rsi_result = indicators.calculate_rsi(df)
atr_result = indicators.calculate_atr(df)

# 2. Analyze market structure
structure = MarketStructureAnalyzer()
structure_result = structure.analyze(df)

# 3. Detect regime
regime = RegimeDetector()
regime_result = regime.detect(df)

# 4. Calculate position size
risk_calc = RiskCalculator()
position = risk_calc.calculate_position_size(
    account_size=10000,
    entry_price=50000,
    stop_loss=49000,
    direction='long',
    atr=500
)
```

### Trading Journal

```python
from trading_bot.technical_analysis import TradingJournal

# Initialize journal
journal = TradingJournal(
    journal_path='./trading_journal.json',
    equity_start=10000.0
)

# Log trade entry
journal.log_trade_entry(
    trade_id='TRADE_001',
    symbol='BTCUSD',
    direction='long',
    entry_price=50000,
    stop_loss=49000,
    take_profit=52000,
    position_size=0.1,
    setup_type='breakout',
    market_regime='trending',
    notes='Clean breakout above resistance with volume'
)

# Log trade exit
journal.log_trade_exit(
    trade_id='TRADE_001',
    exit_price=52000,
    followed_rules=True,
    notes='Target hit'
)

# Generate performance report
print(journal.generate_review_report())
```

---

## Architecture

```
technical_analysis/
├── __init__.py                  # Main exports
├── enhanced_indicators.py       # All indicators (Tools 5-13)
├── market_structure.py          # Structure & MTF analysis (Tools 1-2)
├── regime_detector.py           # Breakout vs mean reversion (Tool 4)
├── pattern_detector.py          # Chart patterns (Tools 14-16)
├── volume_analysis.py           # Advanced volume analysis (Tools 11-13)
├── risk_calculator.py           # Risk/position sizing (Tools 17-18)
├── ta_coordinator.py            # Main orchestrator
└── trading_journal.py           # Backtesting & journal (Tools 19-20)
```

---

## Signal Structure

Every signal from `TACoordinator` contains:

```python
TASignal(
    # Identification
    symbol='BTCUSD',
    timestamp=Timestamp('2025-01-14 12:00:00'),

    # Signal
    signal='LONG',           # LONG, SHORT, HOLD, SKIP
    confidence=75.5,         # 0-100

    # Entry & Exit
    entry_price=50000.0,
    stop_loss=49000.0,
    take_profit=52000.0,

    # Position Sizing
    position_size_shares=0.102,
    position_size_usd=5100.0,
    risk_amount_usd=100.0,   # 1% of $10k account
    reward_amount_usd=200.0,

    # Risk Metrics
    r_multiple=2.0,          # 2:1 risk-reward
    risk_pct_of_account=1.0, # 1% risk
    quality_score=82.0,      # 0-100 overall quality

    # Analysis
    trend='bullish',
    structure='HH/HL',
    regime='breakout',
    pattern='flag',

    # Indicators
    rsi=65.2,
    macd_signal='bullish',
    volume_confirmation=True,

    # Reasoning
    bullish_factors=[
        'Multi-TF trend bullish (confidence: 80%)',
        'Market structure: HH/HL',
        'MA alignment bullish',
        'MACD bullish cross'
    ],
    bearish_factors=[],
    warnings=[],
    reasoning='Trend: BULLISH | Structure: HH/HL | Regime: breakout | ...'
)
```

---

## Practical Action Plan

### 1. Pick a Lane

Choose ONE strategy type:
- **Trend-following swing** (daily/4h)
- **Intraday scalping** (1h/15m) - NOT recommended for beginners
- **Mean-reversion in ranges**

### 2. Choose a Small Toolkit

Example trend swing set:
- Multi-TF trend & structure (Tools 1, 2)
- S/R zones (Tool 3)
- EMAs + RSI (Tools 5, 6)
- ATR for stops/sizing (Tool 9, 18)
- Volume & breakouts (Tools 11, 14)

### 3. Write Hard Rules

Create EXACT entry triggers:
```python
# Example: Trend-following long setup
ENTRY_RULES = {
    'higher_tf_trend': 'bullish',      # Daily uptrend
    'structure': 'HH/HL',              # Making higher highs
    'pullback_to_ema': True,           # Pullback to 20 EMA
    'rsi_above': 50,                   # RSI bullish bias
    'volume_confirmation': True,       # Volume > average
    'min_r_multiple': 2.0,             # 2:1 minimum RR
    'max_risk_pct': 1.0                # 1% max risk
}
```

### 4. Backtest & Forward Test

```python
# Backtest on historical data (minimum 3-5 years)
from trading_bot.technical_analysis import TACoordinator, TradingJournal

ta = TACoordinator(account_size=10000)
journal = TradingJournal()

# Run through historical data
for date, data in historical_data.items():
    signal = ta.analyze_simple(symbol='BTCUSD', df=data)

    if signal.signal == 'LONG' and meets_your_rules(signal):
        # Log trade
        # Simulate outcome
        # Track performance
        pass

# Review results
metrics = journal.calculate_performance()
print(f"Win Rate: {metrics.win_rate}%")
print(f"Avg R: {metrics.avg_r_multiple}")
print(f"Profit Factor: {metrics.profit_factor}")
```

### 5. Journal & Refine

```python
# After every trade
journal.log_trade_exit(
    trade_id=trade_id,
    exit_price=exit_price,
    followed_rules=True,  # Be honest!
    mistakes=['held too long', 'moved stop'],
    emotions=['fear', 'greed'],
    notes='What you learned from this trade'
)

# Weekly/monthly review
report = journal.generate_review_report()
# Kill setups that underperform
# Keep what actually prints money
```

---

## Integration with Existing Trading Bot

The TA framework integrates seamlessly with the existing trading orchestrator:

```python
from trading_bot.orchestrator.trading_orchestrator import TradingOrchestrator
from trading_bot.technical_analysis import TACoordinator

# In your orchestrator or screener
ta = TACoordinator(
    account_size=config.account_size,
    risk_per_trade=config.risk_per_trade
)

# During screening
for symbol in watchlist:
    # Get market data
    df = market_data_service.get_bars(symbol, timeframe='1h')

    # Run TA analysis
    signal = ta.analyze_simple(symbol=symbol, df=df)

    # Filter signals
    if signal.signal == 'LONG' and signal.quality_score > 70:
        # Add to buy list with signal parameters
        buy_candidates.append({
            'symbol': symbol,
            'entry_price': signal.entry_price,
            'stop_loss': signal.stop_loss,
            'take_profit': signal.take_profit,
            'position_size': signal.position_size_shares,
            'reasoning': signal.reasoning
        })
```

---

## Performance Metrics

The framework tracks comprehensive metrics:

```
TRADING PERFORMANCE REVIEW
================================================================================

OVERALL STATISTICS:
  Total Trades: 50
  Wins: 28 | Losses: 20 | BE: 2
  Win Rate: 56.0%

P&L METRICS:
  Total P&L: $2,450.00 (24.50%)
  Avg Win: $120.50 | Avg Loss: $50.25
  Largest Win: $450.00 | Largest Loss: $100.00
  Profit Factor: 2.40
  Expectancy: $67.50 per trade

R-MULTIPLE METRICS:
  Avg R-Multiple: 2.15R
  Total R Achieved: 107.5R

RISK METRICS:
  Max Drawdown: $320.00 (3.20%)
  Sharpe Ratio: 1.85
  Sortino Ratio: 2.34

TRADE QUALITY:
  Avg Trade Duration: 18.5 hours
  Best Setup Type: breakout
  Worst Setup Type: reversal
  Rule Adherence Rate: 92.0%

PERFORMANCE BY REGIME:
  trending: 30 trades, 63.3% wins, $1,890.00 P&L
  ranging: 20 trades, 45.0% wins, $560.00 P&L
```

---

## Examples

See `examples/ta_framework_example.py` for comprehensive examples:

1. **Basic single-timeframe analysis**
2. **Multi-timeframe analysis**
3. **Using individual components**
4. **Trading journal and performance tracking**
5. **Complete trading workflow**

Run examples:
```bash
cd /home/user/robinhood-algo-trading-bot
python examples/ta_framework_example.py
```

---

## Key Principles

1. **No trade without clear risk parameters** - Every signal includes entry, stop, target, position size
2. **Context matters** - Same indicator means different things in different regimes
3. **Higher timeframes rule** - Never fight the higher-TF trend
4. **Size is everything** - More blowups from position sizing than bad entries
5. **Volume confirms** - Breakouts without volume = fakeouts
6. **No journal = no improvement** - You can't fix what you don't measure

---

## Warning Signs to SKIP Trades

The framework will set `signal='SKIP'` when:

- ✗ Multi-TF trends mixed/unclear
- ✗ R-multiple < 2.0 (insufficient reward for risk)
- ✗ Quality score < 50/100
- ✗ Confidence < 60%
- ✗ Volume doesn't confirm price action
- ✗ Regime transitional (unclear breakout vs mean reversion)
- ✗ Structure broken or choppy

**When in doubt, sit it out.**

---

## Advanced Features

### Kelly Criterion for Position Sizing

```python
risk_calc = RiskCalculator()

kelly_pct = risk_calc.calculate_kelly_criterion(
    win_rate=0.55,
    avg_win=120,
    avg_loss=50
)

print(f"Kelly suggests: {kelly_pct*100:.1f}% per trade")
# Most traders use Kelly/2 or Kelly/4 for safety
```

### Sharpe Ratio Calculation

```python
risk_calc = RiskCalculator()

sharpe = risk_calc.calculate_sharpe_ratio(
    returns=[0.02, -0.01, 0.03, 0.01, -0.005, 0.025]
)

print(f"Sharpe Ratio: {sharpe:.2f}")
# > 1 = good, > 2 = excellent
```

### Maximum Drawdown Analysis

```python
risk_calc = RiskCalculator()

max_dd, start_idx, end_idx = risk_calc.calculate_max_drawdown(
    equity_curve=[10000, 10200, 10150, 9900, 10500, 11000]
)

print(f"Max Drawdown: {max_dd:.2f}%")
```

---

## FAQ

**Q: Can I use this for both stocks and crypto?**
A: Yes. All tools work for both. Just adjust volatility expectations (crypto has higher ATR).

**Q: What's the minimum data required?**
A: At least 200 bars for reliable structure analysis. More is better.

**Q: Do I need all 20 tools for every trade?**
A: No. Pick 5-7 tools that fit your strategy. The coordinator uses all 20 to synthesize signals.

**Q: What if I disagree with a signal?**
A: Use individual components to build your own logic. The coordinator is a starting point, not gospel.

**Q: How do I backtest my own rules?**
A: Use the `TradingJournal` to track performance. Run your rules on historical data and journal outcomes.

**Q: What's a good win rate?**
A: 40-60% is normal. Higher R-multiples matter more than win rate. A 40% win rate with 3R average beats a 60% win rate with 1.5R.

---

## Support & Contribution

- **Issues**: Report at https://github.com/your-repo/issues
- **Questions**: See examples and this documentation first
- **Contributions**: PRs welcome for bug fixes and improvements

---

**Built for traders who want informed decisions, not gambling.**
```
