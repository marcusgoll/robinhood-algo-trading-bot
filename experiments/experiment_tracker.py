#!/usr/bin/env python3
"""Experiment tracking system for Phase 3 systematic research.

Manages SQLite database of all experiment runs, results, and model artifacts.
"""

import sqlite3
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import pandas as pd


class ExperimentTracker:
    """Track and store experiment results in SQLite database."""

    def __init__(self, db_path: str = "experiments.db"):
        """Initialize experiment tracker.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.conn = None
        self._initialize_db()

    def _initialize_db(self):
        """Create database schema if not exists."""
        self.conn = sqlite3.connect(self.db_path)
        cursor = self.conn.cursor()

        # Main experiments table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS experiments (
                experiment_id TEXT PRIMARY KEY,
                config_hash TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT,
                duration_seconds REAL,

                -- Data configuration
                symbol TEXT NOT NULL,
                data_period TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                num_samples INTEGER,
                train_samples INTEGER,
                val_samples INTEGER,
                test_samples INTEGER,

                -- Model configuration
                model_name TEXT NOT NULL,
                model_type TEXT NOT NULL,
                model_params TEXT,

                -- Feature configuration
                feature_set TEXT NOT NULL,
                num_features INTEGER,

                -- Training configuration
                horizon_bars INTEGER NOT NULL,
                horizon_name TEXT NOT NULL,
                batch_size INTEGER,
                learning_rate REAL,
                max_epochs INTEGER,
                actual_epochs INTEGER,
                weight_decay REAL,

                -- Validation method
                validation_method TEXT NOT NULL,
                cv_folds INTEGER,

                -- Performance metrics
                directional_accuracy REAL,
                mse REAL,
                rmse REAL,
                mae REAL,
                r2 REAL,

                -- Trading metrics (if available)
                sharpe_ratio REAL,
                max_drawdown REAL,
                win_rate REAL,
                profit_factor REAL,

                -- Additional info
                notes TEXT,
                error_message TEXT,

                -- Config snapshot
                full_config TEXT
            )
        """)

        # Ensemble experiments table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ensemble_experiments (
                ensemble_id TEXT PRIMARY KEY,
                config_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                completed_at TEXT,

                -- Base models
                base_model_ids TEXT NOT NULL,  -- JSON array of experiment_ids
                ensemble_method TEXT NOT NULL,
                ensemble_params TEXT,

                -- Performance
                directional_accuracy REAL,
                mse REAL,
                rmse REAL,
                mae REAL,
                r2 REAL,

                -- Improvement over best base model
                improvement_pct REAL,

                full_config TEXT
            )
        """)

        # Model artifacts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS model_artifacts (
                artifact_id TEXT PRIMARY KEY,
                experiment_id TEXT NOT NULL,
                artifact_type TEXT NOT NULL,  -- 'model', 'predictions', 'features'
                file_path TEXT NOT NULL,
                created_at TEXT NOT NULL,
                file_size_bytes INTEGER,

                FOREIGN KEY (experiment_id) REFERENCES experiments (experiment_id)
            )
        """)

        # Experiment phases tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS experiment_phases (
                phase_id TEXT PRIMARY KEY,
                phase_name TEXT NOT NULL,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                total_experiments INTEGER,
                completed_experiments INTEGER,
                failed_experiments INTEGER,
                best_result REAL,
                best_experiment_id TEXT
            )
        """)

        # Create indices
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_status ON experiments(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_directional_acc ON experiments(directional_accuracy DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_model_type ON experiments(model_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON experiments(created_at DESC)")

        self.conn.commit()

    def generate_experiment_id(self, config: Dict[str, Any]) -> str:
        """Generate unique experiment ID from configuration.

        Args:
            config: Experiment configuration dict

        Returns:
            Unique experiment ID (first 12 chars of SHA256)
        """
        # Create deterministic hash from config
        config_str = json.dumps(config, sort_keys=True)
        hash_obj = hashlib.sha256(config_str.encode())
        return hash_obj.hexdigest()[:12]

    def start_experiment(self, config: Dict[str, Any]) -> str:
        """Register new experiment start.

        Args:
            config: Full experiment configuration

        Returns:
            experiment_id
        """
        experiment_id = self.generate_experiment_id(config)
        config_hash = hashlib.sha256(
            json.dumps(config, sort_keys=True).encode()
        ).hexdigest()

        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO experiments (
                experiment_id, config_hash, status, created_at, started_at,
                symbol, data_period, timeframe,
                model_name, model_type, model_params,
                feature_set, horizon_bars, horizon_name,
                batch_size, learning_rate, max_epochs, weight_decay,
                validation_method, full_config
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            experiment_id,
            config_hash,
            "running",
            datetime.utcnow().isoformat(),
            datetime.utcnow().isoformat(),
            config.get("symbol", "SPY"),
            config.get("data_period", "1yr"),
            config.get("timeframe", "5min"),
            config.get("model_name", "unknown"),
            config.get("model_type", "unknown"),
            json.dumps(config.get("model_params", {})),
            config.get("feature_set", "base"),
            config.get("horizon_bars", 12),
            config.get("horizon_name", "12bar"),
            config.get("batch_size", 32),
            config.get("learning_rate", 0.001),
            config.get("max_epochs", 30),
            config.get("weight_decay", 0.01),
            config.get("validation_method", "holdout"),
            json.dumps(config)
        ))
        self.conn.commit()

        return experiment_id

    def complete_experiment(
        self,
        experiment_id: str,
        results: Dict[str, Any],
        status: str = "completed"
    ):
        """Record experiment completion and results.

        Args:
            experiment_id: Experiment ID
            results: Results dictionary with metrics
            status: 'completed' or 'failed'
        """
        cursor = self.conn.cursor()

        # Get start time to calculate duration
        cursor.execute(
            "SELECT started_at FROM experiments WHERE experiment_id = ?",
            (experiment_id,)
        )
        row = cursor.fetchone()
        if row:
            started_at = datetime.fromisoformat(row[0])
            duration = (datetime.utcnow() - started_at).total_seconds()
        else:
            duration = None

        cursor.execute("""
            UPDATE experiments SET
                status = ?,
                completed_at = ?,
                duration_seconds = ?,
                num_samples = ?,
                train_samples = ?,
                val_samples = ?,
                test_samples = ?,
                num_features = ?,
                actual_epochs = ?,
                directional_accuracy = ?,
                mse = ?,
                rmse = ?,
                mae = ?,
                r2 = ?,
                sharpe_ratio = ?,
                max_drawdown = ?,
                win_rate = ?,
                profit_factor = ?,
                error_message = ?
            WHERE experiment_id = ?
        """, (
            status,
            datetime.utcnow().isoformat(),
            duration,
            results.get("num_samples"),
            results.get("train_samples"),
            results.get("val_samples"),
            results.get("test_samples"),
            results.get("num_features"),
            results.get("actual_epochs"),
            results.get("directional_accuracy"),
            results.get("mse"),
            results.get("rmse"),
            results.get("mae"),
            results.get("r2"),
            results.get("sharpe_ratio"),
            results.get("max_drawdown"),
            results.get("win_rate"),
            results.get("profit_factor"),
            results.get("error_message"),
            experiment_id
        ))
        self.conn.commit()

    def get_leaderboard(self, limit: int = 20, metric: str = "directional_accuracy") -> pd.DataFrame:
        """Get top experiments by metric.

        Args:
            limit: Number of top experiments to return
            metric: Metric to sort by

        Returns:
            DataFrame with top experiments
        """
        query = f"""
            SELECT
                experiment_id,
                model_name,
                feature_set,
                horizon_name,
                data_period,
                directional_accuracy,
                mse,
                rmse,
                mae,
                r2,
                train_samples,
                actual_epochs,
                duration_seconds,
                created_at
            FROM experiments
            WHERE status = 'completed'
            ORDER BY {metric} DESC
            LIMIT ?
        """
        return pd.read_sql_query(query, self.conn, params=(limit,))

    def get_experiment_by_config(self, config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Check if experiment with this config already exists.

        Args:
            config: Experiment configuration

        Returns:
            Existing experiment results or None
        """
        experiment_id = self.generate_experiment_id(config)
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM experiments WHERE experiment_id = ? AND status = 'completed'",
            (experiment_id,)
        )
        row = cursor.fetchone()

        if row:
            cols = [desc[0] for desc in cursor.description]
            return dict(zip(cols, row))
        return None

    def get_best_models(self, top_n: int = 10) -> List[str]:
        """Get experiment IDs of top N models by directional accuracy.

        Args:
            top_n: Number of top models

        Returns:
            List of experiment IDs
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT experiment_id
            FROM experiments
            WHERE status = 'completed' AND directional_accuracy IS NOT NULL
            ORDER BY directional_accuracy DESC
            LIMIT ?
        """, (top_n,))
        return [row[0] for row in cursor.fetchall()]

    def add_ensemble_result(
        self,
        base_experiment_ids: List[str],
        ensemble_method: str,
        ensemble_params: Dict[str, Any],
        results: Dict[str, Any]
    ) -> str:
        """Record ensemble experiment result.

        Args:
            base_experiment_ids: List of base model experiment IDs
            ensemble_method: Name of ensemble method
            ensemble_params: Ensemble configuration
            results: Ensemble performance results

        Returns:
            ensemble_id
        """
        config = {
            "base_models": base_experiment_ids,
            "method": ensemble_method,
            "params": ensemble_params
        }
        ensemble_id = self.generate_experiment_id(config)
        config_hash = hashlib.sha256(
            json.dumps(config, sort_keys=True).encode()
        ).hexdigest()

        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO ensemble_experiments (
                ensemble_id, config_hash, created_at, completed_at,
                base_model_ids, ensemble_method, ensemble_params,
                directional_accuracy, mse, rmse, mae, r2,
                improvement_pct, full_config
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            ensemble_id,
            config_hash,
            datetime.utcnow().isoformat(),
            datetime.utcnow().isoformat(),
            json.dumps(base_experiment_ids),
            ensemble_method,
            json.dumps(ensemble_params),
            results.get("directional_accuracy"),
            results.get("mse"),
            results.get("rmse"),
            results.get("mae"),
            results.get("r2"),
            results.get("improvement_pct"),
            json.dumps(config)
        ))
        self.conn.commit()

        return ensemble_id

    def get_phase_summary(self) -> pd.DataFrame:
        """Get summary of all experiment phases.

        Returns:
            DataFrame with phase summaries
        """
        return pd.read_sql_query(
            "SELECT * FROM experiment_phases ORDER BY started_at",
            self.conn
        )

    def export_to_csv(self, output_path: str = "experiment_results.csv"):
        """Export all experiment results to CSV.

        Args:
            output_path: Path for CSV output
        """
        df = pd.read_sql_query("SELECT * FROM experiments", self.conn)
        df.to_csv(output_path, index=False)
        print(f"Exported {len(df)} experiments to {output_path}")

    def get_statistics(self) -> Dict[str, Any]:
        """Get overall experiment statistics.

        Returns:
            Dictionary with statistics
        """
        cursor = self.conn.cursor()

        stats = {}

        # Total experiments
        cursor.execute("SELECT COUNT(*) FROM experiments")
        stats["total_experiments"] = cursor.fetchone()[0]

        # Completed experiments
        cursor.execute("SELECT COUNT(*) FROM experiments WHERE status = 'completed'")
        stats["completed"] = cursor.fetchone()[0]

        # Failed experiments
        cursor.execute("SELECT COUNT(*) FROM experiments WHERE status = 'failed'")
        stats["failed"] = cursor.fetchone()[0]

        # Running experiments
        cursor.execute("SELECT COUNT(*) FROM experiments WHERE status = 'running'")
        stats["running"] = cursor.fetchone()[0]

        # Best result
        cursor.execute("""
            SELECT MAX(directional_accuracy), experiment_id
            FROM experiments
            WHERE status = 'completed'
        """)
        row = cursor.fetchone()
        stats["best_accuracy"] = row[0]
        stats["best_experiment_id"] = row[1]

        # Average accuracy
        cursor.execute("""
            SELECT AVG(directional_accuracy)
            FROM experiments
            WHERE status = 'completed' AND directional_accuracy IS NOT NULL
        """)
        stats["avg_accuracy"] = cursor.fetchone()[0]

        return stats

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()


