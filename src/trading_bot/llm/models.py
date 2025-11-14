"""SQLAlchemy models for multi-agent system PostgreSQL database.

These models match the schema created by scripts/init_agent_tables.py
"""

import os
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    Column, String, Integer, Numeric, DateTime, Date, Boolean,
    Text, ForeignKey, Index, UniqueConstraint, create_engine,
    Enum as SQLEnum
)
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

Base = declarative_base()


# ============ ENUM TYPES ============

# These match the PostgreSQL ENUM types created in init_agent_tables.py
OUTCOME_ENUM = ['IMPROVED', 'WORSENED', 'NEUTRAL', 'PENDING']
EXIT_REASON_ENUM = [
    'stop_loss', 'take_profit', 'time_exit', 'trailing_stop',
    'manual', 'circuit_breaker', 'regime_change'
]
MARKET_REGIME_ENUM = ['BULL', 'BEAR', 'SIDEWAYS', 'HIGH_VOL', 'LOW_VOL']


# ============ MODEL DEFINITIONS ============

class AgentPrompt(Base):
    """
    Prompt version control for multi-agent system.

    Tracks evolution of prompts over time for reproducibility
    and A/B testing different prompt strategies.
    """
    __tablename__ = 'agent_prompts'

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, server_default='gen_random_uuid()')
    agent_name = Column(String(50), nullable=False, index=True)
    prompt_version = Column(String(20), nullable=False)
    prompt_template = Column(Text, nullable=False)
    description = Column(Text)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    llm_interactions = relationship('LLMInteraction', back_populates='prompt')

    __table_args__ = (
        UniqueConstraint('agent_name', 'prompt_version', name='uq_agent_prompt_version'),
        Index('idx_agent_prompts_agent_active', 'agent_name', 'active'),
    )


class LLMInteraction(Base):
    """
    Every LLM API call with cost tracking and performance metrics.

    Links calls to prompts and downstream trade outcomes for
    ROI analysis and cost optimization.
    """
    __tablename__ = 'llm_interactions'

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, server_default='gen_random_uuid()')
    agent_name = Column(String(50), nullable=False, index=True)
    prompt_id = Column(PostgresUUID(as_uuid=True), ForeignKey('agent_prompts.id'))
    input_context = Column(JSONB, nullable=False)
    output_result = Column(JSONB)
    model = Column(String(50), nullable=False)
    tokens_used = Column(Integer)
    cost_usd = Column(Numeric(10, 6))
    latency_ms = Column(Integer)
    success = Column(Boolean, default=True, nullable=False)
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    prompt = relationship('AgentPrompt', back_populates='llm_interactions')
    trade_outcomes = relationship('TradeOutcome', back_populates='llm_interaction')

    __table_args__ = (
        Index('idx_llm_interactions_agent_created', 'agent_name', 'created_at'),
        Index('idx_llm_interactions_model', 'model'),
    )


class StrategyAdjustment(Base):
    """
    Parameter adjustment proposals with measured outcomes.

    Tracks self-learning loop: what adjustments were proposed,
    why, and whether they improved performance.
    """
    __tablename__ = 'strategy_adjustments'

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, server_default='gen_random_uuid()')
    parameter_name = Column(String(100), nullable=False, index=True)
    old_value = Column(Numeric(10, 4), nullable=False)
    new_value = Column(Numeric(10, 4), nullable=False)
    reasoning = Column(Text, nullable=False)
    expected_impact = Column(Text)
    confidence_score = Column(Numeric(5, 2), nullable=False)
    proposed_by = Column(String(50), nullable=False)
    outcome = Column(
        SQLEnum(*OUTCOME_ENUM, name='outcome_enum', create_type=False),
        default='PENDING',
        nullable=False,
        index=True
    )
    sharpe_before = Column(Numeric(10, 4))
    sharpe_after = Column(Numeric(10, 4))
    win_rate_before = Column(Numeric(5, 2))
    win_rate_after = Column(Numeric(5, 2))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    measured_at = Column(DateTime)

    __table_args__ = (
        Index('idx_strategy_adjustments_param', 'parameter_name'),
        Index('idx_strategy_adjustments_outcome', 'outcome'),
    )


