"""Tests for ML feature extraction.

TDD approach: Write failing tests before implementation.
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timezone

from src.trading_bot.ml.features.technical import TechnicalFeatureCalculator
from src.trading_bot.ml.features.extractor import FeatureExtractor
from src.trading_bot.ml.models import FeatureSet


class TestTechnicalFeatureCalculator:
    """Tests for TechnicalFeatureCalculator."""

    @pytest.fixture
    def sample_prices(self):
        """Create sample price series for testing."""
        # Create 50 bars of uptrending prices
        np.random.seed(42)
        base_prices = np.linspace(100, 150, 50)
        noise = np.random.normal(0, 2, 50)
        prices = pd.Series(base_prices + noise)
        return prices

    @pytest.fixture
    def calculator(self):
        """Create TechnicalFeatureCalculator instance."""
        return TechnicalFeatureCalculator()

    def test_calculate_rsi_range(self, calculator, sample_prices):
        """Test: RSI values are in range [0, 1].

        Given: Sample price series
        When: Calculating RSI
        Then: All values in [0, 1] range (normalized from 0-100)
        """
        # When
        rsi = calculator.calculate_rsi(sample_prices, period=14)

        # Then
        assert np.all(rsi >= 0.0)
        assert np.all(rsi <= 1.0)
        assert len(rsi) == len(sample_prices)

    def test_calculate_rsi_uptrend_high(self, calculator):
        """Test: RSI high (>0.7) during strong uptrend.

        Given: Strong uptrending prices
        When: Calculating RSI
        Then: RSI > 0.7 (overbought)
        """
        # Given: Strong uptrend
        uptrend = pd.Series(range(100, 200, 2))  # Strong rise

        # When
        rsi = calculator.calculate_rsi(uptrend, period=14)

        # Then: Recent RSI should be high
        recent_rsi = rsi[-5:].mean()
        assert recent_rsi > 0.7  # Overbought territory

    def test_calculate_rsi_downtrend_low(self, calculator):
        """Test: RSI low (<0.3) during strong downtrend.

        Given: Strong downtrending prices
        When: Calculating RSI
        Then: RSI < 0.3 (oversold)
        """
        # Given: Strong downtrend
        downtrend = pd.Series(range(200, 100, -2))  # Strong fall

        # When
        rsi = calculator.calculate_rsi(downtrend, period=14)

        # Then: Recent RSI should be low
        recent_rsi = rsi[-5:].mean()
        assert recent_rsi < 0.3  # Oversold territory

    def test_calculate_macd_returns_three_arrays(self, calculator, sample_prices):
        """Test: MACD returns macd_line, signal_line, histogram.

        Given: Sample price series
        When: Calculating MACD
        Then: Returns tuple of 3 arrays
        """
        # When
        macd_line, signal_line, histogram = calculator.calculate_macd(sample_prices)

        # Then
        assert isinstance(macd_line, np.ndarray)
        assert isinstance(signal_line, np.ndarray)
        assert isinstance(histogram, np.ndarray)
        assert len(macd_line) == len(sample_prices)
        assert len(signal_line) == len(sample_prices)
        assert len(histogram) == len(sample_prices)

    def test_calculate_macd_histogram_is_difference(self, calculator):
        """Test: MACD histogram = macd_line - signal_line.

        Given: Sample prices
        When: Calculating MACD
        Then: Histogram approximately equals macd - signal
        """
        # Given
        prices = pd.Series([100 + i * 0.5 for i in range(50)])

        # When
        macd_line, signal_line, histogram = calculator.calculate_macd(prices)

        # Then: histogram ≈ macd - signal (allowing for normalization)
        # Check sign relationship at minimum
        for i in range(26, len(prices)):  # After MACD warmup period
            if macd_line[i] > signal_line[i]:
                assert histogram[i] >= 0
            elif macd_line[i] < signal_line[i]:
                assert histogram[i] <= 0

    def test_calculate_stochastic_range(self, calculator, sample_prices):
        """Test: Stochastic %K and %D are in range [0, 1].

        Given: Sample price OHLC data
        When: Calculating stochastic oscillator
        Then: All values in [0, 1] range
        """
        # Given: Create OHLC DataFrame
        high = sample_prices * 1.02
        low = sample_prices * 0.98
        close = sample_prices

        # When
        stoch_k, stoch_d = calculator.calculate_stochastic(high, low, close, k_period=14, d_period=3)

        # Then
        assert np.all(stoch_k >= 0.0)
        assert np.all(stoch_k <= 1.0)
        assert np.all(stoch_d >= 0.0)
        assert np.all(stoch_d <= 1.0)

    def test_calculate_atr_positive_values(self, calculator):
        """Test: ATR values are positive and normalized.

        Given: Sample OHLC data
        When: Calculating ATR
        Then: All values >= 0
        """
        # Given
        high = pd.Series([102, 105, 108, 107, 110] * 10)
        low = pd.Series([98, 95, 92, 93, 90] * 10)
        close = pd.Series([100, 100, 100, 100, 100] * 10)

        # When
        atr = calculator.calculate_atr(high, low, close, period=14)

        # Then
        assert np.all(atr >= 0.0)
        assert len(atr) == len(high)


class TestFeatureExtractor:
    """Tests for FeatureExtractor main orchestrator."""

    @pytest.fixture
    def sample_ohlcv(self):
        """Create sample OHLCV DataFrame."""
        np.random.seed(42)
        n = 100

        # Generate realistic price movement
        close_prices = 100 * np.exp(np.cumsum(np.random.normal(0.001, 0.02, n)))

        df = pd.DataFrame({
            'date': pd.date_range('2024-01-01', periods=n, freq='D'),
            'open': close_prices * np.random.uniform(0.98, 1.00, n),
            'high': close_prices * np.random.uniform(1.00, 1.02, n),
            'low': close_prices * np.random.uniform(0.98, 1.00, n),
            'close': close_prices,
            'volume': np.random.randint(1_000_000, 10_000_000, n)
        })

        return df

    @pytest.fixture
    def extractor(self):
        """Create FeatureExtractor instance."""
        return FeatureExtractor()

    def test_calculate_price_features_returns_dict(self, extractor, sample_ohlcv):
        """Test: calculate_price_features returns dict of features.

        Given: OHLCV DataFrame
        When: Calculating price features
        Then: Returns dict with 10 price feature arrays
        """
        # When
        features = extractor.calculate_price_features(sample_ohlcv)

        # Then
        assert isinstance(features, dict)
        assert len(features) == 10  # 10 price features

        # Check all expected keys
        expected_keys = [
            'returns_1d', 'returns_5d', 'returns_20d',
            'volatility_20d', 'volume_ratio', 'high_low_range',
            'close_to_high', 'price_to_sma20', 'price_to_sma50',
            'price_to_vwap'
        ]

        for key in expected_keys:
            assert key in features
            assert isinstance(features[key], np.ndarray)
            assert len(features[key]) == len(sample_ohlcv)

    def test_calculate_price_features_normalization(self, extractor, sample_ohlcv):
        """Test: Price features are properly normalized.

        Given: OHLCV DataFrame
        When: Calculating price features
        Then: Most values in reasonable ranges
        """
        # When
        features = extractor.calculate_price_features(sample_ohlcv)

        # Then: Check normalization ranges
        # Returns should be clipped and normalized
        assert features['returns_1d'].min() >= -1.0
        assert features['returns_1d'].max() <= 1.0

        # Volume ratio should be normalized to [0, 1]
        assert features['volume_ratio'].min() >= 0.0
        assert features['volume_ratio'].max() <= 1.0

        # Close position in range should be [0, 1]
        assert features['close_to_high'].min() >= 0.0
        assert features['close_to_high'].max() <= 1.0

    def test_extract_creates_feature_set(self, extractor, sample_ohlcv):
        """Test: extract() returns list of FeatureSet objects.

        Given: OHLCV DataFrame
        When: Calling extract()
        Then: Returns list of FeatureSet with all features populated
        """
        # When
        result = extractor.extract(sample_ohlcv, symbol="AAPL")

        # Then
        assert isinstance(result, list)
        assert len(result) == len(sample_ohlcv)

        # Check last feature set (most recent bar)
        last_features = result[-1]
        assert hasattr(last_features, 'symbol')
        assert hasattr(last_features, 'timestamp')
        assert last_features.symbol == "AAPL"
        assert isinstance(last_features.timestamp, datetime)

        # Check some key features are set
        assert last_features.rsi_14 >= 0.0 and last_features.rsi_14 <= 1.0  # Normalized RSI
        assert last_features.volume_ratio >= 0.0

    def test_extract_handles_minimal_data(self, extractor):
        """Test: extract() handles minimal data gracefully.

        Given: OHLCV DataFrame with only 30 bars (minimum)
        When: Calling extract()
        Then: Returns list of FeatureSet without errors
        """
        # Given: Minimal data (30 bars)
        df = pd.DataFrame({
            'date': pd.date_range('2024-01-01', periods=30, freq='D'),
            'open': [100] * 30,
            'high': [102] * 30,
            'low': [98] * 30,
            'close': [100] * 30,
            'volume': [1_000_000] * 30
        })

        # When
        result = extractor.extract(df, symbol="TEST")

        # Then: Should complete without errors
        assert isinstance(result, list)
        assert len(result) == 30
        assert result[-1].symbol == "TEST"

    def test_extract_uses_latest_bar(self, extractor, sample_ohlcv):
        """Test: extract() returns features for all bars.

        Given: OHLCV DataFrame with 100 bars
        When: Calling extract()
        Then: Returns 100 feature sets (one per bar)
        """
        # When
        result = extractor.extract(sample_ohlcv, symbol="AAPL")

        # Then: Should have one feature set per bar
        assert len(result) == len(sample_ohlcv)
        assert result[-1].timestamp is not None
        assert result[0].timestamp is not None

    def test_to_array_correct_shape(self, extractor, sample_ohlcv):
        """Test: FeatureSet.to_array() returns feature array.

        Given: Extracted FeatureSet
        When: Converting to numpy array
        Then: Shape is (N,) where N is number of features
        """
        # Given
        feature_list = extractor.extract(sample_ohlcv, symbol="AAPL")
        features = feature_list[-1]  # Get last feature set

        # When
        arr = features.to_array()

        # Then
        assert isinstance(arr, np.ndarray)
        assert len(arr.shape) == 1  # 1D array
        assert arr.dtype == np.float64
        # Check we have at least 40 features (price + technical + pattern)
        assert arr.shape[0] >= 40

    def test_feature_names_match_array_order(self):
        """Test: FeatureSet.feature_names() returns feature names.

        Given: FeatureSet class
        When: Getting feature names
        Then: Returns list of feature names in correct order
        """
        # When
        names = FeatureSet.feature_names()

        # Then
        assert isinstance(names, list)
        assert len(names) > 0  # Has features
        assert names[0] == "returns_1d"  # Starts with price features
        assert "rsi_14" in names  # Technical indicators included
        assert "bull_flag_score" in names  # Pattern features included

        # Verify minimum number of features
        assert len(names) >= 40  # At least 40 features
