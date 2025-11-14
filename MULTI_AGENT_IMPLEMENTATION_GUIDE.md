# Multi-Agent Trading System - Implementation Continuation Guide

## Status: Phase 1 Complete (40% Done)

This guide provides step-by-step instructions to complete the remaining 60% of the self-learning multi-agent trading system.

---

## ✅ COMPLETED: Phase 1 - PostgreSQL Foundation

**Files Created:**
1. `api/alembic/versions/003_create_agent_memory.py` (680 lines) - Database migration
2. `api/app/models/agent_memory.py` (475 lines) - SQLAlchemy ORM models
3. `src/trading_bot/llm/memory_service.py` (650 lines) - Database operations wrapper

**Database Tables:**
- `agent_prompts` - Prompt versioning and A/B testing
- `llm_interactions` - Every LLM call logged
- `strategy_adjustments` - Parameter evolution tracking
- `trade_outcomes` - Rich trade metadata
- `screener_results` - Opportunity tracking
- `agent_metrics` - Daily agent performance

**What Works:**
- PostgreSQL schema ready for deployment
- Memory service provides high-level database operations
- Agents can store/retrieve interactions, trades, adjustments
- Pattern queries enabled ("show me oversold bounces in bear markets")

---

## 📋 REMAINING: Phases 2-6 (60% to Complete)

### Phase 2: Agent Foundation & Coordination
### Phase 3: FMP Integration & Specialized Agents
### Phase 4: Self-Learning Loops
### Phase 5: Multi-Agent Workflows
### Phase 6: Deployment & Configuration

---

## PHASE 2: Agent Foundation & Coordination

### Task 2.1: Create BaseAgent Abstract Class

**File**: `src/trading_bot/llm/agents/base_agent.py`

```python
"""Base agent class that all specialized agents inherit from."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from uuid import UUID, uuid4
import anthropic
from ..memory_service import AgentMemory


class BaseAgent(ABC):
    """
    Abstract base class for all agents.

    All agents share common capabilities:
    - LLM interaction tracking
    - Cost monitoring
    - Memory storage
    - Standardized logging
    """

    def __init__(
        self,
        agent_name: str,
        model: str = "claude-haiku-4-20250514",
        memory: Optional[AgentMemory] = None
    ):
        self.agent_name = agent_name
        self.model = model
        self.memory = memory or AgentMemory()
        self.client = anthropic.Anthropic()  # Uses ANTHROPIC_API_KEY env var

    @abstractmethod
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main execution method each agent must implement.

        Args:
            context: Input data for agent (market data, symbols, etc.)

        Returns:
            Dict with agent's output
        """
        pass

    def _call_llm(
        self,
        system_message: str,
        user_prompt: str,
        prompt_id: Optional[UUID] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Wrapper for LLM calls with automatic tracking.

        Logs every call to database for cost analysis and learning.

        Args:
            system_message: System-level instructions
            user_prompt: User message
            prompt_id: Optional link to prompt version
            **kwargs: Additional anthropic.Message params

        Returns:
            Dict with 'content', 'tokens_used', 'cost_usd'
        """
        import time

        start = time.time()

        # Make API call
        response = self.client.messages.create(
            model=self.model,
            system=system_message,
            messages=[{"role": "user", "content": user_prompt}],
            **kwargs
        )

        latency_ms = int((time.time() - start) * 1000)

        # Calculate cost (Haiku 4.5 pricing)
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        cost = (input_tokens * 0.25 + output_tokens * 1.25) / 1_000_000

        # Extract text content
        content = response.content[0].text if response.content else ""

        # Store in database
        interaction_id = self.memory.store_interaction(
            agent_name=self.agent_name,
            prompt_id=prompt_id,
            input_context={'system': system_message, 'user': user_prompt},
            output_result={'content': content, 'raw_response': str(response)},
            model=self.model,
            tokens_used=input_tokens + output_tokens,
            cost_usd=cost,
            latency_ms=latency_ms,
            success=True
        )

        return {
            'content': content,
            'tokens_used': input_tokens + output_tokens,
            'cost_usd': cost,
            'latency_ms': latency_ms,
            'interaction_id': interaction_id
        }

    def log_metric(self, metric_name: str, value: float):
        """Log custom metric for this agent."""
        # Implement metric aggregation
        pass
```

---

### Task 2.2: Create FMPClient with Rate Limiting

**File**: `src/trading_bot/market_data/fmp_client.py`