class TradeOutcome(Base):
    """
    Completed trade records with full context for pattern learning.

    Links trades to the LLM interactions that generated them and
    captures market regime, indicators, and strategy params.
    """
    __tablename__ = 'trade_outcomes'

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, server_default='gen_random_uuid()')
    symbol = Column(String(20), nullable=False, index=True)
    entry_time = Column(DateTime, nullable=False)
    exit_time = Column(DateTime, nullable=False)
    entry_price = Column(Numeric(12, 4), nullable=False)
    exit_price = Column(Numeric(12, 4), nullable=False)
    quantity = Column(Integer, nullable=False)
    pnl = Column(Numeric(12, 2), nullable=False)
    return_pct = Column(Numeric(8, 4), nullable=False, index=True)
    setup_type = Column(String(50), nullable=False, index=True)
    entry_reason = Column(Text)
    exit_reason = Column(
        SQLEnum(*EXIT_REASON_ENUM, name='exit_reason_enum', create_type=False),
        nullable=False
    )
    market_regime = Column(
        SQLEnum(*MARKET_REGIME_ENUM, name='market_regime_enum', create_type=False)
    )
    vix_at_entry = Column(Numeric(6, 2))
    rsi_at_entry = Column(Numeric(5, 2))
    volume_ratio = Column(Numeric(6, 2))
    llm_interaction_id = Column(PostgresUUID(as_uuid=True), ForeignKey('llm_interactions.id'))
    strategy_params = Column(JSONB)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    llm_interaction = relationship('LLMInteraction', back_populates='trade_outcomes')

    __table_args__ = (
        Index('idx_trade_outcomes_symbol', 'symbol'),
        Index('idx_trade_outcomes_setup_regime', 'setup_type', 'market_regime'),
        Index('idx_trade_outcomes_return', 'return_pct'),
    )


class ScreenerResult(Base):
    """
    Screener candidates with forward-looking outcome tracking.

    Measures screener effectiveness: which filters/scores
    predict future outperformance?
    """
    __tablename__ = 'screener_results'

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, server_default='gen_random_uuid()')
    scan_id = Column(PostgresUUID(as_uuid=True), nullable=False, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    asset_type = Column(String(20), default='stock', nullable=False)
    filters_matched = Column(JSONB, nullable=False)
    fundamental_snapshot = Column(JSONB)
    technical_snapshot = Column(JSONB)
    composite_score = Column(Numeric(5, 2), nullable=False)
    selected_for_watchlist = Column(Boolean, default=False, nullable=False)
    outcome_7d = Column(Numeric(8, 4))
    outcome_30d = Column(Numeric(8, 4))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    __table_args__ = (
        Index('idx_screener_results_scan', 'scan_id'),
        Index('idx_screener_results_score', 'composite_score'),
    )


class AgentMetric(Base):
    """
    Daily performance metrics per agent.

    Tracks productivity, cost, and downstream impact for
    multi-agent system optimization.
    """
    __tablename__ = 'agent_metrics'

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, server_default='gen_random_uuid()')
    agent_name = Column(String(50), nullable=False)
    date = Column(Date, nullable=False)
    tasks_completed = Column(Integer, default=0, nullable=False)
    avg_latency_ms = Column(Integer)
    success_rate = Column(Numeric(5, 2))
    avg_confidence = Column(Numeric(5, 2))
    impact_on_pnl = Column(Numeric(12, 2))
    cost_usd = Column(Numeric(10, 2), default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint('agent_name', 'date', name='uq_agent_metrics_date'),
        Index('idx_agent_metrics_date', 'date'),
    )


# ============ DATABASE SESSION FACTORY ============

def get_database_url() -> str:
    """
    Get PostgreSQL connection URL from environment.

    Returns:
        Database URL string

    Raises:
        ValueError: If DATABASE_URL not set
    """
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        raise ValueError(
            "DATABASE_URL environment variable not set. "
            "Required format: postgresql://user:password@host:port/database"
        )
    return db_url


def create_session_factory():
    """
    Create SQLAlchemy session factory.

    Returns:
        Configured sessionmaker

    Raises:
        ValueError: If DATABASE_URL not configured
    """
    db_url = get_database_url()

    engine = create_engine(
        db_url,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,  # Verify connections before using
        echo=False  # Set to True for SQL debugging
    )

    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Global session factory (lazy initialization)
_SessionLocal = None


def get_session_factory():
    """
    Get or create the global session factory.

    Returns:
        Configured sessionmaker
    """
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = create_session_factory()
    return _SessionLocal


def SessionLocal():
    """
    Create a new database session.

    Returns:
        SQLAlchemy Session instance

    Usage:
        session = SessionLocal()
        try:
            # Use session
            ...
        finally:
            session.close()
    """
    factory = get_session_factory()
    return factory()
