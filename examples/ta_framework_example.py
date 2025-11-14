"""Technical Analysis Framework - Complete Example

This example demonstrates how to use the TA framework to:
1. Analyze a symbol with all 20 technical tools
2. Get actionable trading signals with risk management
3. Track trades in a journal
4. Review performance

No astrology. Just quantifiable, backtestable analysis.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from trading_bot.technical_analysis import (
    TACoordinator,
    TradingJournal,
    EnhancedIndicators,
    MarketStructureAnalyzer,
    RegimeDetector,
    PatternDetector,
    RiskCalculator
)


def generate_sample_data(symbol='BTCUSD', periods=200, timeframe='1h'):
    """Generate sample OHLCV data for testing."""
    np.random.seed(42)

    # Create datetime index
    end_date = datetime.now()
    start_date = end_date - timedelta(hours=periods)
    dates = pd.date_range(start=start_date, end=end_date, freq='1h')[:periods]

    # Generate price data with trend
    base_price = 50000 if symbol == 'BTCUSD' else 150
    trend = np.linspace(0, 0.1, periods)  # 10% uptrend
    noise = np.random.randn(periods) * 0.02  # 2% noise

    close = base_price * (1 + trend + noise)
    high = close * (1 + np.random.rand(periods) * 0.01)
    low = close * (1 - np.random.rand(periods) * 0.01)
    open_price = (high + low) / 2

    volume = np.random.randint(1000000, 5000000, periods)

    df = pd.DataFrame({
        'open': open_price,
        'high': high,
        'low': low,
        'close': close,
        'volume': volume
    }, index=dates)

    return df


def example_1_basic_analysis():
    """Example 1: Basic single-timeframe analysis."""
    print("\n" + "="*80)
    print("EXAMPLE 1: Basic Single-Timeframe Analysis")
    print("="*80)

    # Generate sample data
    df = generate_sample_data('BTCUSD', periods=200, timeframe='1h')

    # Initialize TA Coordinator
    ta = TACoordinator(
        account_size=10000,
        risk_per_trade=1.0,  # 1% per trade
        min_confidence=60.0,
        min_r_multiple=2.0
    )

    # Analyze the symbol
    signal = ta.analyze_simple(
        symbol='BTCUSD',
        df=df
    )

    # Print the signal
    ta.print_signal(signal)


def example_2_multi_timeframe_analysis():
    """Example 2: Multi-timeframe analysis."""
    print("\n" + "="*80)
    print("EXAMPLE 2: Multi-Timeframe Analysis")
    print("="*80)

    # Generate data for multiple timeframes
    df_15m = generate_sample_data('BTCUSD', periods=400, timeframe='15m')
    df_1h = generate_sample_data('BTCUSD', periods=200, timeframe='1h')
    df_4h = generate_sample_data('BTCUSD', periods=100, timeframe='4h')
    df_1d = generate_sample_data('BTCUSD', periods=50, timeframe='1d')

    # Initialize TA Coordinator
    ta = TACoordinator(
        account_size=10000,
        risk_per_trade=1.0,
        min_confidence=65.0,  # Higher confidence for multi-TF
        min_r_multiple=2.5
    )

    # Analyze with multiple timeframes
    signal = ta.analyze(
        symbol='BTCUSD',
        data={
            '15m': df_15m,
            '1h': df_1h,
            '4h': df_4h,
            '1d': df_1d
        },
        primary_timeframe='1h'
    )

    # Print the signal
    ta.print_signal(signal)


def example_3_individual_components():
    """Example 3: Using individual components."""
    print("\n" + "="*80)
    print("EXAMPLE 3: Using Individual Components")
    print("="*80)

    df = generate_sample_data('BTCUSD', periods=200)

    # 1. Enhanced Indicators
    print("\n1. ENHANCED INDICATORS:")
    indicators = EnhancedIndicators()

    ma_result = indicators.calculate_moving_averages(df)
    print(f"   MA Alignment: {ma_result.ma_alignment}")
    print(f"   Price: ${ma_result.price:.2f}")
    print(f"   SMA 20: ${ma_result.sma_20:.2f}")
    print(f"   Golden Cross: {ma_result.golden_cross}")

    rsi_result = indicators.calculate_rsi(df)
    print(f"   RSI: {rsi_result.rsi:.1f}")
    print(f"   Bullish Bias: {rsi_result.bullish_bias}")

    # 2. Market Structure
    print("\n2. MARKET STRUCTURE:")
    structure_analyzer = MarketStructureAnalyzer()
    structure = structure_analyzer.analyze(df)

    print(f"   Trend: {structure.trend}")
    print(f"   Structure: {structure.structure}")
    print(f"   Confidence: {structure.confidence:.1f}%")
    print(f"   Swing Highs: {len(structure.swing_highs)}")
    print(f"   Swing Lows: {len(structure.swing_lows)}")

    # 3. Regime Detection
    print("\n3. REGIME DETECTION:")
    regime_detector = RegimeDetector()
    regime = regime_detector.detect(df)

    print(f"   Regime: {regime.regime}")
    print(f"   Confidence: {regime.confidence:.1f}%")
    print(f"   Recommendation: {regime.recommendation}")

    # 4. Pattern Detection
    print("\n4. PATTERN DETECTION:")
    pattern_detector = PatternDetector()

    consolidation = pattern_detector.detect_consolidation(df)
    print(f"   Consolidating: {consolidation.is_consolidating}")
    if consolidation.is_consolidating:
        print(f"   Pattern: {consolidation.pattern_type}")
        print(f"   Support: ${consolidation.support_level:.2f}")
        print(f"   Resistance: ${consolidation.resistance_level:.2f}")

    # 5. Risk Calculator
    print("\n5. RISK CALCULATOR:")
    risk_calculator = RiskCalculator()

    current_price = float(df['close'].iloc[-1])
    stop_loss = current_price * 0.98  # 2% stop
    take_profit = current_price * 1.04  # 4% target

    rr_result = risk_calculator.calculate_risk_reward(
        entry_price=current_price,
        stop_loss=stop_loss,
        take_profit=take_profit,
        direction='long'
    )

    print(f"   Entry: ${rr_result.entry_price:.2f}")
    print(f"   Stop: ${rr_result.stop_loss:.2f}")
    print(f"   Target: ${rr_result.take_profit:.2f}")
    print(f"   R-Multiple: {rr_result.r_multiple:.2f}R")
    print(f"   Acceptable: {rr_result.acceptable}")


def example_4_trading_journal():
    """Example 4: Trading journal and performance tracking."""
    print("\n" + "="*80)
    print("EXAMPLE 4: Trading Journal & Performance Tracking")
    print("="*80)

    # Initialize journal
    journal = TradingJournal(
        journal_path='./test_trading_journal.json',
        equity_start=10000.0
    )

    # Simulate some trades
    print("\nSimulating 10 trades...")

    for i in range(10):
        trade_id = f"TRADE_{i+1:03d}"
        symbol = 'BTCUSD'
        direction = 'long' if i % 2 == 0 else 'short'
        entry_price = 50000 + (i * 100)
        stop_loss = entry_price - 500 if direction == 'long' else entry_price + 500
        take_profit = entry_price + 1000 if direction == 'long' else entry_price - 1000

        # Log entry
        journal.log_trade_entry(
            trade_id=trade_id,
            symbol=symbol,
            direction=direction,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            position_size=0.1,
            setup_type='breakout' if i % 3 == 0 else 'pullback',
            market_regime='trending' if i < 5 else 'ranging',
            trend_direction='uptrend',
            timeframe='1h',
            notes=f"Test trade {i+1}"
        )

        # Simulate exit (70% win rate)
        if i < 7:  # Winning trade
            exit_price = take_profit
        else:  # Losing trade
            exit_price = stop_loss

        journal.log_trade_exit(
            trade_id=trade_id,
            exit_price=exit_price,
            followed_rules=True,
            notes=f"Trade completed"
        )

        print(f"  {trade_id}: {direction.upper()} @ {entry_price:.2f} -> {exit_price:.2f}")

    # Generate performance report
    print("\n" + "-"*80)
    print(journal.generate_review_report())


def example_5_complete_workflow():
    """Example 5: Complete trading workflow."""
    print("\n" + "="*80)
    print("EXAMPLE 5: Complete Trading Workflow")
    print("="*80)

    # 1. Initialize components
    ta = TACoordinator(
        account_size=10000,
        risk_per_trade=1.0,
        min_confidence=60.0,
        min_r_multiple=2.0
    )

    journal = TradingJournal(
        journal_path='./workflow_journal.json',
        equity_start=10000.0
    )

    # 2. Get market data (simulated)
    df = generate_sample_data('BTCUSD', periods=200)

    # 3. Analyze and get signal
    print("\n1. Analyzing market conditions...")
    signal = ta.analyze_simple(symbol='BTCUSD', df=df)

    # 4. Decide whether to trade
    print("\n2. Evaluating signal...")
    if signal.signal == 'LONG' and signal.quality_score > 70:
        print(f"   ✓ TAKING TRADE: {signal.signal}")
        print(f"   Confidence: {signal.confidence:.1f}%")
        print(f"   Quality Score: {signal.quality_score:.0f}/100")
        print(f"   R-Multiple: {signal.r_multiple:.2f}R")

        # 5. Log trade entry
        trade_id = f"TRADE_{int(signal.timestamp.timestamp())}"
        journal.log_trade_entry(
            trade_id=trade_id,
            symbol=signal.symbol,
            direction=signal.signal.lower(),
            entry_price=signal.entry_price,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
            position_size=signal.position_size_shares,
            setup_type=signal.pattern or 'systematic',
            market_regime=signal.regime,
            trend_direction=signal.trend,
            timeframe='1h',
            indicators={
                'rsi': signal.rsi,
                'macd_signal': signal.macd_signal
            },
            notes=signal.reasoning
        )

        print(f"\n3. Trade logged with ID: {trade_id}")
        print(f"   Entry: ${signal.entry_price:.2f}")
        print(f"   Stop: ${signal.stop_loss:.2f}")
        print(f"   Target: ${signal.take_profit:.2f}")
        print(f"   Position Size: {signal.position_size_shares:.2f} shares (${signal.position_size_usd:.2f})")

        # 6. Simulate trade execution (in real trading, this would be actual fill)
        # For demo, assume we hit target
        exit_price = signal.take_profit

        # 7. Log trade exit
        journal.log_trade_exit(
            trade_id=trade_id,
            exit_price=exit_price,
            followed_rules=True,
            notes="Target hit"
        )

        print(f"\n4. Trade closed at ${exit_price:.2f}")

        # 8. Review performance
        metrics = journal.calculate_performance()
        print(f"\n5. Performance Update:")
        print(f"   Total P&L: ${metrics.total_pnl:.2f}")
        print(f"   Win Rate: {metrics.win_rate:.1f}%")
        print(f"   Avg R: {metrics.avg_r_multiple:.2f}R")

    else:
        print(f"   ✗ SKIPPING TRADE: {signal.signal}")
        print(f"   Reason: Low confidence ({signal.confidence:.1f}%) or quality ({signal.quality_score or 0:.0f}/100)")
        if signal.warnings:
            for warning in signal.warnings:
                print(f"   ⚠ {warning}")


def main():
    """Run all examples."""
    print("\n" + "="*80)
    print("TECHNICAL ANALYSIS FRAMEWORK - EXAMPLES")
    print("="*80)
    print("\nDemonstrating the 20-tool TA framework for informed trading")
    print("No astrology. Just quantifiable, backtestable analysis.")

    # Run examples
    example_1_basic_analysis()
    example_2_multi_timeframe_analysis()
    example_3_individual_components()
    example_4_trading_journal()
    example_5_complete_workflow()

    print("\n" + "="*80)
    print("All examples completed!")
    print("="*80 + "\n")


if __name__ == '__main__':
    main()
