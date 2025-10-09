"""Test fixtures for trade logging tests.

Provides sample trade records following the TradeRecord schema from plan.md.
Constitution v1.0.0: Support for trade logging feature testing.
"""

from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import List

from src.trading_bot.logging.trade_record import TradeRecord


def sample_buy_trade() -> TradeRecord:
    """Sample BUY trade fixture.

    Returns a complete TradeRecord instance representing
    a bull flag breakout entry in paper trading mode.

    Returns:
        TradeRecord: TradeRecord instance for a BUY trade
    """
    return TradeRecord(
        # Core Trade Data (FR-002)
        timestamp=datetime.now(timezone.utc).isoformat(),
        symbol="AAPL",
        action="BUY",
        quantity=100,
        price=Decimal("150.50"),
        total_value=Decimal("15050.00"),

        # Execution Context (FR-003)
        order_id="ORD123",
        execution_mode="PAPER",
        account_id=None,

        # Strategy Metadata (FR-004)
        strategy_name="bull-flag-breakout",
        entry_type="breakout",
        stop_loss=Decimal("148.00"),
        target=Decimal("156.00"),

        # Decision Audit Trail (FR-005)
        decision_reasoning="Bull flag breakout above $150 resistance with volume confirmation",
        indicators_used=["VWAP", "EMA-9", "Volume"],
        risk_reward_ratio=2.2,

        # Outcome Tracking (FR-006) - open position
        outcome="open",
        profit_loss=None,
        hold_duration_seconds=None,
        exit_timestamp=None,
        exit_reasoning=None,

        # Performance Metrics (FR-007)
        slippage=Decimal("0.02"),
        commission=Decimal("0.00"),
        net_profit_loss=None,

        # Compliance & Audit (NFR-002)
        session_id="SES-20250109-001",
        bot_version="1.0.0",
        config_hash="abc123"
    )


def sample_sell_trade() -> TradeRecord:
    """Sample SELL trade fixture.

    Returns a complete TradeRecord instance representing
    a winning exit trade at target price.

    Returns:
        TradeRecord: TradeRecord instance for a SELL trade (winner)
    """
    # Base timestamp for entry
    entry_time = datetime.now(timezone.utc) - timedelta(minutes=13, seconds=15)
    exit_time = datetime.now(timezone.utc)

    return TradeRecord(
        # Core Trade Data (FR-002)
        timestamp=exit_time.isoformat(),
        symbol="AAPL",
        action="SELL",
        quantity=100,
        price=Decimal("152.75"),
        total_value=Decimal("15275.00"),

        # Execution Context (FR-003)
        order_id="ORD124",
        execution_mode="PAPER",
        account_id=None,

        # Strategy Metadata (FR-004)
        strategy_name="bull-flag-breakout",
        entry_type="breakout",
        stop_loss=Decimal("148.00"),
        target=Decimal("156.00"),

        # Decision Audit Trail (FR-005)
        decision_reasoning="Target reached at $152.75 (partial profit taking)",
        indicators_used=["VWAP", "EMA-9"],
        risk_reward_ratio=2.2,

        # Outcome Tracking (FR-006) - winning trade
        outcome="win",
        profit_loss=Decimal("225.00"),  # (152.75 - 150.50) * 100
        hold_duration_seconds=795,  # 13 minutes 15 seconds
        exit_timestamp=exit_time.isoformat(),
        exit_reasoning="Target hit, price stalling at resistance",

        # Performance Metrics (FR-007)
        slippage=Decimal("0.03"),
        commission=Decimal("0.00"),
        net_profit_loss=Decimal("225.00"),

        # Compliance & Audit (NFR-002)
        session_id="SES-20250109-001",
        bot_version="1.0.0",
        config_hash="abc123"
    )


def sample_loss_trade() -> TradeRecord:
    """Sample losing SELL trade fixture.

    Returns a complete TradeRecord instance representing
    a stopped-out trade at stop loss price.

    Returns:
        TradeRecord: TradeRecord instance for a SELL trade (loser)
    """
    entry_time = datetime.now(timezone.utc) - timedelta(minutes=5, seconds=30)
    exit_time = datetime.now(timezone.utc)

    return TradeRecord(
        # Core Trade Data (FR-002)
        timestamp=exit_time.isoformat(),
        symbol="TSLA",
        action="SELL",
        quantity=50,
        price=Decimal("247.50"),
        total_value=Decimal("12375.00"),

        # Execution Context (FR-003)
        order_id="ORD125",
        execution_mode="PAPER",
        account_id=None,

        # Strategy Metadata (FR-004)
        strategy_name="pullback-reversal",
        entry_type="pullback",
        stop_loss=Decimal("247.50"),
        target=Decimal("255.00"),

        # Decision Audit Trail (FR-005)
        decision_reasoning="Stop loss hit, invalidated setup",
        indicators_used=["RSI", "MACD", "Support"],
        risk_reward_ratio=3.0,

        # Outcome Tracking (FR-006) - losing trade
        outcome="loss",
        profit_loss=Decimal("-125.00"),  # (247.50 - 250.00) * 50
        hold_duration_seconds=330,  # 5 minutes 30 seconds
        exit_timestamp=exit_time.isoformat(),
        exit_reasoning="Stop loss triggered, price broke support",

        # Performance Metrics (FR-007)
        slippage=Decimal("0.05"),
        commission=Decimal("0.00"),
        net_profit_loss=Decimal("-125.00"),

        # Compliance & Audit (NFR-002)
        session_id="SES-20250109-002",
        bot_version="1.0.0",
        config_hash="abc123"
    )


