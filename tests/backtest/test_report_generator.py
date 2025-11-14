"""
Tests for ReportGenerator markdown and JSON report generation.

Tests markdown format, JSON export schema, trade table formatting, and complete report.
Following TDD RED phase - tests written before ReportGenerator implementation.
"""

import json
import pytest
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Tuple

# Import will FAIL because ReportGenerator doesn't exist yet (TDD RED phase)
from src.trading_bot.backtest.report_generator import ReportGenerator
from src.trading_bot.backtest.models import (
    BacktestResult,
    BacktestConfig,
    Trade,
    PerformanceMetrics,
)


def test_markdown_format():
    """
    T050: Test markdown report contains all required sections.

    Given: BacktestResult with complete data
    Expected: Markdown report contains all required sections:
    - # Backtest Report
    - ## Configuration
    - ## Performance Metrics
    - ## Trades
    - ## Equity Curve
    - ## Data Warnings

    Validates ReportGenerator.generate_markdown() produces structured markdown
    with all necessary sections for human-readable backtest analysis.

    TDD RED phase: This test should FAIL (ReportGenerator not implemented yet)
    """
    # Create sample BacktestConfig
    config = BacktestConfig(
        strategy_class=type("DummyStrategy", (), {}),
        symbols=["AAPL", "TSLA"],
        start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
        end_date=datetime(2024, 12, 31, tzinfo=timezone.utc),
        initial_capital=Decimal("100000"),
        commission=Decimal("0.00"),
        slippage_pct=Decimal("0.001"),
        risk_free_rate=Decimal("0.02"),
    )

    # Create sample trade
    trade = Trade(
        symbol="AAPL",
        entry_date=datetime(2024, 1, 2, tzinfo=timezone.utc),
        entry_price=Decimal("100.00"),
        exit_date=datetime(2024, 1, 10, tzinfo=timezone.utc),
        exit_price=Decimal("110.00"),
        shares=100,
        pnl=Decimal("1000.00"),
        pnl_pct=Decimal("0.10"),
        duration_days=8,
        exit_reason="take_profit",
        commission=Decimal("0.00"),
        slippage=Decimal("0.00"),
    )

    # Create sample PerformanceMetrics
    metrics = PerformanceMetrics(
        total_return=Decimal("0.05"),
        annualized_return=Decimal("0.05"),
        cagr=Decimal("0.05"),
        win_rate=Decimal("0.60"),
        profit_factor=Decimal("2.50"),
        average_win=Decimal("1000.00"),
        average_loss=Decimal("-400.00"),
        max_drawdown=Decimal("0.10"),
        max_drawdown_duration_days=30,
        sharpe_ratio=Decimal("1.50"),
        total_trades=5,
        winning_trades=3,
        losing_trades=2,
    )

    # Create sample equity curve
    equity_curve = [
        (datetime(2024, 1, 1, tzinfo=timezone.utc), Decimal("100000")),
        (datetime(2024, 1, 10, tzinfo=timezone.utc), Decimal("101000")),
    ]

    # Create BacktestResult
    result = BacktestResult(
        config=config,
        trades=[trade],
        equity_curve=equity_curve,
        metrics=metrics,
        data_warnings=["Missing data for 2024-02-15"],
        execution_time_seconds=1.5,
        completed_at=datetime(2024, 1, 10, 12, 0, 0, tzinfo=timezone.utc),
    )

    # Generate markdown report
    generator = ReportGenerator()
    markdown = generator.generate_markdown(result)

    # Verify required sections exist
    assert "# Backtest Report" in markdown, "Missing '# Backtest Report' section"
    assert "## Configuration" in markdown, "Missing '## Configuration' section"
    assert "## Performance Metrics" in markdown, "Missing '## Performance Metrics' section"
    assert "## Trades" in markdown, "Missing '## Trades' section"
    assert "## Equity Curve" in markdown, "Missing '## Equity Curve' section"
    assert "## Data Warnings" in markdown, "Missing '## Data Warnings' section"

    # Verify markdown is non-empty
    assert len(markdown) > 100, "Markdown report should contain substantial content"