if __name__ == "__main__":
    # Test the tracker
    tracker = ExperimentTracker("experiments_test.db")

    # Test experiment
    config = {
        "symbol": "SPY",
        "data_period": "1yr",
        "timeframe": "5min",
        "model_name": "lstm_medium",
        "model_type": "regression_lstm",
        "model_params": {"hidden_dim": 64, "num_layers": 2},
        "feature_set": "base_micro",
        "horizon_bars": 12,
        "horizon_name": "12bar",
        "batch_size": 32,
        "learning_rate": 0.001,
        "max_epochs": 30,
        "weight_decay": 0.01,
        "validation_method": "holdout"
    }

    exp_id = tracker.start_experiment(config)
    print(f"Started experiment: {exp_id}")

    # Simulate results
    results = {
        "num_samples": 10000,
        "train_samples": 6000,
        "val_samples": 2000,
        "test_samples": 2000,
        "num_features": 57,
        "actual_epochs": 25,
        "directional_accuracy": 0.555,
        "mse": 0.0004,
        "rmse": 0.02,
        "mae": 0.015,
        "r2": -0.01
    }

    tracker.complete_experiment(exp_id, results)
    print(f"Completed experiment: {exp_id}")

    # Get statistics
    stats = tracker.get_statistics()
    print(f"\nStatistics: {stats}")

    # Get leaderboard
    leaderboard = tracker.get_leaderboard(limit=10)
    print(f"\nLeaderboard:\n{leaderboard}")

    tracker.close()
    print("\nTest complete!")
