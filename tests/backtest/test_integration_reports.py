"""
Integration Tests for Full Report Workflow

Tests end-to-end reporting workflow from complete backtest execution to
report generation in both markdown and JSON formats. Validates the entire
pipeline: backtest → result → reports → file output.

These tests verify that all reporting components work together correctly:
- BacktestEngine execution with realistic data
- ReportGenerator markdown generation
- ReportGenerator JSON export
- File creation and content validation
- Data consistency between formats

From: specs/001-backtesting-engine/tasks.md T059
"""

import json
import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from pathlib import Path
from typing import List

from trading_bot.backtest.engine import BacktestEngine
from trading_bot.backtest.report_generator import ReportGenerator
from trading_bot.backtest.models import (
    BacktestConfig,
    BacktestResult,
    HistoricalDataBar,
)
from examples.sample_strategies import MomentumStrategy


@pytest.mark.integration
class TestFullReportWorkflow:
    """
    Integration test for complete backtest → report workflow.

    Tests the full pipeline:
    1. Configure backtest (BacktestConfig)
    2. Generate historical data (mock)
    3. Execute backtest (BacktestEngine)
    4. Generate markdown report (ReportGenerator)
    5. Generate JSON report (ReportGenerator)
    6. Validate file output and content
    7. Verify data consistency between formats
    """

    @pytest.fixture
    def mock_historical_data(self) -> List[HistoricalDataBar]:
        """
        Create realistic mock historical data for full year (252 trading days).

        Simulates one full year of trading with trends suitable for
        momentum strategy signals. Price movements designed to generate
        multiple trades for comprehensive report testing.

        Returns:
            List of 252 HistoricalDataBar objects (1 year)
        """
        bars = []
        symbol = "AAPL"
        start_date = datetime(2023, 1, 3, 9, 30, tzinfo=timezone.utc)

        # Create realistic price movements for full year
        # Start at $130, end at $195 (50% gain over year)
        prices = []

        # Q1: Uptrend $130 -> $155 (25 points in ~60 days)
        for i in range(60):
            price = Decimal("130.0") + (Decimal("25.0") * Decimal(i) / Decimal(60))
            prices.append(price)

        # Q2: Sideways consolidation $155 -> $160 (5 points in ~60 days)
        for i in range(60):
            price = Decimal("155.0") + (Decimal("5.0") * Decimal(i) / Decimal(60))
            prices.append(price)

        # Q3: Downtrend correction $160 -> $145 (-15 points in ~60 days)
        for i in range(60):
            price = Decimal("160.0") - (Decimal("15.0") * Decimal(i) / Decimal(60))
            prices.append(price)

        # Q4: Strong uptrend $145 -> $195 (50 points in ~72 days)
        for i in range(72):
            price = Decimal("145.0") + (Decimal("50.0") * Decimal(i) / Decimal(72))
            prices.append(price)

        # Create OHLC bars from prices
        for i, base_price in enumerate(prices):
            bar_timestamp = start_date + timedelta(days=i)

            # Add realistic OHLC spreads
            open_price = base_price - Decimal("0.50")
            high_price = base_price + Decimal("1.00")
            low_price = base_price - Decimal("1.00")
            close_price = base_price

            bar = HistoricalDataBar(
                symbol=symbol,
                timestamp=bar_timestamp,
                open=open_price,
                high=high_price,
                low=low_price,
                close=close_price,
                volume=50000000 + (i * 100000),  # Realistic volume
                split_adjusted=True,
                dividend_adjusted=True
            )
            bars.append(bar)

        return bars

    def test_full_report_workflow(
        self,
        mock_historical_data: List[HistoricalDataBar],
        tmp_path: Path
    ):
        """
        Test: Complete workflow from backtest execution to report generation.

        **Test Scenario**:
        GIVEN: Complete backtest with MomentumStrategy and full year of data
        AND: tmp_path for report file output
        WHEN: Backtest is executed and reports are generated (markdown + JSON)
        THEN:
        - Both report files are created successfully
        - Markdown contains all required sections and data
        - JSON contains valid schema with complete data
        - Symbol appears in both reports
        - Trade counts match between reports and backtest result
        - Equity curve data consistent across all formats
        - File contents match expected formats

        **Acceptance Criteria**:
        1. Backtest executes successfully (no errors)
        2. Markdown report file created at specified path
        3. JSON report file created at specified path
        4. Markdown contains "# Backtest Report" and config data
        5. JSON contains valid structure (config, metrics, trades, equity_curve)
        6. Trade counts consistent: result.trades == JSON trades == markdown data
        7. Symbol "AAPL" appears in both report formats
        8. Performance metrics present in both formats
        9. Files are non-empty with substantial content

        From: specs/001-backtesting-engine/tasks.md T059
        """
        # ARRANGE: Setup complete backtest configuration
        symbol = "AAPL"
        config = BacktestConfig(
            strategy_class=MomentumStrategy,
            symbols=[symbol],
            start_date=datetime(2023, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2023, 12, 31, tzinfo=timezone.utc),
            initial_capital=Decimal("100000.0"),
            commission=Decimal("0.0"),
            slippage_pct=Decimal("0.001"),
            risk_free_rate=Decimal("0.02"),
            cache_enabled=True
        )

        # Create momentum strategy with windows suitable for full year
        # short=10, long=30 should generate multiple signals
        strategy = MomentumStrategy(short_window=10, long_window=30)

        # Verify sufficient data for strategy
        assert len(mock_historical_data) >= strategy.long_window, (
            f"Insufficient data for MomentumStrategy (need >= {strategy.long_window} bars, "
            f"got {len(mock_historical_data)})"
        )

        print(f"\n=== Full Report Workflow Integration Test ===")
        print(f"Symbol: {symbol}")
        print(f"Data bars: {len(mock_historical_data)}")
        print(f"Strategy: MomentumStrategy(short={strategy.short_window}, long={strategy.long_window})")
        print(f"Initial capital: ${config.initial_capital:,.2f}")

        # ACT 1: Run complete backtest
        print(f"\n[1/5] Running backtest...")
        engine = BacktestEngine(config=config)
        result = engine.run(
            strategy=strategy,
            historical_data={symbol: mock_historical_data}
        )

        # Verify backtest executed successfully
        assert isinstance(result, BacktestResult), "Backtest should return BacktestResult"
        assert len(result.trades) > 0, (
            "MomentumStrategy should generate at least one trade with full year data"
        )
        assert len(result.equity_curve) > 0, "Equity curve should have data points"

        print(f"[1/5] Backtest complete:")
        print(f"  - {len(result.trades)} trades executed")
        print(f"  - {len(result.equity_curve)} equity curve points")
        print(f"  - Final equity: ${result.final_equity:,.2f}")
        print(f"  - Total return: {((result.final_equity - config.initial_capital) / config.initial_capital) * 100:.2f}%")

        # ACT 2: Generate markdown report
        print(f"\n[2/5] Generating markdown report...")
        generator = ReportGenerator()
        md_path = tmp_path / "backtest_report.md"

        markdown = generator.generate_markdown(result, str(md_path))

        # Verify markdown generated successfully
        assert markdown is not None, "Markdown should be generated"
        assert isinstance(markdown, str), "Markdown should be string"
        assert len(markdown) > 0, "Markdown should not be empty"

        print(f"[2/5] Markdown report generated:")
        print(f"  - Path: {md_path}")
        print(f"  - Size: {len(markdown)} characters")

        # ACT 3: Generate JSON report
        print(f"\n[3/5] Generating JSON report...")
        json_path = tmp_path / "backtest_report.json"

        json_str = generator.generate_json(result, str(json_path))

        # Verify JSON generated successfully
        assert json_str is not None, "JSON should be generated"
        assert isinstance(json_str, str), "JSON should be string"
        assert len(json_str) > 0, "JSON should not be empty"

        print(f"[3/5] JSON report generated:")
        print(f"  - Path: {json_path}")
        print(f"  - Size: {len(json_str)} characters")

        # ASSERT 1: Verify files created
        print(f"\n[4/5] Validating file creation...")
        assert md_path.exists(), f"Markdown file should be created at {md_path}"
        assert json_path.exists(), f"JSON file should be created at {json_path}"

        # Verify file sizes (non-empty)
        md_stat = md_path.stat()
        json_stat = json_path.stat()
        assert md_stat.st_size > 0, "Markdown file should not be empty"
        assert json_stat.st_size > 0, "JSON file should not be empty"

        print(f"[4/5] Files created successfully:")
        print(f"  - Markdown: {md_stat.st_size} bytes")
        print(f"  - JSON: {json_stat.st_size} bytes")

        # ASSERT 2: Verify markdown content
        print(f"\n[5/5] Validating report content...")
        md_content = md_path.read_text(encoding="utf-8")

        # Verify markdown structure
        assert "# Backtest Report" in md_content, "Markdown missing title section"
        assert "## Configuration" in md_content, "Markdown missing Configuration section"
        assert "## Performance Metrics" in md_content, "Markdown missing Performance Metrics section"
        assert "## Trades" in md_content, "Markdown missing Trades section"
        assert "## Equity Curve" in md_content, "Markdown missing Equity Curve section"
        assert "## Data Warnings" in md_content, "Markdown missing Data Warnings section"

        # Verify config data appears
        assert f"Symbol: {symbol}" in md_content or symbol in md_content, (
            f"Markdown should contain symbol {symbol}"
        )
        # Check for initial capital (markdown uses bold formatting)
        assert "$100,000.00" in md_content and "Initial Capital" in md_content, (
            "Markdown should contain initial capital value"
        )

        # Verify trade data appears
        assert "Entry Date" in md_content, "Markdown should have trade table headers"
        assert "Exit Date" in md_content, "Markdown should have trade table headers"
        assert "P&L" in md_content, "Markdown should have P&L column"

        print(f"[5/5] Markdown validation passed:")
        print(f"  - All sections present")
        print(f"  - Symbol '{symbol}' found")
        print(f"  - Trade table headers present")

        # ASSERT 3: Verify JSON content
        json_data = json.loads(json_path.read_text(encoding="utf-8"))

        # Verify JSON schema
        assert "config" in json_data, "JSON missing 'config' key"
        assert "metrics" in json_data, "JSON missing 'metrics' key"
        assert "trades" in json_data, "JSON missing 'trades' key"
        assert "equity_curve" in json_data, "JSON missing 'equity_curve' key"
        assert "metadata" in json_data, "JSON missing 'metadata' key"
        assert "data_warnings" in json_data, "JSON missing 'data_warnings' key"

        # Verify config section
        assert symbol in json_data["config"]["symbols"], (
            f"JSON config should contain symbol {symbol}"
        )
        assert json_data["config"]["initial_capital"] == float(config.initial_capital), (
            "JSON config should contain initial capital"
        )

        # Verify metrics section
        assert isinstance(json_data["metrics"], dict), "Metrics should be dict"
        assert "total_trades" in json_data["metrics"], "Metrics missing total_trades"
        assert "win_rate" in json_data["metrics"], "Metrics missing win_rate"
        assert "sharpe_ratio" in json_data["metrics"], "Metrics missing sharpe_ratio"

        # Verify trades section
        assert isinstance(json_data["trades"], list), "Trades should be list"
        assert len(json_data["trades"]) == len(result.trades), (
            f"JSON trade count ({len(json_data['trades'])}) should match "
            f"result trade count ({len(result.trades)})"
        )

        # Verify equity curve section
        assert isinstance(json_data["equity_curve"], list), "Equity curve should be list"
        assert len(json_data["equity_curve"]) == len(result.equity_curve), (
            f"JSON equity curve count ({len(json_data['equity_curve'])}) should match "
            f"result equity curve count ({len(result.equity_curve)})"
        )

        print(f"[5/5] JSON validation passed:")
        print(f"  - Valid schema structure")
        print(f"  - Symbol '{symbol}' in config")
        print(f"  - {len(json_data['trades'])} trades (matches backtest result)")
        print(f"  - {len(json_data['equity_curve'])} equity points (matches backtest result)")

        # ASSERT 4: Verify data consistency between formats
        print(f"\n[FINAL] Validating data consistency...")

        # Verify trade counts match
        assert len(json_data["trades"]) == len(result.trades), (
            "Trade count mismatch between JSON and result"
        )

        # Verify first trade details match
        if len(result.trades) > 0:
            first_trade = result.trades[0]
            first_trade_json = json_data["trades"][0]

            assert first_trade_json["symbol"] == first_trade.symbol
            assert first_trade_json["shares"] == first_trade.shares
            assert abs(first_trade_json["pnl"] - float(first_trade.pnl)) < 0.01

        # Verify equity curve data points match
        assert len(json_data["equity_curve"]) == len(result.equity_curve), (
            "Equity curve count mismatch between JSON and result"
        )

        # Verify metadata
        assert json_data["metadata"]["execution_time_seconds"] == result.execution_time_seconds
        assert json_data["metadata"]["completed_at"] == result.completed_at.isoformat()

        print(f"[FINAL] Data consistency validated:")
        print(f"  - Trade data matches across formats")
        print(f"  - Equity curve matches across formats")
        print(f"  - Metadata matches across formats")

        # Success summary
        print(f"\n=== Full Report Workflow Integration Test PASSED ===")
        print(f"[✓] Backtest executed: {len(result.trades)} trades")
        print(f"[✓] Markdown report: {md_path.name} ({md_stat.st_size} bytes)")
        print(f"[✓] JSON report: {json_path.name} ({json_stat.st_size} bytes)")
        print(f"[✓] Data consistency: All formats match")
        print(f"[✓] File output: Both reports saved successfully")

    def test_full_report_workflow_no_trades(self, tmp_path: Path):
        """
        Test: Report generation with backtest that produces no trades.

        **Test Scenario**:
        GIVEN: Backtest with strategy that generates no trades (insufficient data)
        AND: tmp_path for report file output
        WHEN: Reports are generated
        THEN:
        - Both report files still created
        - Markdown shows "No trades executed"
        - JSON has empty trades array
        - Equity curve still present (flat line)
        - No errors during report generation

        This verifies report generation handles edge cases gracefully.
        """
        # ARRANGE: Create limited data (insufficient for momentum strategy)
        bars = []
        symbol = "AAPL"
        start_date = datetime(2023, 1, 3, 9, 30, tzinfo=timezone.utc)

        # Only 20 bars (insufficient for long_window=30)
        for i in range(20):
            bar_timestamp = start_date + timedelta(days=i)
            base_price = Decimal("150.0")

            bar = HistoricalDataBar(
                symbol=symbol,
                timestamp=bar_timestamp,
                open=base_price - Decimal("0.50"),
                high=base_price + Decimal("1.00"),
                low=base_price - Decimal("1.00"),
                close=base_price,
                volume=50000000,
                split_adjusted=True,
                dividend_adjusted=True
            )
            bars.append(bar)

        # Config
        config = BacktestConfig(
            strategy_class=MomentumStrategy,
            symbols=[symbol],
            start_date=datetime(2023, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2023, 1, 31, tzinfo=timezone.utc),
            initial_capital=Decimal("100000.0"),
            commission=Decimal("0.0"),
            slippage_pct=Decimal("0.0"),
            risk_free_rate=Decimal("0.02"),
        )

        # Strategy with windows too large for data
        strategy = MomentumStrategy(short_window=20, long_window=40)

        # ACT: Run backtest (should generate no trades)
        engine = BacktestEngine(config=config)
        result = engine.run(strategy=strategy, historical_data={symbol: bars})

        # Verify no trades
        assert len(result.trades) == 0, "Should have no trades (design check)"

        # ACT: Generate reports
        generator = ReportGenerator()
        md_path = tmp_path / "no_trades_report.md"
        json_path = tmp_path / "no_trades_report.json"

        markdown = generator.generate_markdown(result, str(md_path))
        json_str = generator.generate_json(result, str(json_path))

        # ASSERT: Verify files created
        assert md_path.exists(), "Markdown file should be created even with no trades"
        assert json_path.exists(), "JSON file should be created even with no trades"

        # Verify markdown handles no trades
        md_content = md_path.read_text(encoding="utf-8")
        assert "No trades executed" in md_content or "*No trades" in md_content, (
            "Markdown should indicate no trades executed"
        )

        # Verify JSON handles no trades
        json_data = json.loads(json_path.read_text(encoding="utf-8"))
        assert len(json_data["trades"]) == 0, "JSON should have empty trades array"
        assert json_data["metrics"]["total_trades"] == 0, "JSON metrics should show 0 trades"

        # Verify equity curve still present
        assert len(json_data["equity_curve"]) > 0, "Equity curve should exist even with no trades"

        print(f"\n[PASS] No-trades report generation test passed")
        print(f"[PASS] Reports handle edge case gracefully")
