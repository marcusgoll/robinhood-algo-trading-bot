# Multi-Agent Trading System Setup Guide

This guide walks you through setting up the multi-agent trading system on your VPS with existing PostgreSQL.

## Prerequisites

- Existing PostgreSQL database running on VPS
- SSH access to VPS (`ssh hetzner`)
- API keys added to `.env` file:
  - `ANTHROPIC_API_KEY` - Claude API key
  - `FMP_API_KEY` - Financial Modeling Prep API key
  - `DATABASE_URL` - PostgreSQL connection string

## Step 1: Create Trading Bot Database

SSH into your VPS and create a dedicated database for the trading bot:

```bash
ssh hetzner
sudo -u postgres psql
```

In the PostgreSQL prompt, run:

```sql
-- Create database
CREATE DATABASE trading_bot;

-- Create user (optional - you may use existing user)
CREATE USER trading_bot WITH PASSWORD 'your_secure_password_here';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE trading_bot TO trading_bot;

-- Exit
\q
```

## Step 2: Configure Database Connection

Update your `.env` file with the correct DATABASE_URL:

```bash
# Format: postgresql://username:password@host:port/database
DATABASE_URL=postgresql://trading_bot:your_secure_password_here@localhost:5432/trading_bot
```

**Note**: If your PostgreSQL is on the VPS and you're running the bot locally for testing, you'll need to:
- Use SSH tunnel: `ssh -L 5432:localhost:5432 hetzner`
- Or expose PostgreSQL port (not recommended for security)
- Or run the bot on the VPS directly

## Step 3: Run Database Migrations

The trading bot uses Alembic for database migrations. Run migrations to create the 6 agent memory tables:

```bash
# From your project root
alembic upgrade head
```

This will create the following tables:
- `agent_interactions` - Tracks every agent action with cost/tokens
- `agent_prompts` - Stores prompt versions for A/B testing
- `trade_outcomes` - Records trade results for learning
- `strategy_adjustments` - Tracks parameter changes over time
- `agent_daily_metrics` - Aggregates daily performance by agent
- `trade_metadata` - Extended trade context (regime, sentiment, etc.)

## Step 4: Verify Database Setup

Check that all tables were created successfully:

```bash
ssh hetzner
sudo -u postgres psql -d trading_bot -c "\dt"
```

You should see 6 tables plus the Alembic version table:

```
                List of relations
 Schema |         Name          | Type  |    Owner
--------+-----------------------+-------+-------------
 public | agent_daily_metrics   | table | trading_bot
 public | agent_interactions    | table | trading_bot
 public | agent_prompts         | table | trading_bot
 public | alembic_version       | table | trading_bot
 public | strategy_adjustments  | table | trading_bot
 public | trade_metadata        | table | trading_bot
 public | trade_outcomes        | table | trading_bot
```

## Step 5: Enable Multi-Agent System

Update `.env` to enable the multi-agent system:

```bash
# Multi-Agent System Configuration
MULTI_AGENT_ENABLED=true              # Enable multi-agent consensus
MULTI_AGENT_MIN_AGREEMENT=2           # Require 2/3 agents to agree
MULTI_AGENT_DAILY_LLM_BUDGET=5.00    # $5/day limit for Claude API calls

# Self-Learning Loop Configuration (optional)
SELF_LEARNING_ENABLED=false           # Enable nightly optimization (start with false)
SELF_LEARNING_MIN_TRADES=10           # Minimum trades before learning
SELF_LEARNING_AUTO_APPLY_THRESHOLD=80.0  # Auto-apply adjustments with 80%+ confidence
SELF_LEARNING_LOOKBACK_DAYS=30        # Analyze last 30 days of trades
```

**Important**: Start with `SELF_LEARNING_ENABLED=false` until you have enough trades (10+) for the learning algorithm to analyze.

## Step 6: Test Multi-Agent System

Run the example workflow to verify everything works:

```bash
python -m trading_bot.llm.examples.multi_agent_consensus_workflow
```

