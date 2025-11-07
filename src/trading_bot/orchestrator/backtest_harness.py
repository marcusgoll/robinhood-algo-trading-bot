#!/usr/bin/env python3
"""
Backtest Harness for LLM Trading System

Simulates the orchestrator workflows on historical data to validate
system performance before live trading.

Test Period: 2024-01-01 to 2025-01-01 (12 months)
Test Symbols: AAPL, SPY, QQQ, TSLA, NVDA

Performance Targets:
- Win Rate: >50%
- Profit Factor: >1.5
- Sharpe Ratio: >1.0
- Max Drawdown: <10%
"""

import sys
import json
import logging
import os
from datetime import datetime, timedelta, UTC
from typing import Dict, List, Optional, Any
from pathlib import Path
from dataclasses import dataclass, asdict
import statistics

# Import historical data manager directly to avoid circular import in backtest.__init__
import importlib.util
_hdm_path = os.path.join(os.path.dirname(__file__), '..', 'backtest', 'historical_data_manager.py')
_hdm_spec = importlib.util.spec_from_file_location("historical_data_manager", _hdm_path)
_hdm_module = importlib.util.module_from_spec(_hdm_spec)
_hdm_spec.loader.exec_module(_hdm_module)
HistoricalDataManager = _hdm_module.HistoricalDataManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class BacktestTrade:
    """Simulated trade for backtesting"""
    symbol: str
    entry_date: str
    entry_price: float
    shares: int
    stop_loss: float
    target_1: float
    target_2: float
    signal: str
    confidence: float
    exit_date: Optional[str] = None
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None
    pnl: Optional[float] = None
    pnl_percent: Optional[float] = None
    win: Optional[bool] = None


@dataclass
class BacktestMetrics:
    """Performance metrics for backtest"""
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    sharpe_ratio: float
    max_drawdown: float
    max_drawdown_percent: float
    total_return_percent: float
    trades: List[Dict[str, Any]]


