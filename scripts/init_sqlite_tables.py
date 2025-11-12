#!/usr/bin/env python3
"""
Initialize agent memory tables in SQLite database for paper trading.
Run this to create multi-agent system tables in SQLite.

Usage:
    python scripts/init_sqlite_tables.py
"""
import os
import sys
import sqlite3
from pathlib import Path

# Get DATABASE_URL from environment
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:////app/logs/trading_bot.db')

# Extract SQLite path from DATABASE_URL
if DATABASE_URL.startswith('sqlite:///'):
    db_path = DATABASE_URL.replace('sqlite:///', '')
else:
    print(f"ERROR: Expected SQLite DATABASE_URL, got: {DATABASE_URL}")
    sys.exit(1)

def create_agent_tables():
    """Create all agent memory tables for SQLite."""

    # Create parent directory if it doesn't exist
    db_dir = Path(db_path).parent
    db_dir.mkdir(parents=True, exist_ok=True)

    print(f"Connecting to SQLite database: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Create agent_prompts table
        print("Creating agent_prompts table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_prompts (
                id TEXT PRIMARY KEY,
                agent_name TEXT NOT NULL,
                prompt_version TEXT NOT NULL,
                prompt_template TEXT NOT NULL,
                description TEXT,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)

        cursor.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS uq_agent_prompt_version
            ON agent_prompts (agent_name, prompt_version)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_agent_prompts_agent_active
            ON agent_prompts (agent_name, active)
        """)

        print("✓ agent_prompts table created")

        # Create llm_interactions table
        print("Creating llm_interactions table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS llm_interactions (
                id TEXT PRIMARY KEY,
                agent_name TEXT NOT NULL,
                prompt_id TEXT,
                input_context TEXT NOT NULL,
                output_result TEXT,
                model TEXT NOT NULL,
                tokens_used INTEGER,
                cost_usd REAL,
                latency_ms INTEGER,
                success INTEGER NOT NULL DEFAULT 1,
                error_message TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (prompt_id) REFERENCES agent_prompts(id) ON DELETE SET NULL
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_llm_interactions_agent_created
            ON llm_interactions (agent_name, created_at)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_llm_interactions_model
            ON llm_interactions (model)
        """)

        print("✓ llm_interactions table created")

        # Create strategy_adjustments table
        print("Creating strategy_adjustments table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS strategy_adjustments (
                id TEXT PRIMARY KEY,
                parameter_name TEXT NOT NULL,
                old_value REAL NOT NULL,
                new_value REAL NOT NULL,
                reasoning TEXT NOT NULL,
                expected_impact TEXT,
                confidence_score REAL NOT NULL,
                proposed_by TEXT NOT NULL,
                outcome TEXT NOT NULL DEFAULT 'PENDING',
                sharpe_before REAL,
                sharpe_after REAL,
                win_rate_before REAL,
                win_rate_after REAL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                measured_at TEXT
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_strategy_adjustments_param
            ON strategy_adjustments (parameter_name)
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
                id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                entry_time TEXT NOT NULL,
                exit_time TEXT NOT NULL,
                entry_price REAL NOT NULL,
                exit_price REAL NOT NULL,
                quantity INTEGER NOT NULL,
                pnl REAL NOT NULL,
                return_pct REAL NOT NULL,
                setup_type TEXT NOT NULL,
                entry_reason TEXT,
                exit_reason TEXT NOT NULL,
                market_regime TEXT,
                vix_at_entry REAL,
                rsi_at_entry REAL,
                volume_ratio REAL,
                llm_interaction_id TEXT,
                strategy_params TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (llm_interaction_id) REFERENCES llm_interactions(id)
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_trade_outcomes_symbol
            ON trade_outcomes (symbol)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_trade_outcomes_setup_regime
            ON trade_outcomes (setup_type, market_regime)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_trade_outcomes_return
            ON trade_outcomes (return_pct)
        """)

        print("✓ trade_outcomes table created")

        # Create screener_results table
        print("Creating screener_results table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS screener_results (
                id TEXT PRIMARY KEY,
                scan_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                asset_type TEXT NOT NULL DEFAULT 'stock',
                filters_matched TEXT NOT NULL,
                fundamental_snapshot TEXT,
                technical_snapshot TEXT,
                composite_score REAL NOT NULL,
                selected_for_watchlist INTEGER NOT NULL DEFAULT 0,
                outcome_7d REAL,
                outcome_30d REAL,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_screener_results_scan
            ON screener_results (scan_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_screener_results_score
            ON screener_results (composite_score)
        """)

        print("✓ screener_results table created")

        # Create agent_metrics table
        print("Creating agent_metrics table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_metrics (
                id TEXT PRIMARY KEY,
                agent_name TEXT NOT NULL,
                date TEXT NOT NULL,
                tasks_completed INTEGER NOT NULL DEFAULT 0,
                avg_latency_ms INTEGER,
                success_rate REAL,
                avg_confidence REAL,
                impact_on_pnl REAL,
                cost_usd REAL NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)

        cursor.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS uq_agent_metrics_date
            ON agent_metrics (agent_name, date)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_agent_metrics_date
            ON agent_metrics (date)
        """)

        print("✓ agent_metrics table created")

        # Commit all changes
        conn.commit()
        print("\n✅ All tables created successfully!")
        print(f"Database location: {db_path}")

    except Exception as e:
        print(f"\n❌ Error creating tables: {e}")
        conn.rollback()
        raise

    finally:
        conn.close()

if __name__ == '__main__':
    create_agent_tables()
