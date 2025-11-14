"""
Custom Strategy Example

Demonstrates how to create a custom trading strategy from scratch.
This example shows:
- IStrategy protocol implementation
- Using multiple indicators (RSI, Bollinger Bands)
- Position sizing logic
- Risk management (stop loss, take profit)

Run:
    python examples/custom_strategy_example.py
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import List

from src.trading_bot.backtest.engine import BacktestEngine
from src.trading_bot.backtest.models import (
    BacktestConfig,
    HistoricalDataBar,
    Position,
)
from src.trading_bot.backtest.historical_data_manager import HistoricalDataManager
from src.trading_bot.backtest.performance_calculator import PerformanceCalculator
from src.trading_bot.backtest.report_generator import ReportGenerator


class MeanReversionStrategy:
    """
    Mean Reversion Strategy with RSI and Bollinger Bands

    Entry Signal:
        - RSI < 30 (oversold)
        - Price < Lower Bollinger Band (below 2 standard deviations)

    Exit Signal:
        - RSI > 70 (overbought)
        - Price > Upper Bollinger Band (above 2 standard deviations)
        - Stop loss: -5% from entry
        - Take profit: +10% from entry

    Parameters:
        rsi_period: RSI lookback period (default: 14)
        rsi_oversold: RSI oversold threshold (default: 30)
        rsi_overbought: RSI overbought threshold (default: 70)
        bb_period: Bollinger Bands lookback period (default: 20)
        bb_std_dev: Bollinger Bands standard deviations (default: 2.0)
        stop_loss_pct: Stop loss percentage (default: 0.05 = 5%)
        take_profit_pct: Take profit percentage (default: 0.10 = 10%)
    """

    def __init__(
        self,
        rsi_period: int = 14,
        rsi_oversold: Decimal = Decimal("30"),
        rsi_overbought: Decimal = Decimal("70"),
        bb_period: int = 20,
        bb_std_dev: Decimal = Decimal("2.0"),
        stop_loss_pct: Decimal = Decimal("0.05"),
        take_profit_pct: Decimal = Decimal("0.10"),
    ):
        """Initialize Mean Reversion Strategy."""
        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        self.bb_period = bb_period
        self.bb_std_dev = bb_std_dev
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct

    def _calculate_rsi(self, bars: List[HistoricalDataBar]) -> Decimal:
        """
        Calculate Relative Strength Index (RSI).

        RSI = 100 - (100 / (1 + RS))
        where RS = Average Gain / Average Loss over period
        """
        if len(bars) < self.rsi_period + 1:
            return Decimal("50")  # Neutral RSI if insufficient data

        # Calculate price changes
        gains = []
        losses = []
        for i in range(len(bars) - self.rsi_period, len(bars)):
            change = bars[i].close - bars[i - 1].close
            if change > 0:
                gains.append(change)
                losses.append(Decimal("0"))
            else:
                gains.append(Decimal("0"))
                losses.append(abs(change))

        # Calculate average gain and loss
        avg_gain = sum(gains) / self.rsi_period
        avg_loss = sum(losses) / self.rsi_period

        if avg_loss == 0:
            return Decimal("100")  # Maximum RSI (all gains)

        rs = avg_gain / avg_loss
        rsi = Decimal("100") - (Decimal("100") / (Decimal("1") + rs))
        return rsi

    def _calculate_bollinger_bands(
        self,
        bars: List[HistoricalDataBar]
    ) -> tuple[Decimal, Decimal, Decimal]:
        """
        Calculate Bollinger Bands (middle, upper, lower).

        Middle Band = Simple Moving Average
        Upper Band = Middle + (std_dev * standard deviation)
        Lower Band = Middle - (std_dev * standard deviation)
        """
        if len(bars) < self.bb_period:
            # Insufficient data: return current price for all bands
            current_price = bars[-1].close
            return current_price, current_price, current_price

        # Calculate SMA (middle band)
        recent_bars = bars[-self.bb_period:]
        prices = [bar.close for bar in recent_bars]
        middle = sum(prices) / len(prices)

        # Calculate standard deviation
        variance = sum((price - middle) ** 2 for price in prices) / len(prices)
        std_dev = variance.sqrt() if variance > 0 else Decimal("0")

        # Calculate upper and lower bands
        upper = middle + (self.bb_std_dev * std_dev)
        lower = middle - (self.bb_std_dev * std_dev)

        return middle, upper, lower

    def should_enter(self, bars: List[HistoricalDataBar]) -> bool:
        """
        Entry signal: RSI oversold AND price below lower Bollinger Band.

        Args:
            bars: Historical data bars available at this point

        Returns:
            True if entry signal detected, False otherwise
        """
        if len(bars) < max(self.rsi_period + 1, self.bb_period):
            return False  # Insufficient data for indicators

        # Calculate indicators
        rsi = self._calculate_rsi(bars)
        middle, upper, lower = self._calculate_bollinger_bands(bars)
        current_price = bars[-1].close

        # Entry signal: oversold on RSI AND below lower BB
        return rsi < self.rsi_oversold and current_price < lower

    def should_exit(
        self,
        position: Position,
        bars: List[HistoricalDataBar]
    ) -> bool:
        """
        Exit signal: RSI overbought OR price above upper BB OR stop loss OR take profit.

        Args:
            position: Current open position
            bars: Historical data bars available at this point

        Returns:
            True if exit signal detected, False otherwise
        """
        if len(bars) < max(self.rsi_period + 1, self.bb_period):
            return False  # Insufficient data for indicators

        current_price = bars[-1].close

        # Check stop loss
        loss_pct = (position.entry_price - current_price) / position.entry_price
        if loss_pct >= self.stop_loss_pct:
            return True  # Stop loss triggered

        # Check take profit
        gain_pct = (current_price - position.entry_price) / position.entry_price
        if gain_pct >= self.take_profit_pct:
            return True  # Take profit triggered

        # Calculate indicators
        rsi = self._calculate_rsi(bars)
        middle, upper, lower = self._calculate_bollinger_bands(bars)

        # Exit signal: overbought on RSI OR above upper BB
        return rsi > self.rsi_overbought or current_price > upper


def main():
    """Run custom strategy backtest."""
    print("=" * 80)
    print("CUSTOM STRATEGY EXAMPLE: Mean Reversion with RSI and Bollinger Bands")
    print("=" * 80)

    # Step 1: Fetch historical data
    print("\n[1/4] Fetching historical data...")
    symbol = "AAPL"
    start_date = datetime(2023, 1, 1, tzinfo=timezone.utc)
    end_date = datetime(2023, 12, 31, tzinfo=timezone.utc)

    data_manager = HistoricalDataManager()
    historical_data = data_manager.fetch_data(symbol, start_date, end_date)
    print(f"  Symbol: {symbol}")
    print(f"  Trading days: {len(historical_data)}")

    # Step 2: Configure backtest
    print("\n[2/4] Configuring backtest...")
    config = BacktestConfig(
        strategy_class=MeanReversionStrategy,
        symbols=[symbol],
        start_date=start_date,
        end_date=end_date,
        initial_capital=Decimal("100000"),
        commission=Decimal("0"),
        slippage_pct=Decimal("0.001"),
    )

    # Step 3: Run backtest
    print("\n[3/4] Running custom strategy...")
    strategy = MeanReversionStrategy(
        rsi_period=14,
        rsi_oversold=Decimal("30"),
        rsi_overbought=Decimal("70"),
        bb_period=20,
        bb_std_dev=Decimal("2.0"),
        stop_loss_pct=Decimal("0.05"),  # 5% stop loss
        take_profit_pct=Decimal("0.10"),  # 10% take profit
    )

    engine = BacktestEngine(config)
    result = engine.run(strategy, historical_data)

    calculator = PerformanceCalculator()
    metrics = calculator.calculate_metrics(result.trades, result.equity_curve, config)

    print(f"  Trades executed: {len(result.trades)}")
    print(f"  Total return: {metrics.total_return * 100:.2f}%")

    # Step 4: Generate report
    print("\n[4/4] Generating report...")
    report_generator = ReportGenerator()
    markdown_path = "specs/001-backtesting-engine/backtest-reports/custom_strategy.md"
    json_path = "specs/001-backtesting-engine/backtest-reports/custom_strategy.json"

    report_generator.generate_markdown(result, markdown_path)
    report_generator.generate_json(result, json_path)
    print(f"  Markdown report: {markdown_path}")
    print(f"  JSON report: {json_path}")

    # Display results
    print("\n" + "=" * 80)
    print("BACKTEST RESULTS")
    print("=" * 80)
    print(f"Strategy: Mean Reversion (RSI + Bollinger Bands)")
    print(f"Final Portfolio Value: ${result.final_equity:,.2f}")
    print(f"Total Return: {metrics.total_return * 100:.2f}%")
    print(f"Annualized Return: {metrics.annualized_return * 100:.2f}%")
    print(f"Max Drawdown: {metrics.max_drawdown * 100:.2f}%")
    print(f"Sharpe Ratio: {metrics.sharpe_ratio:.2f}")
    print(f"Win Rate: {metrics.win_rate * 100:.1f}%")
    print(f"Profit Factor: {metrics.profit_factor:.2f}")
    print(f"Total Trades: {metrics.total_trades}")

    # Display trade details
    if result.trades:
        print("\nSample Trades (first 3):")
        for i, trade in enumerate(result.trades[:3]):
            print(f"  Trade {i+1}:")
            print(f"    Entry: {trade.entry_date.date()} @ ${trade.entry_price}")
            print(f"    Exit: {trade.exit_date.date()} @ ${trade.exit_price}")
            print(f"    P&L: ${trade.pnl:,.2f} ({trade.pnl_pct * 100:.2f}%)")
            print(f"    Duration: {trade.duration_days} days")
            print(f"    Reason: {trade.exit_reason}")

    print("\n" + "=" * 80)
    print("Strategy Implementation Notes:")
    print("=" * 80)
    print("1. This strategy implements mean reversion using RSI and Bollinger Bands")
    print("2. Entry: Oversold conditions (RSI < 30, price < lower BB)")
    print("3. Exit: Overbought conditions OR stop loss OR take profit")
    print("4. Risk management: 5% stop loss, 10% take profit")
    print("\nNext steps:")
    print("  1. Experiment with different RSI and Bollinger Band parameters")
    print("  2. Adjust stop loss and take profit levels")
    print("  3. Test on different stocks and time periods")
    print("  4. Add position sizing logic based on volatility")
    print("=" * 80)


if __name__ == "__main__":
    main()
