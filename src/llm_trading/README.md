# LLM-Powered Autonomous Trading System

After extensive ML validation showing 50% accuracy (coin flip), we pivoted to an LLM-powered hybrid approach that combines Claude's reasoning with fast rule-based execution.

## Architecture

**Hybrid Design: LLM for Strategy, Rules for Execution**

```
Morning (9:00am):
  LLM Screener → Analyze market → Generate watchlist (10-15 stocks)

Intraday (9:30am-4pm):
  Rule Executor → Monitor watchlist → Execute when criteria met (NO LLM, pure speed)

Evening (5:00pm):
  LLM Optimizer → Review performance → Autonomously adjust parameters → Learn
```

## Why LLM Over ML?

**ML Failed (AttentionLSTM):**
- 50.01% average accuracy across 5 market regimes (2020-2024)
- Extreme instability (bimodal convergence, seed-dependent)
- Best period: 56% ± 8% (unstable)
- Worst period: 40% ± 0% (stable but wrong)

**LLM Advantages:**
- Contextual reasoning (can combine technicals + news + sector)
- No training required (adapts to new information immediately)
- Explains decisions (human-readable reasoning)
- Self-tuning (learns from outcomes, adjusts strategy)

## Components

### 1. Market Context Builder (`market_context.py`)
Transforms raw market data into human-readable context with interpretations.

**Example output:**
```json
{
  "symbol": "NVDA",
  "technicals": {
    "rsi": {
      "value": 28.4,
      "level": "oversold",
      "interpretation": "oversold (falling) - potential bounce opportunity but confirm with price action"
    },
    "bollinger_bands": {
      "position_pct": 5.3,
      "interpretation": "touching lower band (oversold, potential bounce) | BB squeeze detected"
    }
  }
}
```

### 2. LLM Morning Screener (`llm_screener.py`)
Uses Claude to analyze candidates and generate daily watchlist with trade setups.

**Features:**
- Analyzes pool of candidate symbols
- LLM selects best opportunities (confidence >60%)
- Generates detailed trade setups with entry/exit criteria
- Saves to `watchlists/watchlist_latest.json`

**Usage:**
```python
screener = LLMScreener(alpaca_key, alpaca_secret, anthropic_key)
watchlist = screener.generate_watchlist(candidates, max_picks=15)
```

### 3. Rule Executor (`rule_executor.py`)
Fast, deterministic execution engine for intraday trading.

**Features:**
- NO LLM calls (pure speed, millisecond latency)
- Monitors watchlist every minute
- Checks entry conditions (price, RSI, volume)
- Manages positions (stop loss, take profit, time exits)
- Circuit breaker at -10% daily loss

**Usage:**
```python
executor = RuleExecutor(alpaca_key, alpaca_secret, paper=True, check_interval=60)
executor.run_trading_session()  # Blocks until market close
```

### 4. LLM Evening Optimizer (`llm_optimizer.py`)
Autonomous strategy optimization with progressive learning.

**Autonomy Levels:**
- **Level 1 (Supervised):** Requires human approval for all changes
- **Level 2 (Bounded):** Auto-applies changes within safety bounds (confidence >70%)
- **Level 3 (Full):** Learns from past adjustments, fully autonomous

**Safety Mechanisms:**
- Hard limits (cannot be violated)
- Circuit breakers (-10% daily loss)
- Rollback capability (checkpoint system)
- Human override (pause anytime)

**Usage:**
```python
optimizer = LLMOptimizer(anthropic_key, autonomy_level=2)
report = optimizer.optimize_strategy(performance_data, watchlist_data, market_conditions)
```

### 5. Main Orchestrator (`main.py`)
Coordinates daily trading cycle with scheduling.

**Modes:**
1. Run daily cycle once (manual)
2. Schedule automated daily cycle
3. Run morning screener only
4. Run trading session only
5. Run evening optimizer only

**Usage:**
```python
python llm_trading/main.py
```

## Setup

### 1. Install Dependencies
```bash
pip install anthropic alpaca-trade-api pandas numpy python-dotenv schedule
```

### 2. Configure API Keys
Create `.env` file:
```env
ALPACA_API_KEY=your_alpaca_key
ALPACA_SECRET_KEY=your_alpaca_secret
ANTHROPIC_API_KEY=your_anthropic_key

# Optional: Telegram Notifications
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

**For Telegram setup:** See `TELEGRAM_SETUP.md` for detailed instructions on creating a bot and getting your chat ID.

### 3. Initialize Parameters
Default parameters are automatically created on first run. You can customize them in `llm_trading/strategy_params.json`:

```json
{
  "rsi_oversold": 30,
  "rsi_overbought": 70,
  "stop_loss_pct": -1.0,
  "take_profit_pct": 2.0,
  "position_size_pct": 0.015,
  "max_trades_per_day": 15,
  "max_hold_minutes": 120,
  "confidence_threshold": 70
}
```

## Usage

### Quick Start (Test Screener)
```python
from llm_screener import LLMScreener
import os
from dotenv import load_dotenv

load_dotenv()

screener = LLMScreener(
    api_key_alpaca=os.getenv('ALPACA_API_KEY'),
    api_secret_alpaca=os.getenv('ALPACA_SECRET_KEY'),
    api_key_anthropic=os.getenv('ANTHROPIC_API_KEY')
)

