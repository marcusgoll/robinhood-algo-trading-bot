"""
Report Generator for Backtest Results

Generates human-readable markdown reports and machine-readable JSON exports
from BacktestResult objects. Provides formatted trade tables, performance metrics,
and equity curve data for analysis and archival.

Usage:
    generator = ReportGenerator()
    markdown = generator.generate_markdown(result, output_path="report.md")
    json_str = generator.generate_json(result, output_path="report.json")
"""

import json
from pathlib import Path

from .models import BacktestResult, Trade


class ReportGenerator:
    """
    Generate markdown and JSON reports from backtest results.

    Provides two output formats:
    1. Markdown: Human-readable report with sections for config, metrics, trades, etc.
    2. JSON: Machine-readable export with complete data serialization

    All numeric values are formatted consistently:
    - Currency: $X,XXX.XX
    - Percentages: XX.XX%
    - Ratios: X.XX
    - Dates: YYYY-MM-DD or ISO format
    """

    def generate_markdown(
        self, result: BacktestResult, output_path: str | None = None
    ) -> str:
        """
        Generate markdown report from backtest result.

        Creates a comprehensive markdown report with sections for:
        - Configuration (strategy, dates, symbols, capital)
        - Performance Metrics (returns, win rate, Sharpe ratio, etc.)
        - Trades (formatted table with all trade details)
        - Equity Curve (data points for plotting)
        - Data Warnings (validation warnings encountered)

        Args:
            result: BacktestResult to generate report from
            output_path: Optional file path to save report (default: return string only)

        Returns:
            Markdown report as string

        Example:
            generator = ReportGenerator()
            markdown = generator.generate_markdown(result)
            # Or save directly:
            markdown = generator.generate_markdown(result, output_path="report.md")
        """
        # Build markdown sections
        sections = []

        # Header
        sections.append("# Backtest Report")
        sections.append("")
        sections.append(f"**Generated:** {result.completed_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        sections.append(f"**Execution Time:** {result.execution_time_seconds:.2f} seconds")
        sections.append("")

        # Configuration section
        sections.append("## Configuration")
        sections.append("")
        sections.append(f"- **Strategy:** {result.config.strategy_class.__name__}")
        sections.append(f"- **Symbols:** {', '.join(result.config.symbols)}")
        sections.append(f"- **Start Date:** {result.config.start_date.strftime('%Y-%m-%d')}")
        sections.append(f"- **End Date:** {result.config.end_date.strftime('%Y-%m-%d')}")
        sections.append(f"- **Initial Capital:** ${result.config.initial_capital:,.2f}")
        sections.append(f"- **Commission:** ${result.config.commission:.2f} per trade")
        sections.append(f"- **Slippage:** {result.config.slippage_pct * 100:.2f}%")
        sections.append(f"- **Risk-Free Rate:** {result.config.risk_free_rate * 100:.2f}%")
        sections.append("")

        # Performance Metrics section
        sections.append("## Performance Metrics")
        sections.append("")
        sections.append(f"- **Total Return:** {result.metrics.total_return * 100:.2f}%")
        sections.append(f"- **Annualized Return:** {result.metrics.annualized_return * 100:.2f}%")
        sections.append(f"- **CAGR:** {result.metrics.cagr * 100:.2f}%")
        sections.append(f"- **Sharpe Ratio:** {result.metrics.sharpe_ratio:.2f}")
        sections.append(f"- **Max Drawdown:** {result.metrics.max_drawdown * 100:.2f}%")
        sections.append(f"- **Max Drawdown Duration:** {result.metrics.max_drawdown_duration_days} days")
        sections.append("")
        sections.append(f"- **Total Trades:** {result.metrics.total_trades}")
        sections.append(f"- **Winning Trades:** {result.metrics.winning_trades}")
        sections.append(f"- **Losing Trades:** {result.metrics.losing_trades}")
        sections.append(f"- **Win Rate:** {result.metrics.win_rate * 100:.2f}%")
        sections.append(f"- **Profit Factor:** {result.metrics.profit_factor:.2f}")
        sections.append(f"- **Average Win:** ${result.metrics.average_win:,.2f}")
        sections.append(f"- **Average Loss:** ${result.metrics.average_loss:,.2f}")
        sections.append("")

        # Trades section
        sections.append("## Trades")
        sections.append("")
        if result.trades:
            sections.append(self._format_trade_table(result.trades))
        else:
            sections.append("*No trades executed during backtest period*")
        sections.append("")

        # Equity Curve section
        sections.append("## Equity Curve")
        sections.append("")
        if result.equity_curve:
            sections.append("| Date | Equity |")
            sections.append("|------|--------|")
            for timestamp, equity in result.equity_curve:
                sections.append(f"| {timestamp.strftime('%Y-%m-%d')} | ${equity:,.2f} |")
        else:
            sections.append("*No equity curve data available*")
        sections.append("")

        # Data Warnings section
        sections.append("## Data Warnings")
        sections.append("")
        if result.data_warnings:
            for warning in result.data_warnings:
                sections.append(f"- {warning}")
        else:
            sections.append("*No data warnings*")
        sections.append("")

        # Join all sections
        markdown = "\n".join(sections)

        # Save to file if output_path provided
        if output_path:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(markdown, encoding="utf-8")

        return markdown

    def generate_json(
        self, result: BacktestResult, output_path: str | None = None
    ) -> str:
        """
        Generate JSON export from backtest result.

        Creates a complete JSON representation of the backtest result with:
        - config: Configuration parameters (strategy, symbols, dates, capital)
        - metrics: Performance statistics (returns, win rate, Sharpe ratio)
        - trades: List of all trades with full details
        - equity_curve: Portfolio value time series
        - data_warnings: List of validation warnings
        - metadata: Execution time and completion timestamp

        All Decimal types are converted to float for JSON compatibility.
        All datetime objects are converted to ISO format strings.

        Args:
            result: BacktestResult to export
            output_path: Optional file path to save JSON (default: return string only)

        Returns:
            JSON string

        Example:
            generator = ReportGenerator()
            json_str = generator.generate_json(result)
            data = json.loads(json_str)
        """
        # Build JSON structure
        data = {
            "config": {
                "strategy": result.config.strategy_class.__name__,
                "symbols": result.config.symbols,
                "start_date": result.config.start_date.isoformat(),
                "end_date": result.config.end_date.isoformat(),
                "initial_capital": float(result.config.initial_capital),
                "commission": float(result.config.commission),
                "slippage_pct": float(result.config.slippage_pct),
                "risk_free_rate": float(result.config.risk_free_rate),
            },
            "metrics": {
                "total_return": float(result.metrics.total_return),
                "annualized_return": float(result.metrics.annualized_return),
                "cagr": float(result.metrics.cagr),
                "win_rate": float(result.metrics.win_rate),
                "profit_factor": float(result.metrics.profit_factor),
                "average_win": float(result.metrics.average_win),
                "average_loss": float(result.metrics.average_loss),
                "max_drawdown": float(result.metrics.max_drawdown),
                "max_drawdown_duration_days": result.metrics.max_drawdown_duration_days,
                "sharpe_ratio": float(result.metrics.sharpe_ratio),
                "total_trades": result.metrics.total_trades,
                "winning_trades": result.metrics.winning_trades,
                "losing_trades": result.metrics.losing_trades,
            },
            "trades": [
                {
                    "symbol": trade.symbol,
                    "entry_date": trade.entry_date.isoformat(),
                    "entry_price": float(trade.entry_price),
                    "exit_date": trade.exit_date.isoformat(),
                    "exit_price": float(trade.exit_price),
                    "shares": trade.shares,
                    "pnl": float(trade.pnl),
                    "pnl_pct": float(trade.pnl_pct),
                    "duration_days": trade.duration_days,
                    "exit_reason": trade.exit_reason,
                    "commission": float(trade.commission),
                    "slippage": float(trade.slippage),
                }
                for trade in result.trades
            ],
            "equity_curve": [
                {
                    "timestamp": timestamp.isoformat(),
                    "equity": float(equity),
                }
                for timestamp, equity in result.equity_curve
            ],
            "data_warnings": result.data_warnings,
            "metadata": {
                "execution_time_seconds": result.execution_time_seconds,
                "completed_at": result.completed_at.isoformat(),
            },
        }

        # Convert to JSON string
        json_str = json.dumps(data, indent=2)

        # Save to file if output_path provided
        if output_path:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(json_str, encoding="utf-8")

        return json_str

    def _format_trade_table(self, trades: list[Trade]) -> str:
        """
        Format trades as markdown table.

        Creates a formatted markdown table with all essential trade information:
        - Symbol
        - Entry Date/Price
        - Exit Date/Price
        - Shares
        - P&L (dollar amount with sign)
        - P&L % (percentage with sign)
        - Duration (days)
        - Exit Reason

        Args:
            trades: List of Trade objects to format

        Returns:
            Markdown table as string

        Example:
            | Symbol | Entry Date | Entry Price | Exit Date | Exit Price | Shares | P&L | P&L % | Duration | Exit Reason |
            |--------|------------|-------------|-----------|------------|--------|-----|-------|----------|-------------|
            | AAPL   | 2024-01-02 | $100.00     | 2024-01-10| $110.00    | 100    | +$1,000.00 | +10.00% | 8 days | take_profit |
        """
        if not trades:
            return "*No trades to display*"

        # Build table header
        lines = []
        lines.append("| Symbol | Entry Date | Entry Price | Exit Date | Exit Price | Shares | P&L | P&L % | Duration | Exit Reason |")
        lines.append("|--------|------------|-------------|-----------|------------|--------|-----|-------|----------|-------------|")

        # Add trade rows
        for trade in trades:
            # Format dates
            entry_date = trade.entry_date.strftime("%Y-%m-%d")
            exit_date = trade.exit_date.strftime("%Y-%m-%d")

            # Format prices
            entry_price = f"${trade.entry_price:.2f}"
            exit_price = f"${trade.exit_price:.2f}"

            # Format P&L with sign
            pnl_sign = "+" if trade.pnl >= 0 else ""
            pnl = f"{pnl_sign}${trade.pnl:,.2f}"

            # Format P&L percentage with sign
            pnl_pct_sign = "+" if trade.pnl_pct >= 0 else ""
            pnl_pct = f"{pnl_pct_sign}{trade.pnl_pct * 100:.2f}%"

            # Format duration
            duration = f"{trade.duration_days} days"

            # Build row
            row = f"| {trade.symbol} | {entry_date} | {entry_price} | {exit_date} | {exit_price} | {trade.shares} | {pnl} | {pnl_pct} | {duration} | {trade.exit_reason} |"
            lines.append(row)

        return "\n".join(lines)
