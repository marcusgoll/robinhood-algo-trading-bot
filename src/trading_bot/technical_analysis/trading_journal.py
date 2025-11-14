"""Trading Journal - Tools 19-20 from TA framework.

Backtesting & Forward-Testing (Tool 19)
- Validate rules on historical data
- Test across multiple market regimes
- Track what actually works

Trading Journal & Performance Review (Tool 20)
- Log every trade with screenshots, reasons, emotions, outcomes
- Track: setup type, R-multiple, rule adherence, market context
- Review weekly/monthly to kill bad behaviors & refine rules

No journal = no improvement. You can't fix what you don't measure.
"""

import json
import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class TradeRecord:
    """Individual trade record for journaling."""
    # Trade identification
    trade_id: str
    symbol: str
    direction: str  # 'long' or 'short'
    entry_timestamp: datetime
    exit_timestamp: Optional[datetime] = None

    # Trade parameters
    entry_price: float = 0.0
    exit_price: Optional[float] = None
    stop_loss: float = 0.0
    take_profit: float = 0.0
    position_size: float = 0.0

    # Outcomes
    status: str = 'open'  # 'open', 'closed_win', 'closed_loss', 'closed_breakeven'
    pnl_usd: Optional[float] = None
    pnl_pct: Optional[float] = None
    r_multiple: Optional[float] = None  # Actual R achieved
    max_favorable_excursion: Optional[float] = None  # MFE - how far trade went in your favor
    max_adverse_excursion: Optional[float] = None  # MAE - how far trade went against you

    # Analysis
    setup_type: str = ''  # 'breakout', 'pullback', 'reversal', etc.
    market_regime: str = ''  # 'trending', 'ranging', 'volatile'
    trend_direction: str = ''  # 'uptrend', 'downtrend', 'sideways'
    timeframe: str = ''

    # Indicators at entry
    indicators: Dict[str, Any] = None

    # Trade quality
    followed_rules: bool = True
    mistakes: List[str] = None
    emotions: List[str] = None  # 'fear', 'greed', 'fomo', 'revenge', 'calm'
    notes: str = ''

    # Screenshots
    entry_screenshot: Optional[str] = None
    exit_screenshot: Optional[str] = None

    def __post_init__(self):
        """Initialize mutable defaults."""
        if self.indicators is None:
            self.indicators = {}
        if self.mistakes is None:
            self.mistakes = []
        if self.emotions is None:
            self.emotions = []


@dataclass
class PerformanceMetrics:
    """Performance metrics for strategy/period."""
    # Basic metrics
    total_trades: int
    winning_trades: int
    losing_trades: int
    breakeven_trades: int
    win_rate: float  # 0-100

    # P&L metrics
    total_pnl: float
    total_pnl_pct: float
    avg_win: float
    avg_loss: float
    largest_win: float
    largest_loss: float
    profit_factor: float  # Total wins / Total losses

    # R-multiple metrics
    avg_r_multiple: float
    expectancy: float  # Average R per trade
    total_r_achieved: float

    # Risk metrics
    max_drawdown: float
    max_drawdown_pct: float
    sharpe_ratio: float
    sortino_ratio: float

    # Trade quality
    avg_trade_duration: float  # In hours
    best_setup_type: str
    worst_setup_type: str
    rule_adherence_rate: float  # % of trades following rules

    # Regime performance
    performance_by_regime: Dict[str, dict]