def test_json_export():
    """
    T051: Test JSON export contains all required data and correct schema.

    Given: BacktestResult with complete data
    Expected: JSON export contains:
    - config (object with strategy, symbols, dates, capital)
    - metrics (object with performance statistics)
    - trades (array of trade objects)
    - equity_curve (array of timestamp/value pairs)

    Validates ReportGenerator.generate_json() produces valid JSON with
    correct schema for programmatic analysis and persistence.

    TDD RED phase: This test should FAIL (ReportGenerator not implemented yet)
    """
    # Create sample BacktestConfig
    config = BacktestConfig(
        strategy_class=type("DummyStrategy", (), {}),
        symbols=["AAPL", "TSLA"],
        start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
        end_date=datetime(2024, 12, 31, tzinfo=timezone.utc),
        initial_capital=Decimal("100000"),
        commission=Decimal("0.00"),
        slippage_pct=Decimal("0.001"),
        risk_free_rate=Decimal("0.02"),
    )

    # Create sample trades
    trades = [
        Trade(
            symbol="AAPL",
            entry_date=datetime(2024, 1, 2, tzinfo=timezone.utc),
            entry_price=Decimal("100.00"),
            exit_date=datetime(2024, 1, 10, tzinfo=timezone.utc),
            exit_price=Decimal("110.00"),
            shares=100,
            pnl=Decimal("1000.00"),
            pnl_pct=Decimal("0.10"),
            duration_days=8,
            exit_reason="take_profit",
            commission=Decimal("0.00"),
            slippage=Decimal("0.00"),
        ),
        Trade(
            symbol="TSLA",
            entry_date=datetime(2024, 1, 11, tzinfo=timezone.utc),
            entry_price=Decimal("200.00"),
            exit_date=datetime(2024, 1, 18, tzinfo=timezone.utc),
            exit_price=Decimal("190.00"),
            shares=50,
            pnl=Decimal("-500.00"),
            pnl_pct=Decimal("-0.05"),
            duration_days=7,
            exit_reason="stop_loss",
            commission=Decimal("0.00"),
            slippage=Decimal("0.00"),
        ),
    ]

    # Create sample PerformanceMetrics
    metrics = PerformanceMetrics(
        total_return=Decimal("0.05"),
        annualized_return=Decimal("0.05"),
        cagr=Decimal("0.05"),
        win_rate=Decimal("0.50"),
        profit_factor=Decimal("2.00"),
        average_win=Decimal("1000.00"),
        average_loss=Decimal("-500.00"),
        max_drawdown=Decimal("0.10"),
        max_drawdown_duration_days=30,
        sharpe_ratio=Decimal("1.50"),
        total_trades=2,
        winning_trades=1,
        losing_trades=1,
    )

    # Create sample equity curve
    equity_curve = [
        (datetime(2024, 1, 1, tzinfo=timezone.utc), Decimal("100000")),
        (datetime(2024, 1, 10, tzinfo=timezone.utc), Decimal("101000")),
        (datetime(2024, 1, 18, tzinfo=timezone.utc), Decimal("100500")),
    ]

    # Create BacktestResult
    result = BacktestResult(
        config=config,
        trades=trades,
        equity_curve=equity_curve,
        metrics=metrics,
        data_warnings=["Missing data for 2024-02-15"],
        execution_time_seconds=2.5,
        completed_at=datetime(2024, 1, 18, 12, 0, 0, tzinfo=timezone.utc),
    )

    # Generate JSON report
    generator = ReportGenerator()
    json_str = generator.generate_json(result)

    # Parse and validate JSON
    data = json.loads(json_str)

    # Verify top-level keys exist
    assert "config" in data, "JSON missing 'config' key"
    assert "metrics" in data, "JSON missing 'metrics' key"
    assert "trades" in data, "JSON missing 'trades' key"
    assert "equity_curve" in data, "JSON missing 'equity_curve' key"

    # Verify types
    assert isinstance(data["trades"], list), "trades should be a list"
    assert isinstance(data["metrics"], dict), "metrics should be a dict"
    assert isinstance(data["config"], dict), "config should be a dict"
    assert isinstance(data["equity_curve"], list), "equity_curve should be a list"

    # Verify trade count matches
    assert len(data["trades"]) == 2, f"Expected 2 trades in JSON, got {len(data['trades'])}"

    # Verify equity curve count matches
    assert len(data["equity_curve"]) == 3, f"Expected 3 equity points in JSON, got {len(data['equity_curve'])}"


