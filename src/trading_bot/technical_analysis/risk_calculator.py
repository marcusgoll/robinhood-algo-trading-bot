"""Risk Calculator - Tools 17-18 from TA framework.

The grown-ups section. If you don't know your R per trade, you're gambling.

Handles:
- R-Multiple / Risk-Reward Ratio (Tool 17)
- Position Sizing & Max Risk Per Trade (Tool 18)

Size is more important than entries. Most blowups are position sizing failures.
"""

import numpy as np
from typing import Optional, Tuple
from dataclasses import dataclass


@dataclass
class RiskRewardResult:
    """Risk-reward analysis result."""
    entry_price: float
    stop_loss: float
    take_profit: float
    risk_amount: float  # Distance from entry to stop
    reward_amount: float  # Distance from entry to target
    r_multiple: float  # Reward / Risk ratio
    risk_pct: float  # Risk as % of entry price
    reward_pct: float  # Reward as % of entry price
    acceptable: bool  # True if R-multiple meets minimum threshold
    recommendation: str


@dataclass
class PositionSizeResult:
    """Position sizing result."""
    account_size: float
    risk_per_trade_pct: float
    risk_per_trade_usd: float
    entry_price: float
    stop_loss: float
    position_size_shares: float
    position_size_usd: float
    position_pct_of_account: float
    max_loss_if_stopped: float
    recommendation: str


@dataclass
class TradeSetupResult:
    """Complete trade setup with risk parameters."""
    symbol: str
    direction: str  # 'long' or 'short'
    entry_price: float
    stop_loss: float
    take_profit: float
    position_size_shares: float
    position_size_usd: float
    risk_amount_usd: float
    reward_amount_usd: float
    r_multiple: float
    risk_pct_of_account: float
    expected_value: float  # EV = (win_rate × avg_win) - (loss_rate × avg_loss)
    quality_score: float  # 0-100