This will simulate a trade evaluation with:
- RegimeDetectorAgent - Classifies market regime
- ResearchAgent - Analyzes fundamentals via FMP API
- NewsAnalystAgent - Analyzes sentiment from news
- RiskManagerAgent - Sizes position using Kelly Criterion

Expected output:
```
==============================================================
EVALUATING TRADE OPPORTUNITY: AAPL @ $175.50
==============================================================

Step 1: Detecting market regime...
  Market Regime: BULL (confidence: 78%, strength: STRONG)
  Key indicators: price_above_sma_20, price_above_sma_50, adx_trending

Step 2: Running multi-agent consensus vote...

  Consensus Result:
    Decision: BUY
    Consensus Reached: True
    Agreement: 2/2
    Avg Confidence: 76.5%

  Agent Votes:
    research: BUY (confidence: 82%)
      Reasoning: Strong fundamentals with P/E ratio of 28.5...
    news_analyst: BUY (confidence: 71%)
      Reasoning: Positive sentiment from recent earnings beat...

Step 3: Consensus reached for BUY - calculating position size...

  Risk Manager Decision: APPROVE
    Position Size: 57 shares (5.0% of portfolio)
    Stop Loss: 3.2% below entry
    Take Profit: 8.5% above entry
    Risk/Reward: 2.66
    Kelly Size: 6.2%

==============================================================
FINAL DECISION
==============================================================
Symbol: AAPL
Decision: BUY
Consensus Reached: True
Market Regime: BULL (78%)

TRADE DETAILS:
  Shares: 57
  Position Size: 5.0% of portfolio
  Entry: $175.50
  Stop Loss: 3.2% ($169.89)
  Take Profit: 8.5% ($190.41)
  Risk/Reward: 2.66

Summary: BUY 57 shares of AAPL @ $175.50 (stop: 3.2%, target: 8.5%)

Cost: $0.1234
Tokens: 4,523
==============================================================
```

## Step 7: Integrate with Trading Orchestrator

The multi-agent system is already integrated into `TradingOrchestrator`. You can use it in two ways:

### Option A: Automatic Integration (Recommended)

The orchestrator will automatically use multi-agent consensus when `MULTI_AGENT_ENABLED=true`:

```python
from trading_bot.orchestrator import TradingOrchestrator

orchestrator = TradingOrchestrator(config={
    'orchestrator_mode': 'paper',  # Start with paper trading
    # ... other config
})

# Run orchestrator - it will use multi-agent system automatically
orchestrator.run()
```

### Option B: Manual Call

Call the multi-agent workflow directly for specific symbols:

```python
from trading_bot.orchestrator import TradingOrchestrator

orchestrator = TradingOrchestrator(config={
    'orchestrator_mode': 'paper',
})

# Evaluate specific trade with multi-agent consensus
result = orchestrator.evaluate_trade_with_agents(
    symbol='AAPL',
    current_price=175.50,
    technical_indicators={
        'sma_20': 172.30,
        'sma_50': 168.45,
        'sma_200': 165.20,
        'atr': 3.25,
        'adx': 28.5,
        'rsi': 58.2,
        'volume_ratio': 1.2,
        'beta': 1.15
    }
)

if result['decision'] == 'BUY':
    print(f"BUY {result['position_size_shares']} shares")
    print(f"Stop: {result['stop_loss_pct']:.1f}%")
    print(f"Target: {result['take_profit_pct']:.1f}%")
```

## Step 8: Monitor Agent Performance

Query the database to monitor agent performance:

```sql
-- View agent interaction history
SELECT
    agent_name,
    COUNT(*) as total_calls,
    AVG(cost_usd) as avg_cost,
    SUM(cost_usd) as total_cost,
    AVG(tokens_used) as avg_tokens
FROM agent_interactions
WHERE created_at >= NOW() - INTERVAL '7 days'
GROUP BY agent_name
ORDER BY total_cost DESC;

-- View daily metrics
SELECT
    agent_name,
    date,
    total_calls,
    total_cost_usd,
    avg_latency_ms
FROM agent_daily_metrics
ORDER BY date DESC, total_cost_usd DESC
LIMIT 20;

-- View trade outcomes
SELECT
    symbol,
    decision,
    entry_price,
    exit_price,
    pnl_dollars,
    pnl_pct,
    exit_reason,
    created_at
FROM trade_outcomes
ORDER BY created_at DESC
LIMIT 20;
```

## Step 9: Enable Self-Learning (After 10+ Trades)

Once you have at least 10 completed trades, you can enable the self-learning loop:

```bash
# Update .env
SELF_LEARNING_ENABLED=true
```

The learning loop will:
1. Run nightly at 2 AM (configurable in code)
2. Analyze last 30 days of trades
3. Identify winning/losing patterns
4. Propose parameter adjustments
5. Auto-apply high-confidence adjustments (80%+ confidence)
6. Flag medium-confidence adjustments for manual review

View learning results:

```sql
-- View strategy adjustments
SELECT
    parameter_name,
    old_value,
    new_value,
    confidence_score,
    status,
    reasoning,
    created_at
FROM strategy_adjustments
ORDER BY created_at DESC
LIMIT 10;
```

## Troubleshooting

### Database Connection Errors

If you see `could not connect to server`:

1. Check DATABASE_URL format in `.env`
2. Verify PostgreSQL is running: `sudo systemctl status postgresql`
3. Check PostgreSQL logs: `sudo tail -f /var/log/postgresql/postgresql-*.log`
4. Verify firewall allows connections (if remote)

### Migration Errors

If `alembic upgrade head` fails:

```bash
# Check current revision
alembic current

# Show migration history
alembic history

# If stuck, reset to head
alembic stamp head
alembic upgrade head
```

### FMP Rate Limit Errors

If you hit the 250 calls/day limit:

1. Monitor FMP usage in logs: `grep "FMP API call" logs/trading_bot.log`
2. Reduce agent frequency in config
3. Cache FMP responses (already implemented with 5-minute TTL)
4. Upgrade to FMP Pro plan ($29/month for 5,000 calls/day)

### LLM Budget Errors

If you exceed the daily LLM budget ($5.00):

1. Monitor spending: `SELECT SUM(cost_usd) FROM agent_interactions WHERE created_at >= CURRENT_DATE`
2. Adjust `MULTI_AGENT_DAILY_LLM_BUDGET` in `.env`
3. Reduce consensus frequency
4. Use cheaper model (Haiku already cheapest at $0.40/M input tokens)

## Cost Estimation

Typical costs per trade evaluation (3 agents: Research + NewsAnalyst + RiskManager):

- **Tokens per evaluation**: ~4,000-6,000 tokens
- **Cost per evaluation**: $0.08-$0.15
- **Daily budget**: $5.00 = ~35-60 trade evaluations/day
- **FMP calls per evaluation**: 6-8 calls
- **Daily FMP limit**: 250 calls = ~30-40 evaluations/day

**Recommendation**: Start with 10-20 evaluations/day to stay well within limits while collecting data for the learning loop.

## Security Notes

1. **Never commit `.env` to git** - Contains API keys and database passwords
2. **Use strong PostgreSQL passwords** - Change `POSTGRES_PASSWORD` from default
3. **Restrict database access** - Only allow localhost or VPN connections
4. **Monitor API key usage** - Check Anthropic and FMP dashboards regularly
5. **Enable PostgreSQL SSL** - Use `?sslmode=require` in DATABASE_URL for remote connections

## Next Steps

1. Complete database setup (Steps 1-4)
2. Test with example workflow (Step 6)
3. Run in paper trading mode for 1-2 weeks
4. Collect 10+ trades
5. Enable self-learning loop (Step 9)
6. Review and approve medium-confidence adjustments
7. Switch to live trading after validation

For questions or issues, check logs at `logs/trading_bot.log` or review agent interactions in the database.