def test_trade_table_formatting():
    """
    T052: Test trade table formatting contains all required columns.

    Given: List of trades with entry/exit data
    Expected: Formatted table contains columns:
    - Symbol
    - Entry Date
    - Exit Price
    - P&L

    Validates ReportGenerator._format_trade_table() produces readable
    markdown table with all essential trade information.

    TDD RED phase: This test should FAIL (ReportGenerator not implemented yet)
    """
    # Create sample trades
    trades = [
        Trade(
            symbol="AAPL",
            entry_date=datetime(2024, 1, 2, tzinfo=timezone.utc),
            entry_price=Decimal("100.00"),
            exit_date=datetime(2024, 1, 10, tzinfo=timezone.utc),
            exit_price=Decimal("110.00"),
            shares=100,
            pnl=Decimal("1000.00"),
            pnl_pct=Decimal("0.10"),
            duration_days=8,
            exit_reason="take_profit",
            commission=Decimal("0.00"),
            slippage=Decimal("0.00"),
        ),
        Trade(
            symbol="TSLA",
            entry_date=datetime(2024, 1, 11, tzinfo=timezone.utc),
            entry_price=Decimal("200.00"),
            exit_date=datetime(2024, 1, 18, tzinfo=timezone.utc),
            exit_price=Decimal("190.00"),
            shares=50,
            pnl=Decimal("-500.00"),
            pnl_pct=Decimal("-0.05"),
            duration_days=7,
            exit_reason="stop_loss",
            commission=Decimal("0.00"),
            slippage=Decimal("0.00"),
        ),
    ]

    # Generate trade table
    generator = ReportGenerator()
    table = generator._format_trade_table(trades)

    # Verify table structure (markdown table format)
    assert "Symbol" in table, "Table missing 'Symbol' column header"
    assert "Entry Date" in table, "Table missing 'Entry Date' column header"
    assert "Exit Price" in table, "Table missing 'Exit Price' column header"
    assert "P&L" in table, "Table missing 'P&L' column header"

    # Verify trade data appears in table
    assert "AAPL" in table, "Table missing AAPL symbol data"
    assert "TSLA" in table, "Table missing TSLA symbol data"
    assert "1000.00" in table or "1,000.00" in table, "Table missing AAPL P&L data"
    assert "-500.00" in table or "-500.00" in table, "Table missing TSLA P&L data"

    # Verify table is non-empty
    assert len(table) > 50, "Trade table should contain substantial content"