class RiskCalculator:
    """Calculate position sizing and risk management parameters.

    No entry is worth taking if the risk management is trash.
    This module ensures every trade has:
    - Clear entry, stop, target
    - Proper position sizing
    - Positive expected value
    - Risk within account limits
    """

    def __init__(
        self,
        min_r_multiple: float = 2.0,
        max_risk_per_trade: float = 1.0,  # 1% of account
        default_win_rate: float = 0.45  # Conservative default
    ):
        """Initialize risk calculator.

        Args:
            min_r_multiple: Minimum acceptable R-multiple (default: 2.0)
            max_risk_per_trade: Max risk per trade as % of account (default: 1.0%)
            default_win_rate: Default win rate for EV calculation (default: 45%)
        """
        self.min_r_multiple = min_r_multiple
        self.max_risk_per_trade = max_risk_per_trade
        self.default_win_rate = default_win_rate

    # Tool 17: R-Multiple / Risk-Reward Ratio
    def calculate_risk_reward(
        self,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        direction: str = 'long'
    ) -> RiskRewardResult:
        """Calculate risk-reward ratio and R-multiple.

        Args:
            entry_price: Entry price
            stop_loss: Stop loss price
            take_profit: Take profit target
            direction: 'long' or 'short'

        Returns:
            RiskRewardResult with R-multiple and assessment

        Rule of thumb:
        - Aim for at least 2R if win rate ~40-50%
        - Higher R allows lower win rate
        - Lower R requires higher win rate
        - Expected Value = (win% × avg_win) - (loss% × avg_loss)
        """
        if direction == 'long':
            risk_amount = entry_price - stop_loss
            reward_amount = take_profit - entry_price
        else:  # short
            risk_amount = stop_loss - entry_price
            reward_amount = entry_price - take_profit

        # Validate
        if risk_amount <= 0:
            raise ValueError(f"Invalid stop loss. Risk amount must be positive. Got {risk_amount}")
        if reward_amount <= 0:
            raise ValueError(f"Invalid take profit. Reward amount must be positive. Got {reward_amount}")

        # Calculate R-multiple
        r_multiple = reward_amount / risk_amount

        # Calculate percentages
        risk_pct = (risk_amount / entry_price) * 100
        reward_pct = (reward_amount / entry_price) * 100

        # Assess if acceptable
        acceptable = r_multiple >= self.min_r_multiple

        # Generate recommendation
        if r_multiple >= 3.0:
            recommendation = f"Excellent R-multiple ({r_multiple:.2f}R). Setup has asymmetric reward."
        elif r_multiple >= 2.0:
            recommendation = f"Good R-multiple ({r_multiple:.2f}R). Acceptable risk-reward."
        elif r_multiple >= 1.5:
            recommendation = f"Marginal R-multiple ({r_multiple:.2f}R). Requires high win rate (>60%)."
        else:
            recommendation = f"Poor R-multiple ({r_multiple:.2f}R). SKIP - insufficient reward for risk."

        return RiskRewardResult(
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_amount=risk_amount,
            reward_amount=reward_amount,
            r_multiple=r_multiple,
            risk_pct=risk_pct,
            reward_pct=reward_pct,
            acceptable=acceptable,
            recommendation=recommendation
        )

    # Tool 18: Position Sizing
    def calculate_position_size(
        self,
        account_size: float,
        entry_price: float,
        stop_loss: float,
        direction: str = 'long',
        risk_per_trade_pct: Optional[float] = None,
        volatility_adjustment: bool = True,
        atr: Optional[float] = None
    ) -> PositionSizeResult:
        """Calculate position size based on risk parameters.

        Args:
            account_size: Total account size in USD
            entry_price: Entry price
            stop_loss: Stop loss price
            direction: 'long' or 'short'
            risk_per_trade_pct: Risk per trade as % (default: use max_risk_per_trade)
            volatility_adjustment: Reduce size in high volatility (default: True)
            atr: Average True Range for volatility adjustment (optional)

        Returns:
            PositionSizeResult with position size and parameters

        Formula:
            Position Size = (Account Size × Risk %) / (Entry - Stop)

        Example:
            Account: $10,000
            Risk: 1% = $100
            Entry: $50
            Stop: $48
            Risk per share: $2
            Position Size: $100 / $2 = 50 shares = $2,500 (25% of account)
        """
        if risk_per_trade_pct is None:
            risk_per_trade_pct = self.max_risk_per_trade

        # Calculate risk per trade in USD
        risk_per_trade_usd = account_size * (risk_per_trade_pct / 100)

        # Calculate risk per share
        if direction == 'long':
            risk_per_share = entry_price - stop_loss
        else:  # short
            risk_per_share = stop_loss - entry_price

        if risk_per_share <= 0:
            raise ValueError(f"Invalid stop loss. Risk per share must be positive. Got {risk_per_share}")

        # Calculate position size in shares
        position_size_shares = risk_per_trade_usd / risk_per_share

        # Apply volatility adjustment if requested
        if volatility_adjustment and atr is not None:
            # Reduce size if high volatility
            atr_pct = (atr / entry_price) * 100

            if atr_pct > 3.0:  # High volatility (>3% ATR)
                adjustment_factor = 0.5  # Half size
                position_size_shares *= adjustment_factor
                volatility_note = " (reduced 50% due to high volatility)"
            elif atr_pct > 2.0:  # Elevated volatility
                adjustment_factor = 0.75  # 75% size
                position_size_shares *= adjustment_factor
                volatility_note = " (reduced 25% due to elevated volatility)"
            else:
                volatility_note = ""
        else:
            volatility_note = ""

        # Calculate position size in USD
        position_size_usd = position_size_shares * entry_price

        # Calculate position as % of account
        position_pct_of_account = (position_size_usd / account_size) * 100

        # Calculate max loss if stopped out
        max_loss_if_stopped = position_size_shares * risk_per_share

        # Generate recommendation
        if position_pct_of_account > 50:
            recommendation = (
                f"WARNING: Position size is {position_pct_of_account:.1f}% of account. "
                f"This is too large. Consider widening stop or reducing risk%{volatility_note}"
            )
        elif position_pct_of_account > 30:
            recommendation = (
                f"Position size is {position_pct_of_account:.1f}% of account. "
                f"This is aggressive but manageable{volatility_note}"
            )
        else:
            recommendation = (
                f"Position size is {position_pct_of_account:.1f}% of account. "
                f"Risk is well-controlled{volatility_note}"
            )

        return PositionSizeResult(
            account_size=account_size,
            risk_per_trade_pct=risk_per_trade_pct,
            risk_per_trade_usd=risk_per_trade_usd,
            entry_price=entry_price,
            stop_loss=stop_loss,
            position_size_shares=position_size_shares,
            position_size_usd=position_size_usd,
            position_pct_of_account=position_pct_of_account,
            max_loss_if_stopped=max_loss_if_stopped,
            recommendation=recommendation
        )

    def calculate_complete_setup(
        self,
        symbol: str,
        direction: str,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        account_size: float,
        risk_per_trade_pct: Optional[float] = None,
        win_rate: Optional[float] = None,
        atr: Optional[float] = None
    ) -> TradeSetupResult:
        """Calculate complete trade setup with all risk parameters.

        Args:
            symbol: Trading symbol
            direction: 'long' or 'short'
            entry_price: Entry price
            stop_loss: Stop loss price
            take_profit: Take profit target
            account_size: Account size in USD
            risk_per_trade_pct: Risk per trade % (optional)
            win_rate: Historical win rate for EV calculation (optional)
            atr: ATR for volatility adjustment (optional)

        Returns:
            TradeSetupResult with complete setup

        This is the final output you use for actual trading.
        """
        # Calculate risk-reward
        rr_result = self.calculate_risk_reward(
            entry_price, stop_loss, take_profit, direction
        )

        # Calculate position size
        pos_result = self.calculate_position_size(
            account_size, entry_price, stop_loss, direction,
            risk_per_trade_pct, volatility_adjustment=True, atr=atr
        )

        # Calculate actual USD amounts
        risk_amount_usd = pos_result.max_loss_if_stopped
        reward_amount_usd = pos_result.position_size_shares * rr_result.reward_amount

        # Calculate risk as % of account
        risk_pct_of_account = (risk_amount_usd / account_size) * 100

        # Calculate expected value
        actual_win_rate = win_rate if win_rate is not None else self.default_win_rate
        loss_rate = 1 - actual_win_rate

        # EV = (win_rate × avg_win) - (loss_rate × avg_loss)
        # Assuming avg_win = reward_amount and avg_loss = risk_amount
        expected_value = (actual_win_rate * reward_amount_usd) - (loss_rate * risk_amount_usd)

        # Calculate quality score
        quality_score = self._calculate_quality_score(
            rr_result.r_multiple,
            risk_pct_of_account,
            pos_result.position_pct_of_account,
            expected_value,
            actual_win_rate
        )

        return TradeSetupResult(
            symbol=symbol,
            direction=direction,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            position_size_shares=pos_result.position_size_shares,
            position_size_usd=pos_result.position_size_usd,
            risk_amount_usd=risk_amount_usd,
            reward_amount_usd=reward_amount_usd,
            r_multiple=rr_result.r_multiple,
            risk_pct_of_account=risk_pct_of_account,
            expected_value=expected_value,
            quality_score=quality_score
        )

    def _calculate_quality_score(
        self,
        r_multiple: float,
        risk_pct_of_account: float,
        position_pct_of_account: float,
        expected_value: float,
        win_rate: float
    ) -> float:
        """Calculate overall trade quality score (0-100).

        Higher score = better trade setup
        """
        score = 50.0  # Base

        # R-multiple (max +30 points)
        if r_multiple >= 3.0:
            score += 30
        elif r_multiple >= 2.0:
            score += 20
        elif r_multiple >= 1.5:
            score += 10

        # Risk control (max +20 points)
        if risk_pct_of_account <= 0.5:
            score += 20
        elif risk_pct_of_account <= 1.0:
            score += 15
        elif risk_pct_of_account <= 2.0:
            score += 5
        else:
            score -= 10  # Too much risk

        # Position size (max +10 points)
        if position_pct_of_account <= 25:
            score += 10
        elif position_pct_of_account <= 40:
            score += 5
        else:
            score -= 10  # Position too large

        # Expected value (max +20 points)
        if expected_value > 0:
            ev_score = min(20, expected_value / 10)  # Scale EV to score
            score += ev_score
        else:
            score -= 20  # Negative EV

        # Win rate adjustment (max +/-10 points)
        if win_rate >= 0.6:
            score += 10
        elif win_rate >= 0.5:
            score += 5
        elif win_rate < 0.4:
            score -= 10

        return max(0, min(100, score))

    def calculate_kelly_criterion(
        self,
        win_rate: float,
        avg_win: float,
        avg_loss: float
    ) -> float:
        """Calculate Kelly Criterion for optimal position sizing.

        Kelly % = W - [(1 - W) / R]
        where:
            W = win rate
            R = avg_win / avg_loss

        Args:
            win_rate: Historical win rate (0-1)
            avg_win: Average winning trade size
            avg_loss: Average losing trade size

        Returns:
            Optimal position size as fraction of account (0-1)

        WARNING: Kelly is aggressive. Most traders use Kelly / 2 or Kelly / 4.
        """
        if avg_loss == 0:
            raise ValueError("Average loss cannot be zero")

        r_ratio = avg_win / avg_loss
        kelly_pct = win_rate - ((1 - win_rate) / r_ratio)

        # Kelly can be negative (system has negative expectancy - don't trade!)
        kelly_pct = max(0, kelly_pct)

        # Cap at 25% (Kelly can suggest crazy high values)
        kelly_pct = min(0.25, kelly_pct)

        return kelly_pct

    def calculate_sharpe_ratio(
        self,
        returns: list[float],
        risk_free_rate: float = 0.0
    ) -> float:
        """Calculate Sharpe Ratio for strategy performance.

        Sharpe = (Average Return - Risk Free Rate) / Std Dev of Returns

        Args:
            returns: List of trade returns (as decimals, e.g., 0.05 = 5%)
            risk_free_rate: Risk-free rate (default: 0)

        Returns:
            Sharpe ratio (higher is better, >1 is good, >2 is excellent)
        """
        if not returns:
            return 0.0

        returns_array = np.array(returns)
        avg_return = np.mean(returns_array)
        std_return = np.std(returns_array)

        if std_return == 0:
            return 0.0

        sharpe = (avg_return - risk_free_rate) / std_return
        return float(sharpe)

    def calculate_max_drawdown(
        self,
        equity_curve: list[float]
    ) -> Tuple[float, int, int]:
        """Calculate maximum drawdown from equity curve.

        Args:
            equity_curve: List of account values over time

        Returns:
            (max_drawdown_pct, start_index, end_index)

        Max drawdown = largest peak-to-trough decline
        """
        if not equity_curve or len(equity_curve) < 2:
            return 0.0, 0, 0

        equity_array = np.array(equity_curve)
        running_max = np.maximum.accumulate(equity_array)
        drawdowns = (equity_array - running_max) / running_max

        max_dd_idx = np.argmin(drawdowns)
        max_dd = abs(float(drawdowns[max_dd_idx]))

        # Find start of drawdown (last peak before max DD)
        start_idx = np.argmax(equity_array[:max_dd_idx+1])

        return max_dd * 100, start_idx, max_dd_idx