```python
"""Financial Modeling Prep (FMP) client with free tier rate limiting."""

import os
import time
from datetime import date, datetime
from typing import Dict, List, Optional
import requests


class FMPClient:
    """
    FMP Free Tier client (250 API calls/day).

    Manages rate limiting to stay within daily quota.
    Prioritizes calls for high-value symbols.
    """

    FREE_TIER_DAILY_LIMIT = 250
    BASE_URL = "https://financialmodelingprep.com/api/v3"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('FMP_API_KEY')
        if not self.api_key:
            raise ValueError("FMP_API_KEY environment variable not set")

        self.calls_today = 0
        self.last_reset_date = date.today()

    def _check_and_increment_limit(self):
        """Check if under daily limit, increment counter."""
        # Reset counter if new day
        if date.today() != self.last_reset_date:
            self.calls_today = 0
            self.last_reset_date = date.today()

        if self.calls_today >= self.FREE_TIER_DAILY_LIMIT:
            raise Exception(f"FMP daily limit reached ({self.FREE_TIER_DAILY_LIMIT} calls)")

        self.calls_today += 1

    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """Make API request with error handling."""
        self._check_and_increment_limit()

        params = params or {}
        params['apikey'] = self.api_key

        url = f"{self.BASE_URL}/{endpoint}"

        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"FMP API error: {e}")
            return {}

    def get_quote(self, symbol: str) -> Dict:
        """Get real-time quote (uses 1 API call)."""
        data = self._make_request(f"quote/{symbol}")
        return data[0] if data else {}

    def get_key_metrics(self, symbol: str) -> Dict:
        """Get key metrics (P/E, P/B, etc.) - uses 1 API call."""
        data = self._make_request(f"key-metrics/{symbol}", {'limit': 1})
        return data[0] if data else {}

    def get_financial_ratios(self, symbol: str) -> Dict:
        """Get financial ratios (ROE, margins, etc.) - uses 1 API call."""
        data = self._make_request(f"ratios/{symbol}", {'limit': 1})
        return data[0] if data else {}

    def get_income_statement(self, symbol: str) -> Dict:
        """Get latest income statement - uses 1 API call."""
        data = self._make_request(f"income-statement/{symbol}", {'limit': 1})
        return data[0] if data else {}

    def batch_enrich_symbols(
        self,
        symbols: List[str],
        max_calls: int = 20
    ) -> Dict[str, Dict]:
        """
        Batch enrich symbols with fundamentals.

        Uses ~2 calls per symbol (quote + key metrics).
        Stops at max_calls to preserve quota.

        Args:
            symbols: List of symbols to enrich
            max_calls: Max API calls to use

        Returns:
            Dict mapping symbol -> fundamental data
        """
        results = {}
        calls_used = 0

        for symbol in symbols:
            if calls_used >= max_calls:
                break

            try:
                quote = self.get_quote(symbol)
                calls_used += 1

                metrics = self.get_key_metrics(symbol)
                calls_used += 1

                results[symbol] = {
                    'quote': quote,
                    'metrics': metrics
                }
            except Exception as e:
                print(f"Error enriching {symbol}: {e}")
                break

        return results

    def get_screener(
        self,
        market_cap_more_than: Optional[int] = None,
        market_cap_less_than: Optional[int] = None,
        price_more_than: Optional[float] = None,
        price_less_than: Optional[float] = None,
        volume_more_than: Optional[int] = None,
        sector: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        Use FMP's stock screener endpoint - uses 1 API call.

        Args:
            market_cap_more_than: Min market cap
            market_cap_less_than: Max market cap
            price_more_than: Min price
            price_less_than: Max price
            volume_more_than: Min volume
            sector: Sector filter
            limit: Max results

        Returns:
            List of stocks matching criteria
        """
        params = {'limit': limit}

        if market_cap_more_than:
            params['marketCapMoreThan'] = market_cap_more_than
        if market_cap_less_than:
            params['marketCapLowerThan'] = market_cap_less_than
        if price_more_than:
            params['priceMoreThan'] = price_more_than
        if price_less_than:
            params['priceLowerThan'] = price_less_than
        if volume_more_than:
            params['volumeMoreThan'] = volume_more_than
        if sector:
            params['sector'] = sector

        return self._make_request("stock-screener", params)
```

---

### Task 2.3: Create ResearchAgent

**File**: `src/trading_bot/llm/agents/research_agent.py`

