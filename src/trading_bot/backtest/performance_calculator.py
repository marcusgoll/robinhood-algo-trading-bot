"""
Performance Calculator for Backtest Metrics

Calculates all performance metrics from backtest results including returns,
drawdown, Sharpe ratio, and trade statistics.

Reuses patterns from:
- PerformanceTracker (src/trading_bot/performance/tracker.py)
- PerformanceMetrics structure (src/trading_bot/performance/models.py)
"""

from datetime import datetime
from decimal import Decimal

from .models import BacktestConfig, PerformanceMetrics, Trade


class PerformanceCalculator:
    """
    Calculate comprehensive performance metrics from backtest results.

    Provides methods for:
    - Return calculations (total, annualized, CAGR)
    - Drawdown analysis (max drawdown, duration)
    - Risk metrics (Sharpe ratio)
    - Trade statistics (win rate, profit factor, avg win/loss)
    """

    def calculate_metrics(
        self,
        trades: list[Trade],
        equity_curve: list[tuple[datetime, Decimal]],
        config: BacktestConfig
    ) -> PerformanceMetrics:
        """
        Calculate all performance metrics from backtest results.

        Args:
            trades: List of completed trades
            equity_curve: Portfolio value over time (timestamp, value tuples)
            config: Backtest configuration (for risk-free rate, initial capital)

        Returns:
            PerformanceMetrics with all calculated statistics
        """
        # Calculate return metrics
        total_return, annualized_return, cagr = self._calculate_returns(
            equity_curve, config
        )

        # Calculate drawdown metrics
        max_drawdown, max_drawdown_duration = self._calculate_drawdown(equity_curve)

        # Calculate Sharpe ratio
        sharpe_ratio = self._calculate_sharpe(equity_curve, config.risk_free_rate)

        # Calculate trade statistics
        (
            win_rate,
            profit_factor,
            avg_win,
            avg_loss,
            total_trades,
            winning_trades,
            losing_trades,
        ) = self._calculate_trade_stats(trades)

        return PerformanceMetrics(
            total_return=total_return,
            annualized_return=annualized_return,
            cagr=cagr,
            win_rate=win_rate,
            profit_factor=profit_factor,
            average_win=avg_win,
            average_loss=avg_loss,
            max_drawdown=max_drawdown,
            max_drawdown_duration_days=max_drawdown_duration,
            sharpe_ratio=sharpe_ratio,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
        )

    def calculate_win_rate(self, trades: list[Trade]) -> Decimal:
        """
        Calculate win rate from trade list.

        Args:
            trades: List of completed trades

        Returns:
            Win rate as decimal (e.g., 0.60 for 60% win rate)
        """
        if not trades:
            return Decimal("0")

        winning_trades = sum(1 for trade in trades if trade.pnl > 0)
        return Decimal(winning_trades) / Decimal(len(trades))

    def calculate_sharpe_ratio(
        self,
        equity_curve: list[tuple[datetime, Decimal]],
        risk_free_rate: Decimal
    ) -> Decimal:
        """
        Calculate Sharpe ratio from equity curve.

        Args:
            equity_curve: Portfolio value over time (timestamp, value tuples)
            risk_free_rate: Annual risk-free rate (e.g., 0.02 for 2%)

        Returns:
            Sharpe ratio (risk-adjusted return metric)
        """
        return self._calculate_sharpe(equity_curve, risk_free_rate)

    def calculate_max_drawdown(
        self,
        equity_curve: list[tuple[datetime, Decimal]]
    ) -> tuple[float, int]:
        """
        Calculate maximum drawdown and duration from equity curve.

        Args:
            equity_curve: Portfolio value over time (timestamp, value tuples)

        Returns:
            Tuple of (max_drawdown_pct, max_drawdown_duration_days)
        """
        max_dd, max_dd_duration = self._calculate_drawdown(equity_curve)
        return (float(max_dd), max_dd_duration)

    def _calculate_returns(
        self,
        equity_curve: list[tuple[datetime, Decimal]],
        config: BacktestConfig
    ) -> tuple[Decimal, Decimal, Decimal]:
        """
        Calculate return metrics (total, annualized, CAGR).

        Args:
            equity_curve: Portfolio value over time
            config: Backtest configuration

        Returns:
            Tuple of (total_return, annualized_return, cagr)
        """
        if not equity_curve or len(equity_curve) < 2:
            return (Decimal("0"), Decimal("0"), Decimal("0"))

        start_value = equity_curve[0][1]
        end_value = equity_curve[-1][1]

        # Total return: (end_value - start_value) / start_value
        if start_value == 0:
            return (Decimal("0"), Decimal("0"), Decimal("0"))

        total_return = (end_value - start_value) / start_value

        # Calculate time period in years
        start_date = equity_curve[0][0]
        end_date = equity_curve[-1][0]
        days = (end_date - start_date).days
        years = Decimal(days) / Decimal("365")

        # Annualized return: total_return * (365 / days)
        if days == 0:
            annualized_return = Decimal("0")
        else:
            annualized_return = total_return * (Decimal("365") / Decimal(days))

        # CAGR: (end_value / start_value) ^ (1 / years) - 1
        if years == 0:
            cagr = Decimal("0")
        else:
            # Use Python's float power for fractional exponents, then convert back
            ratio = float(end_value / start_value)
            cagr = Decimal(str(ratio ** float(Decimal("1") / years))) - Decimal("1")

        return (total_return, annualized_return, cagr)

    def _calculate_drawdown(
        self,
        equity_curve: list[tuple[datetime, Decimal]]
    ) -> tuple[Decimal, int]:
        """
        Calculate maximum drawdown and duration.

        Args:
            equity_curve: Portfolio value over time

        Returns:
            Tuple of (max_drawdown, max_drawdown_duration_days)
        """
        if not equity_curve or len(equity_curve) < 2:
            return (Decimal("0"), 0)

        max_drawdown = Decimal("0")
        max_drawdown_duration = 0
        peak = equity_curve[0][1]
        peak_date = equity_curve[0][0]

        for timestamp, value in equity_curve:
            # Track new peak
            if value > peak:
                peak = value
                peak_date = timestamp
            else:
                # Calculate drawdown from peak
                drawdown = (peak - value) / peak

                # Update max drawdown
                if drawdown > max_drawdown:
                    max_drawdown = drawdown
                    max_drawdown_duration = (timestamp - peak_date).days

        return (max_drawdown, max_drawdown_duration)

    def _calculate_sharpe(
        self,
        equity_curve: list[tuple[datetime, Decimal]],
        risk_free_rate: Decimal
    ) -> Decimal:
        """
        Calculate Sharpe ratio.

        Formula: (annualized_return - risk_free_rate) / annualized_volatility

        Args:
            equity_curve: Portfolio value over time
            risk_free_rate: Annual risk-free rate (e.g., 0.02 for 2%)

        Returns:
            Sharpe ratio
        """
        if not equity_curve or len(equity_curve) < 2:
            return Decimal("0")

        # Calculate periodic returns
        returns = []
        for i in range(1, len(equity_curve)):
            prev_value = equity_curve[i - 1][1]
            curr_value = equity_curve[i][1]

            if prev_value > 0:
                period_return = (curr_value - prev_value) / prev_value
                returns.append(float(period_return))

        if not returns:
            return Decimal("0")

        # Calculate mean return
        mean_return = sum(returns) / len(returns)

        # Calculate volatility (standard deviation)
        # Use sample standard deviation (n-1) for better estimate
        if len(returns) > 1:
            variance = sum((r - mean_return) ** 2 for r in returns) / (len(returns) - 1)
        else:
            variance = 0
        volatility = variance ** 0.5

        # Annualize based on number of periods
        # Calculate average days per period
        start_date = equity_curve[0][0]
        end_date = equity_curve[-1][0]
        total_days = (end_date - start_date).days

        if total_days > 0 and len(returns) > 0:
            days_per_period = total_days / len(returns)
            # Use 252 trading days per year for annualization
            periods_per_year = 252 / days_per_period
        else:
            periods_per_year = 1

        # Annualize mean return and volatility
        annualized_mean_return = mean_return * periods_per_year
        annualized_volatility = volatility * (periods_per_year ** 0.5)

        # Calculate Sharpe ratio
        if annualized_volatility == 0:
            return Decimal("0")

        sharpe = (annualized_mean_return - float(risk_free_rate)) / annualized_volatility

        return Decimal(str(sharpe))

    def _calculate_trade_stats(
        self,
        trades: list[Trade]
    ) -> tuple[Decimal, Decimal, Decimal, Decimal, int, int, int]:
        """
        Calculate trade statistics.

        Args:
            trades: List of completed trades

        Returns:
            Tuple of (win_rate, profit_factor, avg_win, avg_loss,
                     total_trades, winning_trades, losing_trades)
        """
        if not trades:
            return (
                Decimal("0"),
                Decimal("0"),
                Decimal("0"),
                Decimal("0"),
                0,
                0,
                0,
            )

        # Separate winning and losing trades
        wins = [t for t in trades if t.pnl > 0]
        losses = [t for t in trades if t.pnl < 0]

        total_trades = len(trades)
        winning_trades = len(wins)
        losing_trades = len(losses)

        # Win rate: wins / total_trades
        win_rate = Decimal(winning_trades) / Decimal(total_trades)

        # Average win: sum(winning_pnls) / num_wins
        if wins:
            avg_win = sum(t.pnl for t in wins) / Decimal(len(wins))
        else:
            avg_win = Decimal("0")

        # Average loss: sum(losing_pnls) / num_losses
        if losses:
            avg_loss = sum(t.pnl for t in losses) / Decimal(len(losses))
        else:
            avg_loss = Decimal("0")

        # Profit factor: gross_profit / gross_loss (or 0 if no losses)
        if losses:
            gross_profit = Decimal(sum((t.pnl for t in wins), Decimal("0")))
            gross_loss = abs(Decimal(sum((t.pnl for t in losses), Decimal("0"))))  # Make positive
            if gross_loss > 0:
                profit_factor = gross_profit / gross_loss
            else:
                profit_factor = Decimal("0")
        else:
            # No losses - return 0 or could be considered infinite
            # Per typical convention, return 0 if no losses
            profit_factor = Decimal("0")

        return (
            win_rate,
            profit_factor,
            avg_win,
            avg_loss,
            total_trades,
            winning_trades,
            losing_trades,
        )