candidates = ['SPY', 'QQQ', 'NVDA', 'TSLA', 'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'AMD']
watchlist = screener.generate_watchlist(candidates, max_picks=5)

for entry in watchlist:
    print(f"{entry['symbol']}: {entry['setup_type']} ({entry['confidence']}% confidence)")
```

### Full Daily Cycle
```python
from main import TradingSystem
import os
from dotenv import load_dotenv

load_dotenv()

system = TradingSystem(
    alpaca_api_key=os.getenv('ALPACA_API_KEY'),
    alpaca_secret_key=os.getenv('ALPACA_SECRET_KEY'),
    anthropic_api_key=os.getenv('ANTHROPIC_API_KEY'),
    autonomy_level=1,  # Supervised
    paper=True  # ALWAYS use paper trading initially
)

system.run_daily_cycle()  # Morning → Trading → Evening
```

### Scheduled Automation
```python
system.schedule_daily_cycle()  # Runs at 9am, 9:30am, 5pm daily
```

## Safety Features

### Hard Limits (Cannot Be Overridden)
- RSI oversold: 15-35
- RSI overbought: 65-85
- Stop loss: -3% to -0.3%
- Take profit: 0.5% to 5%
- Position size: 0.5% to 3% account risk
- Max trades/day: 3-30
- Max hold time: 30-240 minutes

### Circuit Breakers
- **-10% daily loss:** Halt trading, close all positions
- **Market close:** Close all positions
- **Keyboard interrupt:** Safe shutdown, close positions

### Rollback System
All parameter changes are logged with timestamps. You can revert to previous configurations:
```json
{
  "timestamp": "2024-01-15T17:05:23",
  "parameter": "rsi_oversold",
  "old_value": 30,
  "new_value": 28,
  "reasoning": "Win rate 42% suggests entries too early...",
  "outcome": "IMPROVED"
}
```

## Progressive Autonomy Rollout

### Week 1-2: Level 1 (Supervised)
- Human approves all parameter changes
- Monitor performance and LLM reasoning
- Build trust in system decisions

### Week 3-4: Level 2 (Bounded)
- Auto-applies changes with confidence >70%
- Still within safety bounds
- Human review of low-confidence proposals

### Month 2+: Level 3 (Full Autonomy)
- LLM learns from past adjustment outcomes
- Fully autonomous optimization
- Human can pause/override anytime

## Data Storage

```
llm_trading/
├── strategy_params.json           # Current parameters
├── adjustment_history.json        # All changes with outcomes
├── watchlists/
│   ├── watchlist_YYYYMMDD_HHMMSS.json
│   └── watchlist_latest.json
├── performance/
│   ├── performance_YYYYMMDD_HHMMSS.json
│   └── performance_latest.json
└── reports/
    ├── optimization_YYYYMMDD_HHMMSS.json
    └── optimization_latest.json
```

## Key Differences from ML Approach

| Aspect | ML (Failed) | LLM (Current) |
|--------|-------------|---------------|
| **Training** | Requires historical data, retraining | No training, immediate adaptation |
| **Features** | Pre-selected 15 features (raw numbers) | Rich context with interpretations |
| **Stability** | Extremely unstable (50% ± 25%) | Reasoning-based, consistent |
| **Explainability** | Black box (no reasoning) | Human-readable explanations |
| **Adaptation** | Slow (retrain on new data) | Fast (learns from outcomes) |
| **Context** | Only technical indicators | Technicals + news + sector + macro |
| **Speed** | Fast inference (ms) | Slow (10-60s) but only for strategy |
| **Execution** | N/A | Rule-based (ms latency) |

## Cost Estimation

**Claude Sonnet-4 Pricing:**
- Input: $3 / 1M tokens
- Output: $15 / 1M tokens

**Daily Usage:**
- Morning screener: ~50k tokens ($0.50)
- Evening optimizer: ~30k tokens ($0.30)
- **Total: ~$0.80/day or ~$200/month**

Much cheaper than constant retraining and validation of ML models.

## Future Enhancements

1. **Dynamic Candidate Selection:** Fetch top volume stocks automatically
2. **Multi-Timeframe Analysis:** Incorporate daily/weekly context
3. **News Integration:** Real-time news sentiment (FinBERT or Claude)
4. **Regime Detection:** Adapt strategy to market regime (bull/bear/sideways)
5. **Portfolio Management:** Multi-stock position sizing and correlation
6. **Backtesting:** Simulate historical performance
7. **Web Dashboard:** Real-time monitoring and control

## Testing

### Test Market Context Builder
```python
from market_context import MarketContextBuilder
import os
from dotenv import load_dotenv

load_dotenv()

builder = MarketContextBuilder(
    api_key=os.getenv('ALPACA_API_KEY'),
    api_secret=os.getenv('ALPACA_SECRET_KEY')
)

context = builder.build_full_context('NVDA')
print(json.dumps(context, indent=2))
```

### Test With Mock Data
All components have `if __name__ == "__main__"` sections with mock data for testing.

## Support

For issues or questions, refer to:
- Original ML validation logs: `multi_period_validation.log`
- ML results: `multi_period_robustness_results.csv`
- This document for LLM approach

## License

MIT License - Use at your own risk. ALWAYS test with paper trading first.

## Disclaimer

This is experimental software. Trading involves risk. Past performance does not guarantee future results. ALWAYS use paper trading first. Start with Level 1 autonomy (supervised). Monitor closely during initial weeks.