def test_complete_report():
    """
    T053: Test complete report generation with all data.

    Given: Full BacktestResult with trades, metrics, equity curve, warnings
    Expected:
    - Both markdown and JSON generated successfully
    - Both formats non-empty
    - Trade counts consistent across formats

    Validates ReportGenerator can produce both report formats from same
    BacktestResult with data consistency between formats.

    TDD RED phase: This test should FAIL (ReportGenerator not implemented yet)
    """
    # Create comprehensive BacktestConfig
    config = BacktestConfig(
        strategy_class=type("DummyStrategy", (), {}),
        symbols=["AAPL", "TSLA", "GOOGL"],
        start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
        end_date=datetime(2024, 12, 31, tzinfo=timezone.utc),
        initial_capital=Decimal("100000"),
        commission=Decimal("1.00"),
        slippage_pct=Decimal("0.001"),
        risk_free_rate=Decimal("0.02"),
    )

    # Create comprehensive trade history
    trades = [
        Trade(
            symbol="AAPL",
            entry_date=datetime(2024, 1, 2, tzinfo=timezone.utc),
            entry_price=Decimal("100.00"),
            exit_date=datetime(2024, 1, 10, tzinfo=timezone.utc),
            exit_price=Decimal("110.00"),
            shares=100,
            pnl=Decimal("998.00"),  # $1000 - $2 commission
            pnl_pct=Decimal("0.0998"),
            duration_days=8,
            exit_reason="take_profit",
            commission=Decimal("2.00"),
            slippage=Decimal("0.00"),
        ),
        Trade(
            symbol="TSLA",
            entry_date=datetime(2024, 1, 11, tzinfo=timezone.utc),
            entry_price=Decimal("200.00"),
            exit_date=datetime(2024, 1, 18, tzinfo=timezone.utc),
            exit_price=Decimal("190.00"),
            shares=50,
            pnl=Decimal("-502.00"),  # -$500 - $2 commission
            pnl_pct=Decimal("-0.0502"),
            duration_days=7,
            exit_reason="stop_loss",
            commission=Decimal("2.00"),
            slippage=Decimal("0.00"),
        ),
        Trade(
            symbol="GOOGL",
            entry_date=datetime(2024, 1, 19, tzinfo=timezone.utc),
            entry_price=Decimal("150.00"),
            exit_date=datetime(2024, 1, 28, tzinfo=timezone.utc),
            exit_price=Decimal("165.00"),
            shares=75,
            pnl=Decimal("1123.00"),  # $1125 - $2 commission
            pnl_pct=Decimal("0.0998"),
            duration_days=9,
            exit_reason="take_profit",
            commission=Decimal("2.00"),
            slippage=Decimal("0.00"),
        ),
    ]

    # Create comprehensive PerformanceMetrics
    metrics = PerformanceMetrics(
        total_return=Decimal("0.01619"),  # ($100k + $998 - $502 + $1123) / $100k - 1
        annualized_return=Decimal("0.20628"),  # Annualized from Jan-Feb period
        cagr=Decimal("0.20628"),
        win_rate=Decimal("0.6667"),  # 2 wins out of 3 trades
        profit_factor=Decimal("4.226"),  # ($998 + $1123) / $502
        average_win=Decimal("1060.50"),  # ($998 + $1123) / 2
        average_loss=Decimal("-502.00"),
        max_drawdown=Decimal("0.00495"),  # 0.495% max drawdown
        max_drawdown_duration_days=8,
        sharpe_ratio=Decimal("1.75"),
        total_trades=3,
        winning_trades=2,
        losing_trades=1,
    )

    # Create comprehensive equity curve
    equity_curve = [
        (datetime(2024, 1, 1, tzinfo=timezone.utc), Decimal("100000.00")),
        (datetime(2024, 1, 10, tzinfo=timezone.utc), Decimal("100998.00")),
        (datetime(2024, 1, 18, tzinfo=timezone.utc), Decimal("100496.00")),
        (datetime(2024, 1, 28, tzinfo=timezone.utc), Decimal("101619.00")),
    ]

    # Create BacktestResult with warnings
    result = BacktestResult(
        config=config,
        trades=trades,
        equity_curve=equity_curve,
        metrics=metrics,
        data_warnings=[
            "Missing data for 2024-02-15",
            "Low volume detected for TSLA on 2024-01-12",
        ],
        execution_time_seconds=3.5,
        completed_at=datetime(2024, 1, 28, 12, 0, 0, tzinfo=timezone.utc),
    )

    # Generate both formats
    generator = ReportGenerator()
    markdown = generator.generate_markdown(result)
    json_str = generator.generate_json(result)

    # Verify both generated successfully
    assert len(markdown) > 0, "Markdown report should not be empty"
    assert len(json_str) > 0, "JSON report should not be empty"

    # Verify consistency - parse JSON to check trade count
    json_data = json.loads(json_str)
    assert len(json_data["trades"]) == len(result.trades), (
        f"JSON trade count {len(json_data['trades'])} doesn't match "
        f"result trade count {len(result.trades)}"
    )

    # Verify markdown contains key data
    assert "AAPL" in markdown, "Markdown missing AAPL trade data"
    assert "TSLA" in markdown, "Markdown missing TSLA trade data"
    assert "GOOGL" in markdown, "Markdown missing GOOGL trade data"
    assert "Missing data for 2024-02-15" in markdown, "Markdown missing warning data"

    # Verify JSON contains key data
    assert json_data["metrics"]["total_trades"] == 3, "JSON missing correct total_trades"
    assert json_data["metrics"]["winning_trades"] == 2, "JSON missing correct winning_trades"
    assert len(json_data["equity_curve"]) == 4, "JSON missing correct equity_curve length"