```python
"""Research agent for deep fundamental and technical analysis."""

from typing import Dict, Any, List
from .base_agent import BaseAgent
from ...market_data.fmp_client import FMPClient


class ResearchAgent(BaseAgent):
    """
    Deep research agent for fundamental + technical analysis.

    Uses FMP free tier (250 calls/day) to enrich top watchlist symbols
    with fundamental data, then generates bull/bear thesis via Claude.
    """

    def __init__(self, **kwargs):
        super().__init__(agent_name='research', **kwargs)
        self.fmp = FMPClient()

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze symbol with fundamentals + technicals.

        Args:
            context: {
                'symbol': str,
                'technical_snapshot': dict (RSI, volume, etc.),
                'max_fmp_calls': int (default 2)
            }

        Returns:
            {
                'symbol': str,
                'thesis': str ('bullish', 'bearish', 'neutral'),
                'confidence': float (0-100),
                'key_metrics': dict,
                'reasoning': str
            }
        """
        symbol = context['symbol']
        technical = context.get('technical_snapshot', {})
        max_calls = context.get('max_fmp_calls', 2)

        # Fetch fundamentals from FMP (2 API calls)
        try:
            quote = self.fmp.get_quote(symbol)
            metrics = self.fmp.get_key_metrics(symbol)
        except Exception as e:
            return {
                'symbol': symbol,
                'thesis': 'neutral',
                'confidence': 0,
                'error': str(e)
            }

        # Build context for LLM
        system_message = """You are an expert stock analyst. Analyze the provided
fundamental and technical data to generate a concise investment thesis.

Output format (JSON):
{
    "thesis": "bullish" | "bearish" | "neutral",
    "confidence": 0-100,
    "reasoning": "1-2 sentence explanation"
}"""

        user_prompt = f"""Analyze {symbol}:

**Fundamentals:**
- Market Cap: ${metrics.get('marketCap', 'N/A')}
- P/E Ratio: {metrics.get('peRatio', 'N/A')}
- P/B Ratio: {metrics.get('pbRatio', 'N/A')}
- ROE: {metrics.get('roe', 'N/A')}%
- Debt/Equity: {metrics.get('debtToEquity', 'N/A')}

**Technicals:**
- Price: ${quote.get('price', 'N/A')}
- RSI (14): {technical.get('rsi', 'N/A')}
- Volume Ratio: {technical.get('volume_ratio', 'N/A')}x

Generate investment thesis (JSON only)."""

        # Call LLM
        result = self._call_llm(
            system_message=system_message,
            user_prompt=user_prompt,
            max_tokens=500
        )

        # Parse response (simplified - add proper JSON parsing)
        import json
        try:
            analysis = json.loads(result['content'])
        except:
            analysis = {
                'thesis': 'neutral',
                'confidence': 50,
                'reasoning': result['content'][:200]
            }

        return {
            'symbol': symbol,
            'thesis': analysis.get('thesis', 'neutral'),
            'confidence': analysis.get('confidence', 50),
            'reasoning': analysis.get('reasoning', ''),
            'key_metrics': {
                'pe_ratio': metrics.get('peRatio'),
                'market_cap': metrics.get('marketCap'),
                'price': quote.get('price')
            },
            'llm_cost_usd': result['cost_usd']
        }
```

---

## NEXT STEPS TO COMPLETE SYSTEM

### Immediate Next Components (Priority Order):

1. **AgentOrchestrator** (`src/trading_bot/llm/agent_orchestrator.py`)
   - Coordinates all agents
   - Implements multi-agent consensus
   - Routes tasks to appropriate agents

2. **StrategyBuilderAgent** (`src/trading_bot/llm/agents/strategy_builder_agent.py`)
   - Takes research thesis → generates trade setup
   - Defines entry/exit criteria
   - Links to existing llm_screener.py logic

3. **RiskManagerAgent** (`src/trading_bot/llm/agents/risk_manager_agent.py`)
   - Approves/rejects trades
   - Position sizing
   - Portfolio risk checks

4. **RegimeDetectorAgent** (`src/trading_bot/llm/agents/regime_detector_agent.py`)
   - Classifies market regime (BULL/BEAR/SIDEWAYS)
   - Uses SPY + VIX
   - Simple rules-based or LLM-enhanced

5. **LearningAgent** (`src/trading_bot/llm/agents/learning_agent.py`)
   - Evening review of performance
   - Proposes parameter adjustments
   - Extends existing llm_optimizer.py

6. **SelfLearningLoop** (`src/trading_bot/llm/self_learning_loop.py`)
   - Nightly cycle: measure → analyze → propose → store
   - Updates adjustment outcomes
   - A/B tests prompts

