"""Agent memory models for self-learning multi-agent trading system.

Tables:
- AgentPrompt: Prompt versioning and A/B testing
- LLMInteraction: Every LLM call logged for cost analysis
- StrategyAdjustment: Parameter evolution with outcome tracking
- TradeOutcome: Rich trade metadata for pattern learning
- ScreenerResult: Opportunity tracking with forward-looking outcomes
- AgentMetric: Daily agent performance dashboard
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import (
    Boolean, Column, Date, Enum, ForeignKey, Integer,
    Numeric, String, Text, text
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from .base import BaseModel, GUID


class AgentPrompt(BaseModel):
    """
    Prompt versioning for A/B testing and continuous improvement.

    Allows tracking which prompt formulations perform best for each agent type.
    Performance score is calculated from downstream outcomes (trade P&L, etc.).
    """

    __tablename__ = 'agent_prompts'

    agent_name = Column(
        String(50),
        nullable=False,
        comment='Agent type (research, strategy_builder, risk_manager, etc.)'
    )

    prompt_version = Column(
        Integer,
        nullable=False,
        comment='Version number for A/B testing'
    )

    prompt_template = Column(
        Text,
        nullable=False,
        comment='Full prompt template with placeholders'
    )

    system_message = Column(
        Text,
        nullable=True,
        comment='System-level instructions for this agent'
    )

    performance_score = Column(
        Numeric(5, 2),
        nullable=True,
        comment='Composite score from outcomes (0-100)'
    )

    active = Column(
        Boolean,
        nullable=False,
        server_default=text('true'),
        comment='Whether this prompt is currently in use'
    )

    # Relationships
    interactions = relationship(
        'LLMInteraction',
        back_populates='prompt',
        cascade='all, delete-orphan'
    )


class LLMInteraction(BaseModel):
    """
    Tracking every LLM API call for cost analysis and learning.

    Logs input context, output, model used, tokens consumed, cost, latency.
    Links to specific prompt version used and can be linked to trade outcomes.
    """

    __tablename__ = 'llm_interactions'

    agent_name = Column(
        String(50),
        nullable=False,
        comment='Which agent made this call'
    )

    prompt_id = Column(
        GUID,
        ForeignKey('agent_prompts.id', ondelete='SET NULL'),
        nullable=True,
        comment='Reference to agent_prompts table'
    )

    input_context = Column(
        JSONB,
        nullable=False,
        comment='Market data and context fed to LLM'
    )

    output_result = Column(
        JSONB,
        nullable=True,
        comment='LLM response (structured data)'
    )

    model = Column(
        String(50),
        nullable=False,
        comment='Model used (claude-haiku-4.5, etc.)'
    )

    tokens_used = Column(
        Integer,
        nullable=True,
        comment='Total tokens consumed'
    )

    cost_usd = Column(
        Numeric(10, 6),
        nullable=True,
        comment='Cost of this call in USD'
    )

    latency_ms = Column(
        Integer,
        nullable=True,
        comment='API response time in milliseconds'
    )

    success = Column(
        Boolean,
        nullable=False,
        server_default=text('true'),
        comment='Whether call succeeded'
    )

    error_message = Column(
        Text,
        nullable=True,
        comment='Error details if failed'
    )

    # Relationships
    prompt = relationship('AgentPrompt', back_populates='interactions')
    trade_outcomes = relationship('TradeOutcome', back_populates='llm_interaction')


class StrategyAdjustment(BaseModel):
    """
    Self-learning parameter evolution with outcome tracking.

    When LLM proposes parameter changes, stores the reasoning, confidence,
    and measured outcomes (before/after Sharpe ratio, win rate, etc.).
    """

    __tablename__ = 'strategy_adjustments'

    parameter_name = Column(
        String(100),
        nullable=False,
        comment='Name of parameter adjusted (rsi_oversold, stop_loss_pct, etc.)'
    )

    old_value = Column(
        Numeric(12, 4),
        nullable=False,
        comment='Previous parameter value'
    )

    new_value = Column(
        Numeric(12, 4),
        nullable=False,
        comment='New parameter value'
    )

    reasoning = Column(
        Text,
        nullable=False,
        comment='LLM explanation for this adjustment'
    )

    expected_impact = Column(
        Text,
        nullable=True,
        comment='Predicted effect on performance'
    )

    confidence_score = Column(
        Numeric(5, 2),
        nullable=False,
        comment='LLM confidence (0-100)'
    )

    proposed_by = Column(
        String(50),
        nullable=False,
        comment='Which agent proposed this'
    )

    outcome = Column(
        Enum('IMPROVED', 'WORSENED', 'NEUTRAL', 'PENDING', name='outcome_enum'),
        nullable=False,
        server_default=text("'PENDING'"),
        comment='Measured outcome after trial period'
    )

    sharpe_before = Column(
        Numeric(6, 3),
        nullable=True,
        comment='Sharpe ratio before adjustment'
    )

    sharpe_after = Column(
        Numeric(6, 3),
        nullable=True,
        comment='Sharpe ratio after adjustment'
    )

    win_rate_before = Column(
        Numeric(5, 2),
        nullable=True,
        comment='Win rate % before adjustment'
    )

    win_rate_after = Column(
        Numeric(5, 2),
        nullable=True,
        comment='Win rate % after adjustment'
    )

    measured_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment='When outcome was measured'
    )


class TradeOutcome(BaseModel):
    """
    Rich trade metadata for pattern learning and backtesting.

    Every closed trade logged with entry/exit details, P&L, setup type,
    market regime, technical indicators at entry, and link to LLM call
    that generated the trade.
    """

    __tablename__ = 'trade_outcomes'

    symbol = Column(
        String(10),
        nullable=False,
        comment='Stock symbol traded'
    )

    entry_time = Column(
        DateTime(timezone=True),
        nullable=False,
        comment='When position was entered'
    )

    exit_time = Column(
        DateTime(timezone=True),
        nullable=False,
        comment='When position was exited'
    )

    entry_price = Column(
        Numeric(10, 2),
        nullable=False,
        comment='Entry price per share'
    )

    exit_price = Column(
        Numeric(10, 2),
        nullable=False,
        comment='Exit price per share'
    )

    quantity = Column(
        Integer,
        nullable=False,
        comment='Number of shares traded'
    )

    pnl = Column(
        Numeric(12, 2),
        nullable=False,
        comment='Profit/loss in dollars'
    )

    return_pct = Column(
        Numeric(8, 4),
        nullable=False,
        comment='Return percentage'
    )

    setup_type = Column(
        String(50),
        nullable=False,
        comment='Trade setup category (oversold_bounce, breakout, etc.)'
    )

    entry_reason = Column(
        Text,
        nullable=True,
        comment='Why trade was entered'
    )

    exit_reason = Column(
        Enum(
            'stop_loss', 'take_profit', 'time_exit', 'trailing_stop',
            'manual', 'circuit_breaker', 'regime_change',
            name='exit_reason_enum'
        ),
        nullable=False,
        comment='Why trade was exited'
    )

    market_regime = Column(
        Enum('BULL', 'BEAR', 'SIDEWAYS', 'HIGH_VOL', 'LOW_VOL', name='market_regime_enum'),
        nullable=True,
        comment='Market regime at entry'
    )

    vix_at_entry = Column(
        Numeric(6, 2),
        nullable=True,
        comment='VIX value when entered'
    )

    rsi_at_entry = Column(
        Numeric(6, 2),
        nullable=True,
        comment='RSI value when entered'
    )

    volume_ratio = Column(
        Numeric(8, 2),
        nullable=True,
        comment='Volume vs average'
    )

    llm_interaction_id = Column(
        GUID,
        ForeignKey('llm_interactions.id', ondelete='SET NULL'),
        nullable=True,
        comment='Link to LLM call that generated this trade'
    )

    strategy_params = Column(
        JSONB,
        nullable=True,
        comment='Strategy parameters at time of trade'
    )

    # Relationships
    llm_interaction = relationship('LLMInteraction', back_populates='trade_outcomes')


class ScreenerResult(BaseModel):
    """
    Screener opportunity tracking for pattern learning.

    Every stock identified by screener logged with filters matched,
    fundamental/technical snapshot, composite score, and forward-looking
    outcomes (7-day and 30-day returns).
    """

    __tablename__ = 'screener_results'

    scan_id = Column(
        GUID,
        nullable=False,
        comment='Group results from same scan run'
    )

    symbol = Column(
        String(10),
        nullable=False,
        comment='Stock symbol identified'
    )

    asset_type = Column(
        String(10),
        nullable=False,
        server_default=text("'stock'"),
        comment='Asset type (stock, crypto, etf)'
    )

    filters_matched = Column(
        JSONB,
        nullable=False,
        comment='Which screener filters passed'
    )

    fundamental_snapshot = Column(
        JSONB,
        nullable=True,
        comment='FMP fundamental data at scan time'
    )

    technical_snapshot = Column(
        JSONB,
        nullable=True,
        comment='Technical indicators at scan time'
    )

    composite_score = Column(
        Numeric(5, 2),
        nullable=False,
        comment='Combined opportunity score (0-100)'
    )

    selected_for_watchlist = Column(
        Boolean,
        nullable=False,
        server_default=text('false'),
        comment='Whether added to trading watchlist'
    )

    outcome_7d = Column(
        Numeric(8, 4),
        nullable=True,
        comment='Return % 7 days after scan'
    )

    outcome_30d = Column(
        Numeric(8, 4),
        nullable=True,
        comment='Return % 30 days after scan'
    )


class AgentMetric(BaseModel):
    """
    Daily performance tracking for each agent.

    Aggregated metrics per agent per day: tasks completed, success rate,
    average latency, downstream P&L impact, API costs.
    """

    __tablename__ = 'agent_metrics'

    agent_name = Column(
        String(50),
        nullable=False,
        comment='Agent being measured'
    )

    date = Column(
        Date,
        nullable=False,
        comment='Date of metrics'
    )

    tasks_completed = Column(
        Integer,
        nullable=False,
        server_default=text('0'),
        comment='Number of tasks completed'
    )

    avg_latency_ms = Column(
        Integer,
        nullable=True,
        comment='Average response time'
    )

    success_rate = Column(
        Numeric(5, 2),
        nullable=True,
        comment='Success rate percentage (0-100)'
    )

    avg_confidence = Column(
        Numeric(5, 2),
        nullable=True,
        comment='Average confidence score'
    )

    impact_on_pnl = Column(
        Numeric(12, 2),
        nullable=True,
        comment='Downstream P&L from this agent'
    )

    cost_usd = Column(
        Numeric(10, 4),
        nullable=False,
        server_default=text('0'),
        comment='Total API cost for the day'
    )
