# Multi-Agent Trading System

Self-learning AI trading system with Claude-powered agents, consensus voting, and PostgreSQL memory.

## Overview

This multi-agent system uses specialized AI agents to collaboratively make trading decisions:

- **RegimeDetectorAgent** - Classifies market regime (BULL/BEAR/SIDEWAYS/HIGH_VOL/LOW_VOL)
- **ResearchAgent** - Analyzes fundamentals using Financial Modeling Prep API
- **NewsAnalystAgent** - Performs sentiment analysis from news feeds
- **RiskManagerAgent** - Calculates position sizes using Kelly Criterion
- **StrategyBuilderAgent** - Proposes parameter adjustments based on trade history
- **LearningAgent** - Identifies winning patterns from past trades
- **AgentOrchestrator** - Coordinates consensus voting (2/3 agents must agree)

All agent interactions are stored in PostgreSQL for self-learning and performance analysis.

## Quick Start

### 1. Install Dependencies

```bash
pip install anthropic sqlalchemy psycopg2-binary alembic
```

### 2. Set Up PostgreSQL Database

On your VPS:

```bash
# SSH into VPS
ssh hetzner

# Run setup script
cd /opt/trading-bot
bash scripts/setup-database.sh
```

Or manually:

```bash
sudo -u postgres psql
CREATE DATABASE trading_bot;
CREATE USER trading_bot WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE trading_bot TO trading_bot;
\q
```

### 3. Configure Environment Variables

Add to `.env`:

```bash
# Claude API (required)
ANTHROPIC_API_KEY=sk-ant-api03-xxxxx

# Financial Modeling Prep (required - free tier)
FMP_API_KEY=your_fmp_key

# PostgreSQL (required)
DATABASE_URL=postgresql://trading_bot:password@localhost:5432/trading_bot

# Enable multi-agent system
MULTI_AGENT_ENABLED=true
MULTI_AGENT_MIN_AGREEMENT=2
MULTI_AGENT_DAILY_LLM_BUDGET=5.00

# Self-learning (enable after 10+ trades)
SELF_LEARNING_ENABLED=false
SELF_LEARNING_MIN_TRADES=10
SELF_LEARNING_AUTO_APPLY_THRESHOLD=80.0
SELF_LEARNING_LOOKBACK_DAYS=30
```

### 4. Run Database Migrations

```bash
alembic upgrade head
```

Verify setup:

```bash
bash scripts/verify-database.sh
```

### 5. Test Multi-Agent System

```bash
python -m trading_bot.llm.examples.multi_agent_consensus_workflow
```

Expected output:

```
==============================================================
EVALUATING TRADE OPPORTUNITY: AAPL @ $175.50
==============================================================

Step 1: Detecting market regime...
  Market Regime: BULL (confidence: 78%)

Step 2: Running multi-agent consensus vote...
  Consensus Result:
    Decision: BUY
    Consensus Reached: True
    Agreement: 2/2

  Agent Votes:
    research: BUY (confidence: 82%)
    news_analyst: BUY (confidence: 71%)

Step 3: Consensus reached for BUY - calculating position size...
  Risk Manager Decision: APPROVE
    Position Size: 57 shares (5.0% of portfolio)
    Stop Loss: 3.2% below entry
    Take Profit: 8.5% above entry

Cost: $0.12 | Tokens: 4,523
```

## Architecture

### Database Schema

**agent_interactions** - Every agent action with cost/tokens tracking
```sql
id, agent_name, action, context, result, tokens_used, cost_usd, latency_ms, created_at
```

**agent_prompts** - Prompt versions for A/B testing
```sql
id, agent_name, prompt_name, version, content, performance_score, created_at
```

**trade_outcomes** - Trade results for learning
```sql
id, symbol, decision, entry_price, exit_price, pnl_dollars, pnl_pct, exit_reason, created_at
```

**strategy_adjustments** - Parameter changes over time
```sql
id, parameter_name, old_value, new_value, confidence_score, status, reasoning, created_at
```

**agent_daily_metrics** - Aggregated performance
```sql
id, agent_name, date, total_calls, total_cost_usd, avg_latency_ms
```

**trade_metadata** - Extended trade context
```sql
id, trade_outcome_id, market_regime, sentiment_score, news_catalyst, created_at
```

### Consensus Voting

2/3 agents must agree for BUY decision:

```python
consensus_result = orchestrator.multi_agent_consensus(
    agent_names=['research', 'news_analyst'],
    context={'symbol': 'AAPL', 'current_price': 175.50, ...},
    min_agreement=2
)

if consensus_result['consensus_reached'] and consensus_result['decision'] == 'BUY':
    # Position sizing from RiskManager
    risk_result = risk_manager.execute({...})
```

### Cost Tracking

Every LLM call is automatically tracked:

- **Model**: Claude Haiku 4.5 (`claude-haiku-4-20250514`)
- **Pricing**: $0.40/M input tokens, $2.00/M output tokens
- **Typical cost**: $0.08-$0.15 per trade evaluation
- **Daily budget**: $5.00 = ~35-60 evaluations/day

