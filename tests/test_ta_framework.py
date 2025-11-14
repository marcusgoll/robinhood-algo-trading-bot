"""Basic tests for Technical Analysis Framework.

Tests that:
1. All modules import correctly
2. Basic functionality works
3. Signal generation doesn't crash
"""

import sys
from pathlib import Path
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from trading_bot.technical_analysis import (
    TACoordinator,
    TradingJournal,
    EnhancedIndicators,
    MarketStructureAnalyzer,
    MultiTimeframeAnalyzer,
    RegimeDetector,
    PatternDetector,
    VolumeAnalyzer,
    RiskCalculator
)


@pytest.fixture
def sample_df():
    """Generate sample OHLCV data for testing."""
    np.random.seed(42)

    periods = 200
    end_date = datetime.now()
    start_date = end_date - timedelta(hours=periods)
    dates = pd.date_range(start=start_date, end=end_date, freq='1h')[:periods]

    base_price = 50000
    trend = np.linspace(0, 0.1, periods)
    noise = np.random.randn(periods) * 0.02

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


class TestEnhancedIndicators:
    """Test enhanced indicators module."""

    def test_imports(self):
        """Test that all imports work."""
        assert EnhancedIndicators is not None

    def test_moving_averages(self, sample_df):
        """Test moving average calculation."""
        indicators = EnhancedIndicators()
        result = indicators.calculate_moving_averages(sample_df)

        assert result.sma_20 > 0
        assert result.sma_50 > 0
        assert result.sma_200 > 0
        assert result.ma_alignment in ['bullish', 'bearish', 'mixed']

    def test_rsi(self, sample_df):
        """Test RSI calculation."""
        indicators = EnhancedIndicators()
        result = indicators.calculate_rsi(sample_df)

        assert 0 <= result.rsi <= 100
        assert isinstance(result.bullish_bias, bool)

    def test_macd(self, sample_df):
        """Test MACD calculation."""
        indicators = EnhancedIndicators()
        result = indicators.calculate_macd(sample_df)

        assert result.macd_line is not None
        assert result.signal_line is not None
        assert isinstance(result.bullish, bool)

    def test_atr(self, sample_df):
        """Test ATR calculation."""
        indicators = EnhancedIndicators()
        result = indicators.calculate_atr(sample_df)

        assert result.atr > 0
        assert result.volatility_regime in ['low', 'normal', 'high', 'extreme']


class TestMarketStructure:
    """Test market structure analysis."""

    def test_market_structure_analyzer(self, sample_df):
        """Test market structure detection."""
        analyzer = MarketStructureAnalyzer()
        result = analyzer.analyze(sample_df)

        assert result.trend in ['uptrend', 'downtrend', 'sideways']
        assert result.structure in ['HH/HL', 'LH/LL', 'choppy']
        assert 0 <= result.confidence <= 100

    def test_multi_timeframe_analyzer(self, sample_df):
        """Test multi-timeframe analysis."""
        analyzer = MultiTimeframeAnalyzer()
        result = analyzer.analyze({
            '1h': sample_df,
            '4h': sample_df
        })

        assert result['overall_trend'] in ['bullish', 'bearish', 'mixed']
        assert 0 <= result['confidence'] <= 100


class TestRegimeDetector:
    """Test regime detection."""

    def test_regime_detection(self, sample_df):
        """Test regime detector."""
        detector = RegimeDetector()
        result = detector.detect(sample_df)

        assert result.regime in ['breakout', 'mean_reversion', 'transitional']
        assert 0 <= result.confidence <= 100


class TestPatternDetector:
    """Test pattern detection."""

    def test_consolidation_detection(self, sample_df):
        """Test consolidation pattern detection."""
        detector = PatternDetector()
        result = detector.detect_consolidation(sample_df)

        assert isinstance(result.is_consolidating, bool)
        assert result.pattern_type in ['range', 'triangle', 'flag', 'none']

    def test_gap_detection(self, sample_df):
        """Test gap detection."""
        detector = PatternDetector()
        result = detector.detect_gaps(sample_df)

        assert isinstance(result.gaps_detected, list)
        assert 0 <= result.gap_fill_probability <= 100


class TestRiskCalculator:
    """Test risk calculator."""

    def test_risk_reward_calculation(self):
        """Test risk-reward calculation."""
        calc = RiskCalculator()
        result = calc.calculate_risk_reward(
            entry_price=50000,
            stop_loss=49000,
            take_profit=52000,
            direction='long'
        )

        assert result.r_multiple == 2.0  # (2000 / 1000)
        assert result.risk_amount == 1000
        assert result.reward_amount == 2000

    def test_position_sizing(self):
        """Test position size calculation."""
        calc = RiskCalculator()
        result = calc.calculate_position_size(
            account_size=10000,
            entry_price=50000,
            stop_loss=49000,
            direction='long'
        )

        assert result.position_size_shares > 0
        assert result.position_size_usd > 0
        assert result.risk_per_trade_usd == 100  # 1% of 10000


class TestTACoordinator:
    """Test TA Coordinator."""

    def test_ta_coordinator_init(self):
        """Test TA coordinator initialization."""
        ta = TACoordinator(account_size=10000)

        assert ta.account_size == 10000
        assert ta.indicators is not None
        assert ta.risk_calculator is not None

    def test_signal_generation(self, sample_df):
        """Test signal generation."""
        ta = TACoordinator(account_size=10000)

        signal = ta.analyze_simple(
            symbol='BTCUSD',
            df=sample_df
        )

        assert signal.symbol == 'BTCUSD'
        assert signal.signal in ['LONG', 'SHORT', 'HOLD', 'SKIP']
        assert 0 <= signal.confidence <= 100
        assert signal.entry_price > 0


class TestTradingJournal:
    """Test trading journal."""

    def test_journal_init(self, tmp_path):
        """Test journal initialization."""
        journal_path = tmp_path / "test_journal.json"
        journal = TradingJournal(
            journal_path=str(journal_path),
            equity_start=10000
        )

        assert journal.equity_start == 10000
        assert len(journal.trades) == 0

    def test_trade_logging(self, tmp_path):
        """Test trade entry and exit logging."""
        journal_path = tmp_path / "test_journal.json"
        journal = TradingJournal(
            journal_path=str(journal_path),
            equity_start=10000
        )

        # Log entry
        journal.log_trade_entry(
            trade_id='TEST_001',
            symbol='BTCUSD',
            direction='long',
            entry_price=50000,
            stop_loss=49000,
            take_profit=52000,
            position_size=0.1,
            setup_type='breakout'
        )

        assert len(journal.trades) == 1

        # Log exit
        journal.log_trade_exit(
            trade_id='TEST_001',
            exit_price=52000,
            followed_rules=True
        )

        trade = journal.trades[0]
        assert trade.status == 'closed_win'
        assert trade.pnl_usd == 200  # (52000 - 50000) * 0.1

    def test_performance_metrics(self, tmp_path):
        """Test performance metrics calculation."""
        journal_path = tmp_path / "test_journal.json"
        journal = TradingJournal(
            journal_path=str(journal_path),
            equity_start=10000
        )

        # Log a winning trade
        journal.log_trade_entry(
            trade_id='TEST_001',
            symbol='BTCUSD',
            direction='long',
            entry_price=50000,
            stop_loss=49000,
            take_profit=52000,
            position_size=0.1
        )
        journal.log_trade_exit(
            trade_id='TEST_001',
            exit_price=52000
        )

        # Calculate metrics
        metrics = journal.calculate_performance()

        assert metrics.total_trades == 1
        assert metrics.winning_trades == 1
        assert metrics.win_rate == 100.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
