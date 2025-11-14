"""Create agent memory and self-learning tables

Revision ID: 003
Revises: 001
Create Date: 2025-11-07

Tables: agent_prompts, llm_interactions, strategy_adjustments, trade_outcomes,
        screener_results, agent_metrics
Enums: outcome_enum, exit_reason_enum, market_regime_enum
Purpose: PostgreSQL long-term memory for multi-agent self-learning system

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '003'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Create agent memory infrastructure for self-learning:
    1. Enum types for outcomes, exit reasons, market regimes
    2. agent_prompts table for prompt versioning and A/B testing
    3. llm_interactions table for tracking every LLM call
    4. strategy_adjustments table for parameter evolution tracking
    5. trade_outcomes table for rich trade metadata
    6. screener_results table for opportunity pattern learning
    7. agent_metrics table for agent performance tracking
    8. Indexes for fast semantic search and analytics
    """

    # ========== ENUMS ==========
    op.execute("""
        CREATE TYPE outcome_enum AS ENUM (
            'IMPROVED', 'WORSENED', 'NEUTRAL', 'PENDING'
        )
    """)

    op.execute("""
        CREATE TYPE exit_reason_enum AS ENUM (
            'stop_loss', 'take_profit', 'time_exit', 'trailing_stop',
            'manual', 'circuit_breaker', 'regime_change'
        )
    """)

    op.execute("""
        CREATE TYPE market_regime_enum AS ENUM (
            'BULL', 'BEAR', 'SIDEWAYS', 'HIGH_VOL', 'LOW_VOL'
        )
    """)

    # ========== AGENT_PROMPTS TABLE ==========
    op.create_table(
        'agent_prompts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()'),
                  comment='Unique prompt identifier'),
        sa.Column('agent_name', sa.String(50), nullable=False,
                  comment='Agent type (research, strategy_builder, risk_manager, etc.)'),
        sa.Column('prompt_version', sa.Integer, nullable=False,
                  comment='Version number for A/B testing'),
        sa.Column('prompt_template', sa.Text, nullable=False,
                  comment='Full prompt template with placeholders'),
        sa.Column('system_message', sa.Text, nullable=True,
                  comment='System-level instructions for this agent'),
        sa.Column('performance_score', sa.Numeric(5, 2), nullable=True,
                  comment='Composite score from outcomes (0-100)'),
        sa.Column('active', sa.Boolean, nullable=False,
                  server_default='true',
                  comment='Whether this prompt is currently in use'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text('NOW()'),
                  comment='When prompt was created'),

        sa.CheckConstraint('prompt_version > 0', name='ck_prompts_version_positive'),
        sa.CheckConstraint(
            'performance_score IS NULL OR (performance_score >= 0 AND performance_score <= 100)',
            name='ck_prompts_score_range'
        ),

        comment='Prompt versioning for A/B testing and continuous improvement'
    )

    op.create_index(
        'idx_agent_prompts_name_active',
        'agent_prompts',
        ['agent_name', 'active'],
        postgresql_using='btree'
    )

    op.create_index(
        'idx_agent_prompts_score',
        'agent_prompts',
        [sa.text('performance_score DESC')],
        postgresql_using='btree'
    )

    # ========== LLM_INTERACTIONS TABLE ==========
    op.create_table(
        'llm_interactions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()'),
                  comment='Unique interaction identifier'),
        sa.Column('agent_name', sa.String(50), nullable=False,
                  comment='Which agent made this call'),
        sa.Column('prompt_id', postgresql.UUID(as_uuid=True), nullable=True,
                  comment='Reference to agent_prompts table'),
        sa.Column('input_context', postgresql.JSONB, nullable=False,
                  comment='Market data and context fed to LLM'),
        sa.Column('output_result', postgresql.JSONB, nullable=True,
                  comment='LLM response (structured data)'),
        sa.Column('model', sa.String(50), nullable=False,
                  comment='Model used (claude-haiku-4.5, etc.)'),
        sa.Column('tokens_used', sa.Integer, nullable=True,
                  comment='Total tokens consumed'),
        sa.Column('cost_usd', sa.Numeric(10, 6), nullable=True,
                  comment='Cost of this call in USD'),
        sa.Column('latency_ms', sa.Integer, nullable=True,
                  comment='API response time in milliseconds'),
        sa.Column('success', sa.Boolean, nullable=False,
                  server_default='true',
                  comment='Whether call succeeded'),
        sa.Column('error_message', sa.Text, nullable=True,
                  comment='Error details if failed'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text('NOW()'),
                  comment='When interaction occurred'),

        sa.ForeignKeyConstraint(
            ['prompt_id'], ['agent_prompts.id'],
            name='fk_llm_interactions_prompt_id',
            ondelete='SET NULL'
        ),

        comment='Tracking every LLM API call for cost analysis and learning'
    )

    op.create_index(
        'idx_llm_interactions_agent_created',
        'llm_interactions',
        ['agent_name', sa.text('created_at DESC')],
        postgresql_using='btree'
    )

    op.create_index(
        'idx_llm_interactions_prompt',
        'llm_interactions',
        ['prompt_id'],
        postgresql_using='btree'
    )

    # GIN index for JSONB queries
    op.create_index(
        'idx_llm_interactions_context_gin',
        'llm_interactions',
        ['input_context'],
        postgresql_using='gin'
    )

    # ========== STRATEGY_ADJUSTMENTS TABLE ==========
    op.create_table(
        'strategy_adjustments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()'),
                  comment='Unique adjustment identifier'),
        sa.Column('parameter_name', sa.String(100), nullable=False,
                  comment='Name of parameter adjusted (rsi_oversold, stop_loss_pct, etc.)'),
        sa.Column('old_value', sa.Numeric(12, 4), nullable=False,
                  comment='Previous parameter value'),
        sa.Column('new_value', sa.Numeric(12, 4), nullable=False,
                  comment='New parameter value'),
        sa.Column('reasoning', sa.Text, nullable=False,
                  comment='LLM explanation for this adjustment'),
        sa.Column('expected_impact', sa.Text, nullable=True,
                  comment='Predicted effect on performance'),
        sa.Column('confidence_score', sa.Numeric(5, 2), nullable=False,
                  comment='LLM confidence (0-100)'),
        sa.Column('proposed_by', sa.String(50), nullable=False,
                  comment='Which agent proposed this'),
        sa.Column('outcome',
                  postgresql.ENUM('IMPROVED', 'WORSENED', 'NEUTRAL', 'PENDING',
                                  name='outcome_enum'),
                  nullable=False,
                  server_default='PENDING',
                  comment='Measured outcome after trial period'),
        sa.Column('sharpe_before', sa.Numeric(6, 3), nullable=True,
                  comment='Sharpe ratio before adjustment'),
        sa.Column('sharpe_after', sa.Numeric(6, 3), nullable=True,
                  comment='Sharpe ratio after adjustment'),
        sa.Column('win_rate_before', sa.Numeric(5, 2), nullable=True,
                  comment='Win rate % before adjustment'),
        sa.Column('win_rate_after', sa.Numeric(5, 2), nullable=True,
                  comment='Win rate % after adjustment'),
        sa.Column('measured_at', sa.TIMESTAMP(timezone=True), nullable=True,
                  comment='When outcome was measured'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text('NOW()'),
                  comment='When adjustment was proposed'),

        sa.CheckConstraint(
            'confidence_score >= 0 AND confidence_score <= 100',
            name='ck_adjustments_confidence_range'
        ),

        comment='Self-learning parameter evolution with outcome tracking'
    )

    op.create_index(
        'idx_strategy_adjustments_param_created',
        'strategy_adjustments',
        ['parameter_name', sa.text('created_at DESC')],
        postgresql_using='btree'
    )

    op.create_index(
        'idx_strategy_adjustments_outcome',
        'strategy_adjustments',
        ['outcome'],
        postgresql_using='btree'
    )

    # ========== TRADE_OUTCOMES TABLE ==========
    op.create_table(
        'trade_outcomes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()'),
                  comment='Unique trade identifier'),
        sa.Column('symbol', sa.String(10), nullable=False,
                  comment='Stock symbol traded'),
        sa.Column('entry_time', sa.TIMESTAMP(timezone=True), nullable=False,
                  comment='When position was entered'),
        sa.Column('exit_time', sa.TIMESTAMP(timezone=True), nullable=False,
                  comment='When position was exited'),
        sa.Column('entry_price', sa.Numeric(10, 2), nullable=False,
                  comment='Entry price per share'),
        sa.Column('exit_price', sa.Numeric(10, 2), nullable=False,
                  comment='Exit price per share'),
        sa.Column('quantity', sa.Integer, nullable=False,
                  comment='Number of shares traded'),
        sa.Column('pnl', sa.Numeric(12, 2), nullable=False,
                  comment='Profit/loss in dollars'),
        sa.Column('return_pct', sa.Numeric(8, 4), nullable=False,
                  comment='Return percentage'),
        sa.Column('setup_type', sa.String(50), nullable=False,
                  comment='Trade setup category (oversold_bounce, breakout, etc.)'),
        sa.Column('entry_reason', sa.Text, nullable=True,
                  comment='Why trade was entered'),
        sa.Column('exit_reason',
                  postgresql.ENUM('stop_loss', 'take_profit', 'time_exit', 'trailing_stop',
                                  'manual', 'circuit_breaker', 'regime_change',
                                  name='exit_reason_enum'),
                  nullable=False,
                  comment='Why trade was exited'),
        sa.Column('market_regime',
                  postgresql.ENUM('BULL', 'BEAR', 'SIDEWAYS', 'HIGH_VOL', 'LOW_VOL',
                                  name='market_regime_enum'),
                  nullable=True,
                  comment='Market regime at entry'),
        sa.Column('vix_at_entry', sa.Numeric(6, 2), nullable=True,
                  comment='VIX value when entered'),
        sa.Column('rsi_at_entry', sa.Numeric(6, 2), nullable=True,
                  comment='RSI value when entered'),
        sa.Column('volume_ratio', sa.Numeric(8, 2), nullable=True,
                  comment='Volume vs average'),
        sa.Column('llm_interaction_id', postgresql.UUID(as_uuid=True), nullable=True,
                  comment='Link to LLM call that generated this trade'),
        sa.Column('strategy_params', postgresql.JSONB, nullable=True,
                  comment='Strategy parameters at time of trade'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text('NOW()'),
                  comment='When record was created'),

        sa.CheckConstraint('quantity > 0', name='ck_trade_outcomes_quantity_positive'),
        sa.CheckConstraint('entry_price > 0', name='ck_trade_outcomes_entry_positive'),
        sa.CheckConstraint('exit_price > 0', name='ck_trade_outcomes_exit_positive'),

        sa.ForeignKeyConstraint(
            ['llm_interaction_id'], ['llm_interactions.id'],
            name='fk_trade_outcomes_llm_interaction_id',
            ondelete='SET NULL'
        ),

        comment='Rich trade metadata for pattern learning and backtesting'
    )

    op.create_index(
        'idx_trade_outcomes_symbol_created',
        'trade_outcomes',
        ['symbol', sa.text('created_at DESC')],
        postgresql_using='btree'
    )

    op.create_index(
        'idx_trade_outcomes_setup_return',
        'trade_outcomes',
        ['setup_type', sa.text('return_pct DESC')],
        postgresql_using='btree'
    )

    op.create_index(
        'idx_trade_outcomes_regime_return',
        'trade_outcomes',
        ['market_regime', sa.text('return_pct DESC')],
        postgresql_using='btree'
    )

    # GIN index for JSONB strategy params
    op.create_index(
        'idx_trade_outcomes_params_gin',
        'trade_outcomes',
        ['strategy_params'],
        postgresql_using='gin'
    )

    # ========== SCREENER_RESULTS TABLE ==========
    op.create_table(
        'screener_results',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()'),
                  comment='Unique screener result identifier'),
        sa.Column('scan_id', postgresql.UUID(as_uuid=True), nullable=False,
                  comment='Group results from same scan run'),
        sa.Column('symbol', sa.String(10), nullable=False,
                  comment='Stock symbol identified'),
        sa.Column('asset_type', sa.String(10), nullable=False,
                  server_default='stock',
                  comment='Asset type (stock, crypto, etf)'),
        sa.Column('filters_matched', postgresql.JSONB, nullable=False,
                  comment='Which screener filters passed'),
        sa.Column('fundamental_snapshot', postgresql.JSONB, nullable=True,
                  comment='FMP fundamental data at scan time'),
        sa.Column('technical_snapshot', postgresql.JSONB, nullable=True,
                  comment='Technical indicators at scan time'),
        sa.Column('composite_score', sa.Numeric(5, 2), nullable=False,
                  comment='Combined opportunity score (0-100)'),
        sa.Column('selected_for_watchlist', sa.Boolean, nullable=False,
                  server_default='false',
                  comment='Whether added to trading watchlist'),
        sa.Column('outcome_7d', sa.Numeric(8, 4), nullable=True,
                  comment='Return % 7 days after scan'),
        sa.Column('outcome_30d', sa.Numeric(8, 4), nullable=True,
                  comment='Return % 30 days after scan'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text('NOW()'),
                  comment='When scan was performed'),

        sa.CheckConstraint(
            'composite_score >= 0 AND composite_score <= 100',
            name='ck_screener_results_score_range'
        ),

        comment='Screener opportunity tracking for pattern learning'
    )

    op.create_index(
        'idx_screener_results_scan',
        'screener_results',
        ['scan_id'],
        postgresql_using='btree'
    )

    op.create_index(
        'idx_screener_results_score_created',
        'screener_results',
        [sa.text('composite_score DESC'), sa.text('created_at DESC')],
        postgresql_using='btree'
    )

    op.create_index(
        'idx_screener_results_watchlist',
        'screener_results',
        ['selected_for_watchlist', sa.text('created_at DESC')],
        postgresql_using='btree'
    )

    # GIN indexes for JSONB filter analysis
    op.create_index(
        'idx_screener_results_filters_gin',
        'screener_results',
        ['filters_matched'],
        postgresql_using='gin'
    )

    # ========== AGENT_METRICS TABLE ==========
    op.create_table(
        'agent_metrics',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()'),
                  comment='Unique metrics record identifier'),
        sa.Column('agent_name', sa.String(50), nullable=False,
                  comment='Agent being measured'),
        sa.Column('date', sa.Date, nullable=False,
                  comment='Date of metrics'),
        sa.Column('tasks_completed', sa.Integer, nullable=False,
                  server_default='0',
                  comment='Number of tasks completed'),
        sa.Column('avg_latency_ms', sa.Integer, nullable=True,
                  comment='Average response time'),
        sa.Column('success_rate', sa.Numeric(5, 2), nullable=True,
                  comment='Success rate percentage (0-100)'),
        sa.Column('avg_confidence', sa.Numeric(5, 2), nullable=True,
                  comment='Average confidence score'),
        sa.Column('impact_on_pnl', sa.Numeric(12, 2), nullable=True,
                  comment='Downstream P&L from this agent'),
        sa.Column('cost_usd', sa.Numeric(10, 4), nullable=False,
                  server_default='0',
                  comment='Total API cost for the day'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text('NOW()'),
                  comment='When metrics were recorded'),

        sa.CheckConstraint(
            'tasks_completed >= 0',
            name='ck_agent_metrics_tasks_nonnegative'
        ),
        sa.CheckConstraint(
            'success_rate IS NULL OR (success_rate >= 0 AND success_rate <= 100)',
            name='ck_agent_metrics_success_rate_range'
        ),
        sa.CheckConstraint(
            'avg_confidence IS NULL OR (avg_confidence >= 0 AND avg_confidence <= 100)',
            name='ck_agent_metrics_confidence_range'
        ),

        comment='Daily performance tracking for each agent'
    )

    op.create_index(
        'idx_agent_metrics_agent_date',
        'agent_metrics',
        ['agent_name', sa.text('date DESC')],
        postgresql_using='btree'
    )

    # Unique constraint on agent + date (one record per agent per day)
    op.create_index(
        'idx_agent_metrics_unique_agent_date',
        'agent_metrics',
        ['agent_name', 'date'],
        unique=True,
        postgresql_using='btree'
    )


def downgrade() -> None:
    """
    Rollback migration:
    1. Drop tables (cascade)
    2. Drop enum types
    """

    # Drop tables in reverse dependency order
    op.drop_table('agent_metrics')
    op.drop_table('screener_results')
    op.drop_table('trade_outcomes')
    op.drop_table('strategy_adjustments')
    op.drop_table('llm_interactions')
    op.drop_table('agent_prompts')

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS market_regime_enum")
    op.execute("DROP TYPE IF EXISTS exit_reason_enum")
    op.execute("DROP TYPE IF EXISTS outcome_enum")