### FMP Rate Limiting

Free tier provides 250 calls/day:

- Auto-resets at midnight UTC
- 5-minute response caching
- Graceful degradation if limit reached
- ~30-40 trade evaluations/day within limit

## Usage

### Integrate with Trading Orchestrator

```python
from trading_bot.orchestrator import TradingOrchestrator

orchestrator = TradingOrchestrator(config={
    'orchestrator_mode': 'paper',
})

# Automatic multi-agent evaluation when MULTI_AGENT_ENABLED=true
orchestrator.run()

# Or call directly
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

### Manual Agent Usage

```python
from trading_bot.llm.agents import ResearchAgent, NewsAnalystAgent, RiskManagerAgent
from trading_bot.llm.memory_service import AgentMemory

memory = AgentMemory()

# Research Agent
research_agent = ResearchAgent(memory=memory)
research_result = research_agent.execute({
    'symbol': 'AAPL',
    'current_price': 175.50,
    'technical_data': {...}
})

# News Analyst
news_analyst = NewsAnalystAgent(memory=memory)
news_result = news_analyst.execute({
    'symbol': 'AAPL',
    'current_price': 175.50
})

# Risk Manager
risk_manager = RiskManagerAgent(memory=memory)
risk_result = risk_manager.execute({
    'symbol': 'AAPL',
    'entry_price': 175.50,
    'portfolio_value': 100000.0,
    'cash_available': 50000.0,
    'volatility': 3.25,
    'beta': 1.15
})
```

### Self-Learning Loop

After collecting 10+ trades, enable self-learning:

```python
from trading_bot.llm.self_learning_loop import SelfLearningLoop
from trading_bot.llm.memory_service import AgentMemory

memory = AgentMemory()
learning_loop = SelfLearningLoop(memory=memory)

# Run learning cycle
result = learning_loop.run_cycle(strategy_name='default')

print(f"Analyzed {result['trades_analyzed']} trades")
print(f"Found {result['patterns_found']} patterns")
print(f"Proposed {result['proposals_total']} adjustments")
print(f"Auto-applied {result['proposals_auto_applied']} high-confidence changes")
```

Auto-apply criteria:
- Confidence score ≥ 80%
- Risk level = LOW
- Priority = HIGH

Medium-confidence adjustments are flagged for manual review.

## Monitoring

### Query Agent Performance

```sql
-- Daily costs by agent
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

-- Trade outcomes
SELECT
    symbol,
    decision,
    pnl_pct,
    exit_reason,
    created_at
FROM trade_outcomes
ORDER BY created_at DESC
LIMIT 20;

-- Strategy adjustments
SELECT
    parameter_name,
    old_value,
    new_value,
    confidence_score,
    status,
    reasoning
FROM strategy_adjustments
ORDER BY created_at DESC
LIMIT 10;
```

### Monitor Budget

```python
from trading_bot.llm.memory_service import AgentMemory

memory = AgentMemory()
stats = memory.get_daily_cost_by_agent()

for agent, cost in stats.items():
    print(f"{agent}: ${cost:.4f}")
```

## Cost Estimation

| Activity | Tokens | Cost | Notes |
|----------|--------|------|-------|
| Single agent call | 1,000-2,000 | $0.03-$0.06 | Research or News analysis |
| Trade evaluation | 4,000-6,000 | $0.08-$0.15 | 3 agents (Research + News + Risk) |
| Daily usage (20 evals) | 80,000-120,000 | $1.60-$2.40 | Well within $5 budget |
| Self-learning cycle | 8,000-12,000 | $0.16-$0.24 | Nightly optimization |
| FMP API calls | - | Free | 250 calls/day limit |

## Troubleshooting

### Database Connection Errors

```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Test connection
psql $DATABASE_URL

# Check logs
sudo tail -f /var/log/postgresql/postgresql-*.log
```

### Migration Errors

```bash
# Check current version
alembic current

# Show history
alembic history

# Reset and upgrade
alembic stamp head
alembic upgrade head
```

### FMP Rate Limit

If you hit 250 calls/day:

1. Monitor usage: `grep "FMP API call" logs/trading_bot.log`
2. Reduce evaluation frequency
3. Upgrade to FMP Pro ($29/month for 5,000 calls/day)

### LLM Budget Exceeded

If you exceed $5/day:

1. Check spending: `SELECT SUM(cost_usd) FROM agent_interactions WHERE created_at >= CURRENT_DATE`
2. Adjust `MULTI_AGENT_DAILY_LLM_BUDGET` in `.env`
3. Reduce consensus frequency
4. Use fewer agents per evaluation

## API References

- **Anthropic Claude**: https://docs.anthropic.com/
- **Financial Modeling Prep**: https://financialmodelingprep.com/developer/docs/
- **PostgreSQL**: https://www.postgresql.org/docs/

## Security

- Never commit `.env` to git
- Use strong PostgreSQL passwords
- Restrict database access to localhost
- Monitor API key usage regularly
- Enable PostgreSQL SSL for remote connections

## License

See project root LICENSE file.