class TradingJournal:
    """Track and analyze trading performance.

    This is your feedback loop. Use it to:
    1. Log every trade (wins AND losses)
    2. Track what setups actually work
    3. Identify bad habits and emotional patterns
    4. Calculate real performance metrics
    5. Optimize your system based on data

    No journal = flying blind
    """

    def __init__(
        self,
        journal_path: str = './trading_journal.json',
        equity_start: float = 10000.0
    ):
        """Initialize trading journal.

        Args:
            journal_path: Path to journal file
            equity_start: Starting account equity
        """
        self.journal_path = Path(journal_path)
        self.equity_start = equity_start
        self.trades: List[TradeRecord] = []
        self.equity_curve: List[float] = [equity_start]

        # Load existing journal if it exists
        if self.journal_path.exists():
            self._load_journal()

        logger.info(f"Trading journal initialized at {journal_path}")

    def log_trade_entry(
        self,
        trade_id: str,
        symbol: str,
        direction: str,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        position_size: float,
        setup_type: str = '',
        market_regime: str = '',
        trend_direction: str = '',
        timeframe: str = '',
        indicators: Optional[Dict] = None,
        notes: str = '',
        emotions: Optional[List[str]] = None,
        entry_screenshot: Optional[str] = None
    ) -> TradeRecord:
        """Log trade entry.

        Args:
            trade_id: Unique trade ID
            symbol: Symbol traded
            direction: 'long' or 'short'
            entry_price: Entry price
            stop_loss: Stop loss price
            take_profit: Take profit price
            position_size: Position size in shares/contracts
            setup_type: Type of setup
            market_regime: Market regime at entry
            trend_direction: Trend direction
            timeframe: Timeframe traded
            indicators: Indicator values at entry
            notes: Trade notes
            emotions: Emotional state
            entry_screenshot: Path to entry screenshot

        Returns:
            TradeRecord object
        """
        trade = TradeRecord(
            trade_id=trade_id,
            symbol=symbol,
            entry_timestamp=datetime.now(),
            direction=direction,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            position_size=position_size,
            setup_type=setup_type,
            market_regime=market_regime,
            trend_direction=trend_direction,
            timeframe=timeframe,
            indicators=indicators or {},
            notes=notes,
            emotions=emotions or [],
            entry_screenshot=entry_screenshot
        )

        self.trades.append(trade)
        self._save_journal()

        logger.info(f"Trade entry logged: {trade_id} {symbol} {direction} @ {entry_price}")
        return trade

    def log_trade_exit(
        self,
        trade_id: str,
        exit_price: float,
        followed_rules: bool = True,
        mistakes: Optional[List[str]] = None,
        emotions: Optional[List[str]] = None,
        notes: str = '',
        exit_screenshot: Optional[str] = None
    ):
        """Log trade exit.

        Args:
            trade_id: Trade ID to close
            exit_price: Exit price
            followed_rules: Whether trading rules were followed
            mistakes: List of mistakes made
            emotions: Emotional state at exit
            notes: Exit notes
            exit_screenshot: Path to exit screenshot
        """
        # Find trade
        trade = next((t for t in self.trades if t.trade_id == trade_id), None)

        if not trade:
            logger.error(f"Trade {trade_id} not found")
            return

        if trade.status != 'open':
            logger.warning(f"Trade {trade_id} already closed")
            return

        # Update trade
        trade.exit_timestamp = datetime.now()
        trade.exit_price = exit_price
        trade.followed_rules = followed_rules
        trade.mistakes = mistakes or []
        if emotions:
            trade.emotions.extend(emotions)
        if notes:
            trade.notes += f" | Exit: {notes}"
        trade.exit_screenshot = exit_screenshot

        # Calculate outcomes
        if trade.direction == 'long':
            pnl_per_share = exit_price - trade.entry_price
            risk_per_share = trade.entry_price - trade.stop_loss
        else:  # short
            pnl_per_share = trade.entry_price - exit_price
            risk_per_share = trade.stop_loss - trade.entry_price

        trade.pnl_usd = pnl_per_share * trade.position_size
        trade.pnl_pct = (pnl_per_share / trade.entry_price) * 100

        # Calculate R-multiple
        if risk_per_share > 0:
            trade.r_multiple = pnl_per_share / risk_per_share
        else:
            trade.r_multiple = 0.0

        # Determine status
        if trade.pnl_usd > 0:
            trade.status = 'closed_win'
        elif trade.pnl_usd < 0:
            trade.status = 'closed_loss'
        else:
            trade.status = 'closed_breakeven'

        # Update equity curve
        current_equity = self.equity_curve[-1]
        new_equity = current_equity + trade.pnl_usd
        self.equity_curve.append(new_equity)

        self._save_journal()

        logger.info(
            f"Trade exit logged: {trade_id} {trade.status} "
            f"PnL: ${trade.pnl_usd:.2f} ({trade.r_multiple:.2f}R)"
        )

    def calculate_performance(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> PerformanceMetrics:
        """Calculate performance metrics for a period.

        Args:
            start_date: Start date (None = all time)
            end_date: End date (None = now)

        Returns:
            PerformanceMetrics with all statistics
        """
        # Filter trades by date
        filtered_trades = [
            t for t in self.trades
            if t.status.startswith('closed') and
            (start_date is None or t.entry_timestamp >= start_date) and
            (end_date is None or t.exit_timestamp <= end_date)
        ]

        if not filtered_trades:
            logger.warning("No closed trades in period")
            return self._empty_metrics()

        # Basic counts
        total_trades = len(filtered_trades)
        winning_trades = sum(1 for t in filtered_trades if t.status == 'closed_win')
        losing_trades = sum(1 for t in filtered_trades if t.status == 'closed_loss')
        breakeven_trades = sum(1 for t in filtered_trades if t.status == 'closed_breakeven')

        win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0

        # P&L metrics
        total_pnl = sum(t.pnl_usd for t in filtered_trades if t.pnl_usd is not None)
        total_pnl_pct = (total_pnl / self.equity_start) * 100

        wins = [t.pnl_usd for t in filtered_trades if t.status == 'closed_win']
        losses = [abs(t.pnl_usd) for t in filtered_trades if t.status == 'closed_loss']

        avg_win = np.mean(wins) if wins else 0
        avg_loss = np.mean(losses) if losses else 0
        largest_win = max(wins) if wins else 0
        largest_loss = max(losses) if losses else 0

        total_wins = sum(wins) if wins else 0
        total_losses = sum(losses) if losses else 1  # Avoid division by zero

        profit_factor = total_wins / total_losses

        # R-multiple metrics
        r_multiples = [t.r_multiple for t in filtered_trades if t.r_multiple is not None]
        avg_r_multiple = np.mean(r_multiples) if r_multiples else 0
        total_r_achieved = sum(r_multiples) if r_multiples else 0

        # Expectancy = (Win% × Avg Win) - (Loss% × Avg Loss)
        expectancy = (win_rate / 100 * avg_win) - ((100 - win_rate) / 100 * avg_loss)

        # Risk metrics
        equity_for_period = [self.equity_start]
        running_equity = self.equity_start
        for trade in filtered_trades:
            running_equity += trade.pnl_usd
            equity_for_period.append(running_equity)

        max_dd, max_dd_pct = self._calculate_max_drawdown(equity_for_period)

        # Calculate Sharpe ratio
        returns = [(equity_for_period[i] - equity_for_period[i-1]) / equity_for_period[i-1]
                   for i in range(1, len(equity_for_period))]
        sharpe_ratio = self._calculate_sharpe(returns)
        sortino_ratio = self._calculate_sortino(returns)

        # Trade duration
        durations = []
        for t in filtered_trades:
            if t.exit_timestamp:
                duration = (t.exit_timestamp - t.entry_timestamp).total_seconds() / 3600
                durations.append(duration)
        avg_trade_duration = np.mean(durations) if durations else 0

        # Setup type analysis
        setup_performance = {}
        for trade in filtered_trades:
            if trade.setup_type not in setup_performance:
                setup_performance[trade.setup_type] = {'wins': 0, 'losses': 0, 'pnl': 0}

            if trade.status == 'closed_win':
                setup_performance[trade.setup_type]['wins'] += 1
            elif trade.status == 'closed_loss':
                setup_performance[trade.setup_type]['losses'] += 1

            setup_performance[trade.setup_type]['pnl'] += trade.pnl_usd

        best_setup = max(setup_performance.items(), key=lambda x: x[1]['pnl'])[0] if setup_performance else 'N/A'
        worst_setup = min(setup_performance.items(), key=lambda x: x[1]['pnl'])[0] if setup_performance else 'N/A'

        # Rule adherence
        rule_followed = sum(1 for t in filtered_trades if t.followed_rules)
        rule_adherence_rate = (rule_followed / total_trades) * 100 if total_trades > 0 else 0

        # Regime performance
        regime_performance = {}
        for trade in filtered_trades:
            regime = trade.market_regime or 'unknown'
            if regime not in regime_performance:
                regime_performance[regime] = {'trades': 0, 'wins': 0, 'pnl': 0}

            regime_performance[regime]['trades'] += 1
            if trade.status == 'closed_win':
                regime_performance[regime]['wins'] += 1
            regime_performance[regime]['pnl'] += trade.pnl_usd

        for regime in regime_performance:
            total = regime_performance[regime]['trades']
            regime_performance[regime]['win_rate'] = (regime_performance[regime]['wins'] / total * 100) if total > 0 else 0

        return PerformanceMetrics(
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            breakeven_trades=breakeven_trades,
            win_rate=win_rate,
            total_pnl=total_pnl,
            total_pnl_pct=total_pnl_pct,
            avg_win=avg_win,
            avg_loss=avg_loss,
            largest_win=largest_win,
            largest_loss=largest_loss,
            profit_factor=profit_factor,
            avg_r_multiple=avg_r_multiple,
            expectancy=expectancy,
            total_r_achieved=total_r_achieved,
            max_drawdown=max_dd,
            max_drawdown_pct=max_dd_pct,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            avg_trade_duration=avg_trade_duration,
            best_setup_type=best_setup,
            worst_setup_type=worst_setup,
            rule_adherence_rate=rule_adherence_rate,
            performance_by_regime=regime_performance
        )

    def generate_review_report(self) -> str:
        """Generate performance review report."""
        metrics = self.calculate_performance()

        report = []
        report.append("="*80)
        report.append("TRADING PERFORMANCE REVIEW")
        report.append("="*80)

        report.append(f"\nOVERALL STATISTICS:")
        report.append(f"  Total Trades: {metrics.total_trades}")
        report.append(f"  Wins: {metrics.winning_trades} | Losses: {metrics.losing_trades} | BE: {metrics.breakeven_trades}")
        report.append(f"  Win Rate: {metrics.win_rate:.1f}%")

        report.append(f"\nP&L METRICS:")
        report.append(f"  Total P&L: ${metrics.total_pnl:.2f} ({metrics.total_pnl_pct:.2f}%)")
        report.append(f"  Avg Win: ${metrics.avg_win:.2f} | Avg Loss: ${metrics.avg_loss:.2f}")
        report.append(f"  Largest Win: ${metrics.largest_win:.2f} | Largest Loss: ${metrics.largest_loss:.2f}")
        report.append(f"  Profit Factor: {metrics.profit_factor:.2f}")
        report.append(f"  Expectancy: ${metrics.expectancy:.2f} per trade")

        report.append(f"\nR-MULTIPLE METRICS:")
        report.append(f"  Avg R-Multiple: {metrics.avg_r_multiple:.2f}R")
        report.append(f"  Total R Achieved: {metrics.total_r_achieved:.2f}R")

        report.append(f"\nRISK METRICS:")
        report.append(f"  Max Drawdown: ${metrics.max_drawdown:.2f} ({metrics.max_drawdown_pct:.2f}%)")
        report.append(f"  Sharpe Ratio: {metrics.sharpe_ratio:.2f}")
        report.append(f"  Sortino Ratio: {metrics.sortino_ratio:.2f}")

        report.append(f"\nTRADE QUALITY:")
        report.append(f"  Avg Trade Duration: {metrics.avg_trade_duration:.1f} hours")
        report.append(f"  Best Setup Type: {metrics.best_setup_type}")
        report.append(f"  Worst Setup Type: {metrics.worst_setup_type}")
        report.append(f"  Rule Adherence Rate: {metrics.rule_adherence_rate:.1f}%")

        report.append(f"\nPERFORMANCE BY REGIME:")
        for regime, data in metrics.performance_by_regime.items():
            report.append(
                f"  {regime}: {data['trades']} trades, "
                f"{data['win_rate']:.1f}% wins, "
                f"${data['pnl']:.2f} P&L"
            )

        report.append("="*80)

        return "\n".join(report)

    def _calculate_max_drawdown(self, equity_curve: List[float]) -> tuple:
        """Calculate max drawdown."""
        equity_array = np.array(equity_curve)
        running_max = np.maximum.accumulate(equity_array)
        drawdowns = equity_array - running_max

        max_dd = abs(np.min(drawdowns))
        max_dd_pct = (max_dd / self.equity_start) * 100

        return max_dd, max_dd_pct

    def _calculate_sharpe(self, returns: List[float]) -> float:
        """Calculate Sharpe ratio."""
        if not returns:
            return 0.0

        returns_array = np.array(returns)
        avg_return = np.mean(returns_array)
        std_return = np.std(returns_array)

        if std_return == 0:
            return 0.0

        # Annualized Sharpe (assuming daily returns)
        sharpe = (avg_return / std_return) * np.sqrt(252)
        return float(sharpe)

    def _calculate_sortino(self, returns: List[float]) -> float:
        """Calculate Sortino ratio (only penalizes downside volatility)."""
        if not returns:
            return 0.0

        returns_array = np.array(returns)
        avg_return = np.mean(returns_array)

        # Only calculate std of negative returns
        negative_returns = returns_array[returns_array < 0]
        if len(negative_returns) == 0:
            return 0.0

        downside_std = np.std(negative_returns)

        if downside_std == 0:
            return 0.0

        sortino = (avg_return / downside_std) * np.sqrt(252)
        return float(sortino)

    def _empty_metrics(self) -> PerformanceMetrics:
        """Return empty metrics."""
        return PerformanceMetrics(
            total_trades=0, winning_trades=0, losing_trades=0, breakeven_trades=0,
            win_rate=0.0, total_pnl=0.0, total_pnl_pct=0.0,
            avg_win=0.0, avg_loss=0.0, largest_win=0.0, largest_loss=0.0,
            profit_factor=0.0, avg_r_multiple=0.0, expectancy=0.0, total_r_achieved=0.0,
            max_drawdown=0.0, max_drawdown_pct=0.0,
            sharpe_ratio=0.0, sortino_ratio=0.0, avg_trade_duration=0.0,
            best_setup_type='N/A', worst_setup_type='N/A',
            rule_adherence_rate=0.0, performance_by_regime={}
        )

    def _save_journal(self):
        """Save journal to file."""
        data = {
            'equity_start': self.equity_start,
            'equity_curve': self.equity_curve,
            'trades': [asdict(t) for t in self.trades]
        }

        # Convert datetimes to strings
        for trade in data['trades']:
            trade['entry_timestamp'] = trade['entry_timestamp'].isoformat() if trade['entry_timestamp'] else None
            trade['exit_timestamp'] = trade['exit_timestamp'].isoformat() if trade['exit_timestamp'] else None

        with open(self.journal_path, 'w') as f:
            json.dump(data, f, indent=2)

    def _load_journal(self):
        """Load journal from file."""
        try:
            with open(self.journal_path, 'r') as f:
                data = json.load(f)

            self.equity_start = data.get('equity_start', 10000.0)
            self.equity_curve = data.get('equity_curve', [self.equity_start])

            # Load trades
            self.trades = []
            for trade_dict in data.get('trades', []):
                # Convert timestamp strings back to datetime
                if trade_dict.get('entry_timestamp'):
                    trade_dict['entry_timestamp'] = datetime.fromisoformat(trade_dict['entry_timestamp'])
                if trade_dict.get('exit_timestamp'):
                    trade_dict['exit_timestamp'] = datetime.fromisoformat(trade_dict['exit_timestamp'])

                self.trades.append(TradeRecord(**trade_dict))

            logger.info(f"Loaded {len(self.trades)} trades from journal")

        except Exception as e:
            logger.error(f"Error loading journal: {e}")
