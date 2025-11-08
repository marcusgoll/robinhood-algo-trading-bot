#!/usr/bin/env python3
"""
Initialize agent memory tables in PostgreSQL database.
Run this directly on VPS to create multi-agent system tables.

Usage:
    python scripts/init_agent_tables.py
"""
import os
import sys
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    print("ERROR: DATABASE_URL not found in environment variables")
    sys.exit(1)

def create_agent_tables():
    """Create all agent memory tables and enums."""

    conn = None
    try:
        # Connect to database
        print(f"Connecting to database...")
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()

        print("Creating ENUM types...")

        # Create ENUM types
        cursor.execute("""
            CREATE TYPE IF NOT EXISTS outcome_enum AS ENUM (
                'IMPROVED', 'WORSENED', 'NEUTRAL', 'PENDING'
            )
        """)

        cursor.execute("""
            CREATE TYPE IF NOT EXISTS exit_reason_enum AS ENUM (
                'stop_loss', 'take_profit', 'time_exit', 'trailing_stop',
                'manual', 'circuit_breaker', 'regime_change'
            )
        """)

        cursor.execute("""
            CREATE TYPE IF NOT EXISTS market_regime_enum AS ENUM (
                'BULL', 'BEAR', 'SIDEWAYS', 'HIGH_VOL', 'LOW_VOL'
            )
        """)

        print("✓ ENUM types created")

        # Create agent_prompts table
        print("Creating agent_prompts table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_prompts (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                agent_name VARCHAR(50) NOT NULL,
                prompt_version INTEGER NOT NULL,
                prompt_template TEXT NOT NULL,
                system_message TEXT,
                performance_score NUMERIC(5, 2),
                active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

                CONSTRAINT ck_prompts_version_positive CHECK (prompt_version > 0),
                CONSTRAINT ck_prompts_score_range CHECK (
                    performance_score IS NULL OR
                    (performance_score >= 0 AND performance_score <= 100)
                )
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_agent_prompts_name_active
            ON agent_prompts (agent_name, active)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_agent_prompts_score
            ON agent_prompts (performance_score DESC)
        """)

        print("✓ agent_prompts table created")

        # Create llm_interactions table
        print("Creating llm_interactions table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS llm_interactions (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                agent_name VARCHAR(50) NOT NULL,
                prompt_id UUID REFERENCES agent_prompts(id) ON DELETE SET NULL,
                input_context JSONB NOT NULL,
                output_result JSONB,
                model VARCHAR(50) NOT NULL,
                tokens_used INTEGER,
                cost_usd NUMERIC(10, 6),
                latency_ms INTEGER,
                success BOOLEAN NOT NULL DEFAULT TRUE,
                error_message TEXT,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_llm_interactions_agent_created
            ON llm_interactions (agent_name, created_at DESC)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_llm_interactions_prompt
            ON llm_interactions (prompt_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_llm_interactions_context_gin
            ON llm_interactions USING GIN (input_context)
        """)

        print("✓ llm_interactions table created")

        # Create strategy_adjustments table
        print("Creating strategy_adjustments table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS strategy_adjustments (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                parameter_name VARCHAR(100) NOT NULL,
                old_value NUMERIC(12, 4) NOT NULL,
                new_value NUMERIC(12, 4) NOT NULL,
                reasoning TEXT NOT NULL,
                expected_impact TEXT,
                confidence_score NUMERIC(5, 2) NOT NULL,
                proposed_by VARCHAR(50) NOT NULL,
                outcome outcome_enum NOT NULL DEFAULT 'PENDING',
                sharpe_before NUMERIC(6, 3),
                sharpe_after NUMERIC(6, 3),
                win_rate_before NUMERIC(5, 2),
                win_rate_after NUMERIC(5, 2),
                measured_at TIMESTAMP WITH TIME ZONE,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

                CONSTRAINT ck_adjustments_confidence_range CHECK (
                    confidence_score >= 0 AND confidence_score <= 100
                )
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_strategy_adjustments_param_created
            ON strategy_adjustments (parameter_name, created_at DESC)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_strategy_adjustments_outcome
            ON strategy_adjustments (outcome)
        """)

        print("✓ strategy_adjustments table created")

        # Create trade_outcomes table
        print("Creating trade_outcomes table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trade_outcomes (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                symbol VARCHAR(10) NOT NULL,
                entry_time TIMESTAMP WITH TIME ZONE NOT NULL,
                exit_time TIMESTAMP WITH TIME ZONE NOT NULL,
                entry_price NUMERIC(10, 2) NOT NULL,
                exit_price NUMERIC(10, 2) NOT NULL,
                quantity INTEGER NOT NULL,
                pnl NUMERIC(12, 2) NOT NULL,
                return_pct NUMERIC(8, 4) NOT NULL,
                setup_type VARCHAR(50) NOT NULL,
                entry_reason TEXT,
                exit_reason exit_reason_enum NOT NULL,
                market_regime market_regime_enum,
                vix_at_entry NUMERIC(6, 2),
                rsi_at_entry NUMERIC(6, 2),
                volume_ratio NUMERIC(8, 2),
                llm_interaction_id UUID REFERENCES llm_interactions(id) ON DELETE SET NULL,
                strategy_params JSONB,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

                CONSTRAINT ck_trade_outcomes_quantity_positive CHECK (quantity > 0),
                CONSTRAINT ck_trade_outcomes_entry_positive CHECK (entry_price > 0),
                CONSTRAINT ck_trade_outcomes_exit_positive CHECK (exit_price > 0)
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_trade_outcomes_symbol_created
            ON trade_outcomes (symbol, created_at DESC)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_trade_outcomes_setup_return
            ON trade_outcomes (setup_type, return_pct DESC)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_trade_outcomes_regime_return
            ON trade_outcomes (market_regime, return_pct DESC)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_trade_outcomes_params_gin
            ON trade_outcomes USING GIN (strategy_params)
        """)

        print("✓ trade_outcomes table created")

        # Create screener_results table
        print("Creating screener_results table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS screener_results (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                scan_id UUID NOT NULL,
                symbol VARCHAR(10) NOT NULL,
                asset_type VARCHAR(10) NOT NULL DEFAULT 'stock',
                filters_matched JSONB NOT NULL,
                fundamental_snapshot JSONB,
                technical_snapshot JSONB,
                composite_score NUMERIC(5, 2) NOT NULL,
                selected_for_watchlist BOOLEAN NOT NULL DEFAULT FALSE,
                outcome_7d NUMERIC(8, 4),
                outcome_30d NUMERIC(8, 4),
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

                CONSTRAINT ck_screener_results_score_range CHECK (
                    composite_score >= 0 AND composite_score <= 100
                )
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_screener_results_scan
            ON screener_results (scan_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_screener_results_score_created
            ON screener_results (composite_score DESC, created_at DESC)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_screener_results_watchlist
            ON screener_results (selected_for_watchlist, created_at DESC)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_screener_results_filters_gin
            ON screener_results USING GIN (filters_matched)
        """)

        print("✓ screener_results table created")

        # Create agent_metrics table
        print("Creating agent_metrics table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_metrics (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                agent_name VARCHAR(50) NOT NULL,
                date DATE NOT NULL,
                tasks_completed INTEGER NOT NULL DEFAULT 0,
                avg_latency_ms INTEGER,
                success_rate NUMERIC(5, 2),
                avg_confidence NUMERIC(5, 2),
                impact_on_pnl NUMERIC(12, 2),
                cost_usd NUMERIC(10, 4) NOT NULL DEFAULT 0,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

                CONSTRAINT ck_agent_metrics_tasks_nonnegative CHECK (tasks_completed >= 0),
                CONSTRAINT ck_agent_metrics_success_rate_range CHECK (
                    success_rate IS NULL OR
                    (success_rate >= 0 AND success_rate <= 100)
                ),
                CONSTRAINT ck_agent_metrics_confidence_range CHECK (
                    avg_confidence IS NULL OR
                    (avg_confidence >= 0 AND avg_confidence <= 100)
                )
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_agent_metrics_agent_date
            ON agent_metrics (agent_name, date DESC)
        """)

        cursor.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_agent_metrics_unique_agent_date
            ON agent_metrics (agent_name, date)
        """)

        print("✓ agent_metrics table created")

        # Commit all changes
        conn.commit()

        print("\n" + "="*60)
        print("SUCCESS: All agent memory tables created!")
        print("="*60)
        print("\nTables created:")
        print("  1. agent_prompts")
        print("  2. llm_interactions")
        print("  3. strategy_adjustments")
        print("  4. trade_outcomes")
        print("  5. screener_results")
        print("  6. agent_metrics")
        print("\nNext steps:")
        print("  1. Test multi-agent system:")
        print("     python -m trading_bot.llm.examples.multi_agent_consensus_workflow")
        print("  2. Start trading bot with MULTI_AGENT_ENABLED=true")

    except Exception as e:
        print(f"\nERROR: Failed to create tables: {e}")
        if conn:
            conn.rollback()
        sys.exit(1)
    finally:
        if conn:
            cursor.close()
            conn.close()

if __name__ == '__main__':
    create_agent_tables()