7. **Environment Configuration**
   - Update `.env.example` with all new variables
   - Add FMP_API_KEY, AGENT_ORCHESTRATOR_ENABLED, etc.

8. **Docker & VPS Deployment**
   - Update `docker-compose.yml` with PostgreSQL (pgvector)
   - Create deployment script
   - Run migration on VPS: `alembic upgrade head`

---

## TESTING CHECKLIST

### Phase 1 (Database) Tests:
```bash
# Test migration
cd api
alembic upgrade head
alembic downgrade base
alembic upgrade head

# Test models in Python REPL
python
>>> from app.models.agent_memory import *
>>> from app.core.database import SessionLocal
>>> session = SessionLocal()
>>> # Try creating records
>>> from uuid import uuid4
>>> prompt = AgentPrompt(id=uuid4(), agent_name='test', prompt_version=1, prompt_template='test', active=True)
>>> session.add(prompt)
>>> session.commit()
>>> print(prompt.id)  # Should print UUID

# Test memory service
python
>>> from src.trading_bot.llm.memory_service import AgentMemory
>>> memory = AgentMemory()
>>> id = memory.store_interaction(
...     agent_name='test',
...     input_context={'symbol': 'AAPL'},
...     output_result={'thesis': 'bullish'},
...     model='claude-haiku-4.5',
...     tokens_used=100,
...     cost_usd=0.001
... )
>>> print(id)  # Should print interaction UUID
```

### Phase 2+ (Agents) Tests:
```bash
# Test FMP client
python
>>> from src.trading_bot.market_data.fmp_client import FMPClient
>>> fmp = FMPClient()  # Needs FMP_API_KEY in .env
>>> quote = fmp.get_quote('AAPL')
>>> print(quote)  # Should print quote dict

# Test ResearchAgent
python
>>> from src.trading_bot.llm.agents.research_agent import ResearchAgent
>>> agent = ResearchAgent()  # Needs ANTHROPIC_API_KEY in .env
>>> result = agent.execute({
...     'symbol': 'AAPL',
...     'technical_snapshot': {'rsi': 35, 'volume_ratio': 1.5}
... })
>>> print(result)  # Should print analysis dict
```

---

## DEPLOYMENT STEPS

### 1. Run Migration on VPS

```bash
ssh hetzner
cd /opt/trading-bot/api
# Ensure DATABASE_URL is set in .env
alembic upgrade head
```

### 2. Verify Tables Created

```bash
ssh hetzner
docker exec -it trading-bot-postgres psql -U trading_user -d trading_bot
\dt  # Should show 6 new tables (agent_prompts, llm_interactions, etc.)
\d agent_prompts  # Should show table schema
```

### 3. Test Memory Service on VPS

```bash
ssh hetzner
cd /opt/trading-bot
docker exec -it trading-bot python
>>> from src.trading_bot.llm.memory_service import AgentMemory
>>> memory = AgentMemory()
>>> # Test store interaction...
```

---

## FILES CREATED SO FAR

```
D:\Coding\Stocks\
├── api/
│   ├── alembic/
│   │   └── versions/
│   │       └── 003_create_agent_memory.py ✅ (680 lines)
│   └── app/
│       └── models/
│           └── agent_memory.py ✅ (475 lines)
├── src/
│   └── trading_bot/
│       └── llm/
│           └── memory_service.py ✅ (650 lines)
└── MULTI_AGENT_IMPLEMENTATION_GUIDE.md ✅ (this file)
```

---

## ESTIMATED TIME TO COMPLETION

- **Phase 2**: 3-4 hours (BaseAgent, FMPClient, 3 core agents, Orchestrator)
- **Phase 3**: 2-3 hours (NewsAnalyst, RegimeDetector agents)
- **Phase 4**: 2-3 hours (LearningAgent, SelfLearningLoop)
- **Phase 5**: 1-2 hours (Multi-agent workflows, integrate with main.py)
- **Phase 6**: 1-2 hours (Environment config, Docker, VPS deployment)

**Total**: 9-14 hours of focused implementation

---

## SUPPORT & CONTINUATION

To continue implementation:

1. Start with **Task 2.1** (BaseAgent class) using the code skeleton above
2. Test each component incrementally
3. Follow the code patterns established in Phase 1
4. Refer to existing `llm_screener.py` and `llm_optimizer.py` for LLM interaction patterns
5. Use this guide as a roadmap - each task has code skeletons to build from

**Next Session**: Pick up at Phase 2, Task 2.1 (BaseAgent) and continue sequentially.
