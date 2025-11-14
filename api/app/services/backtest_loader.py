"""Service for loading backtest results from filesystem."""

import json
from functools import lru_cache
from pathlib import Path
from typing import Optional

from ..schemas.backtest import BacktestSummary, BacktestDetailResponse


class BacktestLoader:
    """Load backtest JSON files from filesystem."""

    def __init__(self, backtest_dir: str = "backtest_results"):
        """Initialize loader with backtest directory path."""
        self.backtest_dir = Path(backtest_dir)

    def list_backtests(
        self,
        strategy: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> list[BacktestSummary]:
        """
        List all backtests with optional filtering.

        Args:
            strategy: Filter by strategy name
            start_date: Filter by start date (ISO format)
            end_date: Filter by end date (ISO format)

        Returns:
            List of backtest summaries sorted by created_at (newest first)
        """
        results = []

        if not self.backtest_dir.exists():
            return results

        for file in self.backtest_dir.glob("*.json"):
            try:
                data = json.loads(file.read_text())

                # Apply filters
                if strategy and data["config"]["strategy"] != strategy:
                    continue
                if start_date and data["config"]["start_date"] < start_date:
                    continue
                if end_date and data["config"]["end_date"] > end_date:
                    continue

                summary = BacktestSummary(
                    id=file.stem,
                    strategy=data["config"]["strategy"],
                    symbols=data["config"]["symbols"],
                    start_date=data["config"]["start_date"],
                    end_date=data["config"]["end_date"],
                    total_return=data["metrics"]["total_return"],
                    win_rate=data["metrics"]["win_rate"],
                    total_trades=data["metrics"]["total_trades"],
                    created_at=data["metadata"]["completed_at"],
                )
                results.append(summary)

            except (json.JSONDecodeError, KeyError) as e:
                # Skip malformed files
                print(f"Warning: Skipping {file.name}: {e}")
                continue

        # Sort by created_at (newest first)
        results.sort(key=lambda x: x.created_at, reverse=True)
        return results

    @lru_cache(maxsize=128)  # 10-minute cache (TTL handled by LRU eviction)
    def get_backtest(self, backtest_id: str) -> Optional[BacktestDetailResponse]:
        """
        Get full backtest details by ID.

        Args:
            backtest_id: Backtest identifier (filename without extension)

        Returns:
            Full backtest result or None if not found
        """
        file_path = self.backtest_dir / f"{backtest_id}.json"

        if not file_path.exists():
            return None

        try:
            data = json.loads(file_path.read_text())
            return BacktestDetailResponse(**data)
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Error loading {backtest_id}: {e}")
            return None