def sample_breakeven_trade() -> TradeRecord:
    """Sample breakeven SELL trade fixture.

    Returns a complete TradeRecord instance representing
    a trade exited at entry price (no profit, no loss).

    Returns:
        TradeRecord: TradeRecord instance for a SELL trade (breakeven)
    """
    entry_time = datetime.now(timezone.utc) - timedelta(minutes=2)
    exit_time = datetime.now(timezone.utc)

    return TradeRecord(
        # Core Trade Data (FR-002)
        timestamp=exit_time.isoformat(),
        symbol="MSFT",
        action="SELL",
        quantity=75,
        price=Decimal("375.00"),
        total_value=Decimal("28125.00"),

        # Execution Context (FR-003)
        order_id="ORD126",
        execution_mode="PAPER",
        account_id=None,

        # Strategy Metadata (FR-004)
        strategy_name="manual",
        entry_type="reversal",
        stop_loss=Decimal("373.00"),
        target=Decimal("380.00"),

        # Decision Audit Trail (FR-005)
        decision_reasoning="Setup invalidated, exit at breakeven",
        indicators_used=["Price Action"],
        risk_reward_ratio=2.5,

        # Outcome Tracking (FR-006) - breakeven
        outcome="breakeven",
        profit_loss=Decimal("0.00"),
        hold_duration_seconds=120,  # 2 minutes
        exit_timestamp=exit_time.isoformat(),
        exit_reasoning="Setup invalidated, moved stop to breakeven",

        # Performance Metrics (FR-007)
        slippage=Decimal("0.00"),
        commission=Decimal("0.00"),
        net_profit_loss=Decimal("0.00"),

        # Compliance & Audit (NFR-002)
        session_id="SES-20250109-003",
        bot_version="1.0.0",
        config_hash="abc123"
    )


def sample_live_trade() -> TradeRecord:
    """Sample LIVE trade fixture (real money).

    Returns a complete TradeRecord instance representing
    a trade executed in live trading mode with account ID.

    Returns:
        TradeRecord: TradeRecord instance for a LIVE BUY trade
    """
    return TradeRecord(
        # Core Trade Data (FR-002)
        timestamp=datetime.now(timezone.utc).isoformat(),
        symbol="SPY",
        action="BUY",
        quantity=10,
        price=Decimal("450.25"),
        total_value=Decimal("4502.50"),

        # Execution Context (FR-003)
        order_id="ORD-LIVE-001",
        execution_mode="LIVE",
        account_id="RH-ACC-12345",  # Robinhood account ID

        # Strategy Metadata (FR-004)
        strategy_name="market-open-momentum",
        entry_type="breakout",
        stop_loss=Decimal("448.50"),
        target=Decimal("453.00"),

        # Decision Audit Trail (FR-005)
        decision_reasoning="Market open gap up with strong volume",
        indicators_used=["Volume", "Gap", "Premarket High"],
        risk_reward_ratio=1.5,

        # Outcome Tracking (FR-006) - open
        outcome="open",
        profit_loss=None,
        hold_duration_seconds=None,
        exit_timestamp=None,
        exit_reasoning=None,

        # Performance Metrics (FR-007)
        slippage=Decimal("0.10"),  # Higher slippage in live market
        commission=Decimal("0.00"),  # Robinhood is commission-free
        net_profit_loss=None,

        # Compliance & Audit (NFR-002)
        session_id="SES-LIVE-20250109-001",
        bot_version="1.0.0",
        config_hash="def456"
    )


def sample_trade_sequence() -> List[TradeRecord]:
    """Sequence of trades for integration testing.

    Returns a chronologically ordered list of trades representing
    a typical trading session with mixed outcomes.

    Returns:
        list[TradeRecord]: List of TradeRecord instances
    """
    return [
        sample_buy_trade(),      # Open BUY position
        sample_sell_trade(),     # Close with profit (win)
        sample_buy_trade(),      # Reopen position
        sample_loss_trade(),     # Different symbol, stopped out (loss)
        sample_breakeven_trade() # Breakeven exit (neutral)
    ]


def sample_multi_symbol_sequence() -> List[TradeRecord]:
    """Multi-symbol trade sequence for analytics testing.

    Returns trades across multiple symbols and strategies for testing
    aggregation and filtering queries.

    Returns:
        list[TradeRecord]: List of TradeRecord instances
    """
    trades = []

    # AAPL trades
    aapl_buy = sample_buy_trade()
    aapl_sell = sample_sell_trade()
    trades.extend([aapl_buy, aapl_sell])

    # TSLA trades
    tsla_trade = sample_loss_trade()
    trades.append(tsla_trade)

    # MSFT trades
    msft_trade = sample_breakeven_trade()
    trades.append(msft_trade)

    # SPY trade
    spy_trade = sample_live_trade()
    trades.append(spy_trade)

    return trades