class LLMBacktestHarness:
    """
    Backtest harness for LLM trading workflows.

    Simulates:
    - Pre-market screening (identify candidates)
    - Trade analysis (generate signals)
    - Position optimization (size and risk)
    - Trade execution and monitoring
    """

    def __init__(self, start_date: str, end_date: str, symbols: List[str],
                 initial_capital: float = 10000.0):
        """
        Initialize backtest harness.

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            symbols: List of symbols to test
            initial_capital: Starting capital
        """
        self.start_date = datetime.strptime(start_date, "%Y-%m-%d")
        self.end_date = datetime.strptime(end_date, "%Y-%m-%d")
        self.symbols = symbols
        self.initial_capital = initial_capital
        self.capital = initial_capital

        self.trades: List[BacktestTrade] = []
        self.open_positions: Dict[str, BacktestTrade] = {}
        self.equity_curve: List[Dict[str, Any]] = []

        logger.info(f"Initialized backtest: {start_date} to {end_date}")
        logger.info(f"Symbols: {', '.join(symbols)}")
        logger.info(f"Initial capital: ${initial_capital:,.2f}")

        # Initialize historical data manager with Alpaca integration
        logger.info("Initializing historical data manager with Alpaca API...")
        self.data_manager = HistoricalDataManager(
            api_key=os.getenv('ALPACA_API_KEY'),
            api_secret=os.getenv('ALPACA_SECRET_KEY'),
            cache_dir=".backtest_cache",
            cache_enabled=True
        )

        # Pre-fetch all historical data for symbols
        logger.info("Pre-fetching historical data (this may take a minute)...")
        self.historical_data: Dict[str, Dict] = {}
        for symbol in self.symbols:
            logger.info(f"  Fetching {symbol}...")
            try:
                bars = self.data_manager.fetch_data(
                    symbol=symbol,
                    start_date=self.start_date.replace(tzinfo=UTC),
                    end_date=self.end_date.replace(tzinfo=UTC)
                )
                # Convert to dict keyed by date for fast lookup
                self.historical_data[symbol] = {
                    bar.timestamp.date(): bar for bar in bars
                }
                logger.info(f"  Loaded {len(bars)} bars for {symbol}")
            except Exception as e:
                logger.error(f"  Failed to fetch data for {symbol}: {e}")
                self.historical_data[symbol] = {}

        logger.info("Historical data pre-fetch complete!")

    def simulate_screening(self, date: str) -> List[str]:
        """
        Simulate pre-market screening.

        In real implementation, this would call the /screen command.
        For backtest, we'll use simplified momentum criteria.

        Returns:
            List of candidate symbols
        """
        # For backtest, return all symbols as candidates
        # In production, this would run the LLM screening workflow
        logger.debug(f"{date}: Screening {len(self.symbols)} symbols")
        return self.symbols[:3]  # Top 3 candidates

    def simulate_analysis(self, symbol: str, date: str,
                         current_price: float) -> Optional[Dict[str, Any]]:
        """
        Simulate trade analysis.

        In real implementation, this would call /analyze-trade.
        For backtest, we'll use simplified technical rules.

        Returns:
            Analysis dict with signal, confidence, etc.
        """
        # Simplified analysis for backtest
        # In production, this would run the LLM analysis workflow

        # Mock signal based on simple momentum
        # In real backtest, you'd use actual historical indicators
        import random
        random.seed(hash(f"{symbol}{date}"))  # Deterministic for symbol+date

        signals = ["STRONG_BUY", "BUY", "HOLD", "AVOID"]
        weights = [0.15, 0.25, 0.35, 0.25]  # Probability distribution
        signal = random.choices(signals, weights=weights)[0]

        if signal in ["STRONG_BUY", "BUY"]:
            confidence = random.uniform(70, 95) if signal == "STRONG_BUY" else random.uniform(60, 80)

            return {
                "symbol": symbol,
                "signal": signal,
                "confidence": confidence,
                "current_price": current_price,
                "analysis": {
                    "technical_score": random.uniform(60, 90),
                    "momentum_score": random.uniform(65, 95)
                }
            }

        return None  # No trade signal

    def simulate_optimization(self, symbol: str, analysis: Dict[str, Any],
                            date: str) -> Optional[Dict[str, Any]]:
        """
        Simulate position optimization.

        In real implementation, this would call /optimize-entry.
        For backtest, we'll use 2% risk rule and ATR-based stops.

        Returns:
            Optimization dict with entry, size, stops, targets
        """
        current_price = analysis["current_price"]

        # Simplified optimization for backtest
        # In production, this would run the LLM optimization workflow

        # 2% risk rule
        risk_amount = self.capital * 0.02

        # Simplified stop loss (3% below entry)
        stop_loss = current_price * 0.97

        # Risk per share
        risk_per_share = current_price - stop_loss

        # Position size based on risk
        shares = int(risk_amount / risk_per_share) if risk_per_share > 0 else 0

        # Ensure at least 1 share if capital allows
        if shares == 0 and self.capital >= current_price:
            shares = 1

        # Ensure we have enough capital (max 30% per position)
        max_shares = int((self.capital * 0.3) / current_price)
        shares = min(shares, max_shares)

        # Final position cost
        position_cost = shares * current_price

        # Ensure we can afford this
        if position_cost > self.capital:
            shares = int(self.capital / current_price)
            position_cost = shares * current_price

        # Targets (1.5:1 and 2.5:1 R:R)
        target_1 = current_price + (risk_per_share * 1.5)
        target_2 = current_price + (risk_per_share * 2.5)

        return {
            "symbol": symbol,
            "entry_price": current_price,
            "shares": shares,
            "stop_loss": stop_loss,
            "target_1": target_1,
            "target_2": target_2,
            "position_cost": position_cost
        }

    def execute_trade(self, optimization: Dict[str, Any], analysis: Dict[str, Any],
                     date: str) -> Optional[BacktestTrade]:
        """Execute simulated trade."""
        symbol = optimization["symbol"]

        # Check if we already have position in this symbol
        if symbol in self.open_positions:
            logger.debug(f"{date}: Already have position in {symbol}")
            return None

        # Skip trades with 0 shares
        if optimization["shares"] <= 0:
            logger.debug(f"{date}: Invalid share count ({optimization['shares']}) for {symbol}")
            return None

        # Check capital
        if optimization["position_cost"] > self.capital:
            logger.debug(f"{date}: Insufficient capital for {symbol}")
            return None

        # Create trade
        trade = BacktestTrade(
            symbol=symbol,
            entry_date=date,
            entry_price=optimization["entry_price"],
            shares=optimization["shares"],
            stop_loss=optimization["stop_loss"],
            target_1=optimization["target_1"],
            target_2=optimization["target_2"],
            signal=analysis["signal"],
            confidence=analysis["confidence"]
        )

        # Update capital
        self.capital -= optimization["position_cost"]

        # Add to open positions
        self.open_positions[symbol] = trade

        logger.info(f"{date}: ENTER {symbol} @ ${trade.entry_price:.2f} x {trade.shares} shares")

        return trade

    def monitor_positions(self, date: str, price_data: Dict[str, float]):
        """Monitor open positions and check for exits."""
        for symbol in list(self.open_positions.keys()):
            trade = self.open_positions[symbol]
            current_price = price_data.get(symbol)

            if current_price is None:
                continue

            # Check stop loss
            if current_price <= trade.stop_loss:
                self._close_trade(trade, current_price, date, "STOP_LOSS")
                continue

            # Check target 2 (full exit)
            if current_price >= trade.target_2:
                self._close_trade(trade, current_price, date, "TARGET_2")
                continue

            # Check target 1 (partial exit or raise stop)
            if current_price >= trade.target_1:
                # For simplicity, full exit at target 1
                self._close_trade(trade, current_price, date, "TARGET_1")
                continue

    def _close_trade(self, trade: BacktestTrade, exit_price: float,
                    exit_date: str, exit_reason: str):
        """Close a trade and calculate P&L."""
        trade.exit_date = exit_date
        trade.exit_price = exit_price
        trade.exit_reason = exit_reason

        # Calculate P&L
        trade.pnl = (exit_price - trade.entry_price) * trade.shares
        trade.pnl_percent = ((exit_price - trade.entry_price) / trade.entry_price) * 100
        trade.win = trade.pnl > 0

        # Update capital
        self.capital += (exit_price * trade.shares)

        # Remove from open positions
        del self.open_positions[trade.symbol]

        # Add to completed trades
        self.trades.append(trade)

        logger.info(
            f"{exit_date}: EXIT {trade.symbol} @ ${exit_price:.2f} | "
            f"P&L: ${trade.pnl:.2f} ({trade.pnl_percent:+.2f}%) | {exit_reason}"
        )

    def get_price_data(self, date: str) -> Dict[str, float]:
        """
        Get REAL historical price data for a date from Alpaca.

        Args:
            date: Date string (YYYY-MM-DD)

        Returns:
            Dict mapping symbol to close price
        """
        date_obj = datetime.strptime(date, "%Y-%m-%d").date()

        prices = {}
        for symbol in self.symbols:
            if symbol in self.historical_data:
                bar = self.historical_data[symbol].get(date_obj)
                if bar:
                    prices[symbol] = float(bar.close)
                else:
                    # Use last known price if date not found (weekends/holidays)
                    recent_bars = sorted(
                        [(d, b) for d, b in self.historical_data[symbol].items() if d < date_obj],
                        key=lambda x: x[0],
                        reverse=True
                    )
                    if recent_bars:
                        prices[symbol] = float(recent_bars[0][1].close)
                    else:
                        logger.warning(f"No historical data available for {symbol} on or before {date}")

        return prices

    def run(self) -> BacktestMetrics:
        """Run the backtest simulation."""
        logger.info("Starting backtest simulation...")

        current_date = self.start_date
        trading_days = 0

        while current_date <= self.end_date:
            date_str = current_date.strftime("%Y-%m-%d")

            # Skip weekends (simplified)
            if current_date.weekday() >= 5:
                current_date += timedelta(days=1)
                continue

            trading_days += 1

            # Get price data from real historical data
            price_data = self.get_price_data(date_str)

            # Monitor existing positions first
            self.monitor_positions(date_str, price_data)

            # Pre-market screening (once per day)
            candidates = self.simulate_screening(date_str)

            # Analyze candidates
            for symbol in candidates:
                current_price = price_data.get(symbol)
                if current_price is None:
                    continue

                # Analyze
                analysis = self.simulate_analysis(symbol, date_str, current_price)
                if analysis is None:
                    continue

                # Optimize
                optimization = self.simulate_optimization(symbol, analysis, date_str)
                if optimization is None:
                    continue

                # Execute
                self.execute_trade(optimization, analysis, date_str)

            # Track equity
            total_equity = self.capital
            for trade in self.open_positions.values():
                current_price = price_data.get(trade.symbol, trade.entry_price)
                total_equity += current_price * trade.shares

            self.equity_curve.append({
                "date": date_str,
                "capital": self.capital,
                "equity": total_equity,
                "open_positions": len(self.open_positions)
            })

            current_date += timedelta(days=1)

        # Close any remaining positions at end date
        final_prices = self.get_price_data(self.end_date.strftime("%Y-%m-%d"))
        for symbol, trade in list(self.open_positions.items()):
            self._close_trade(trade, final_prices[symbol],
                            self.end_date.strftime("%Y-%m-%d"), "END_OF_BACKTEST")

        logger.info(f"Backtest complete: {trading_days} trading days")

        # Calculate metrics
        return self._calculate_metrics()

    def _calculate_metrics(self) -> BacktestMetrics:
        """Calculate performance metrics."""
        if not self.trades:
            logger.warning("No trades executed during backtest")
            return BacktestMetrics(
                total_trades=0, winning_trades=0, losing_trades=0,
                win_rate=0.0, total_pnl=0.0, avg_win=0.0, avg_loss=0.0,
                profit_factor=0.0, sharpe_ratio=0.0, max_drawdown=0.0,
                max_drawdown_percent=0.0, total_return_percent=0.0,
                trades=[]
            )

        # Basic metrics
        total_trades = len(self.trades)
        winning_trades = sum(1 for t in self.trades if t.win)
        losing_trades = total_trades - winning_trades
        win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0.0

        # P&L metrics
        wins = [t.pnl for t in self.trades if t.win]
        losses = [abs(t.pnl) for t in self.trades if not t.win]

        total_pnl = sum(t.pnl for t in self.trades)
        avg_win = statistics.mean(wins) if wins else 0.0
        avg_loss = statistics.mean(losses) if losses else 0.0

        total_wins = sum(wins)
        total_losses = sum(losses)
        profit_factor = total_wins / total_losses if total_losses > 0 else 0.0

        # Return
        final_capital = self.capital
        total_return_percent = ((final_capital - self.initial_capital) / self.initial_capital) * 100

        # Sharpe ratio (simplified)
        returns = [t.pnl_percent for t in self.trades]
        if len(returns) > 1:
            avg_return = statistics.mean(returns)
            std_return = statistics.stdev(returns)
            sharpe_ratio = (avg_return / std_return) * (252 ** 0.5) if std_return > 0 else 0.0
        else:
            sharpe_ratio = 0.0

        # Max drawdown
        peak = self.initial_capital
        max_drawdown = 0.0
        max_drawdown_percent = 0.0

        for point in self.equity_curve:
            equity = point["equity"]
            if equity > peak:
                peak = equity
            drawdown = peak - equity
            drawdown_percent = (drawdown / peak) * 100 if peak > 0 else 0.0
            if drawdown > max_drawdown:
                max_drawdown = drawdown
                max_drawdown_percent = drawdown_percent

        return BacktestMetrics(
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            total_pnl=total_pnl,
            avg_win=avg_win,
            avg_loss=avg_loss,
            profit_factor=profit_factor,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            max_drawdown_percent=max_drawdown_percent,
            total_return_percent=total_return_percent,
            trades=[asdict(t) for t in self.trades]
        )

    def save_results(self, output_file: str):
        """Save backtest results to file."""
        metrics = self._calculate_metrics()

        results = {
            "backtest_params": {
                "start_date": self.start_date.strftime("%Y-%m-%d"),
                "end_date": self.end_date.strftime("%Y-%m-%d"),
                "symbols": self.symbols,
                "initial_capital": self.initial_capital
            },
            "metrics": asdict(metrics),
            "equity_curve": self.equity_curve
        }

        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)

        logger.info(f"Results saved to {output_file}")


def main():
    """Main entry point for backtest."""
    import argparse

    parser = argparse.ArgumentParser(description="LLM Trading System Backtest")
    parser.add_argument("--start-date", default="2024-01-01", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", default="2025-01-01", help="End date (YYYY-MM-DD)")
    parser.add_argument("--symbols", default="AAPL,SPY,QQQ,TSLA,NVDA", help="Comma-separated symbols")
    parser.add_argument("--capital", type=float, default=10000.0, help="Initial capital")
    parser.add_argument("--output", default="logs/backtest/results.json", help="Output file")

    args = parser.parse_args()

    # Parse symbols
    symbols = [s.strip() for s in args.symbols.split(",")]

    # Run backtest
    harness = LLMBacktestHarness(
        start_date=args.start_date,
        end_date=args.end_date,
        symbols=symbols,
        initial_capital=args.capital
    )

    metrics = harness.run()

    # Print results
    print("\n" + "="*60)
    print("BACKTEST RESULTS")
    print("="*60)
    print(f"Period: {args.start_date} to {args.end_date}")
    print(f"Initial Capital: ${harness.initial_capital:,.2f}")
    print(f"Final Capital: ${harness.capital:,.2f}")
    print(f"Total Return: {metrics.total_return_percent:+.2f}%")
    print("-"*60)
    print(f"Total Trades: {metrics.total_trades}")
    print(f"Winning Trades: {metrics.winning_trades}")
    print(f"Losing Trades: {metrics.losing_trades}")
    print(f"Win Rate: {metrics.win_rate:.2f}%")
    print(f"Avg Win: ${metrics.avg_win:.2f}")
    print(f"Avg Loss: ${metrics.avg_loss:.2f}")
    print(f"Profit Factor: {metrics.profit_factor:.2f}")
    print(f"Sharpe Ratio: {metrics.sharpe_ratio:.2f}")
    print(f"Max Drawdown: ${metrics.max_drawdown:.2f} ({metrics.max_drawdown_percent:.2f}%)")
    print("-"*60)

    # Targets evaluation
    print("\nTARGET EVALUATION:")
    print(f"Win Rate >50%: {'PASS' if metrics.win_rate > 50 else 'FAIL'}")
    print(f"Profit Factor >1.5: {'PASS' if metrics.profit_factor > 1.5 else 'FAIL'}")
    print(f"Sharpe Ratio >1.0: {'PASS' if metrics.sharpe_ratio > 1.0 else 'FAIL'}")
    print(f"Max Drawdown <10%: {'PASS' if metrics.max_drawdown_percent < 10 else 'FAIL'}")
    print("="*60 + "\n")

    # Save results
    harness.save_results(args.output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
