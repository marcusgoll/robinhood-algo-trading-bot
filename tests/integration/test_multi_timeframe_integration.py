#!/usr/bin/env python3
"""Integration tests for multi-timeframe ML system.

Tests the complete pipeline:
1. Multi-timeframe data fetching
2. Feature extraction and alignment
3. Neural network forward pass
4. Walk-forward validation
5. End-to-end integration

Run with:
    pytest tests/test_multi_timeframe_integration.py -v
    or
    python tests/test_multi_timeframe_integration.py
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import torch

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from trading_bot.ml.features.multi_timeframe import (
    MultiTimeframeExtractor,
    MultiTimeframeFeatureSet,
)
from trading_bot.ml.neural_models import HierarchicalTimeframeNet
from trading_bot.ml.validation import WalkForwardValidator, WalkForwardConfig
from trading_bot.ml.training import EarlyStopping, ModelCheckpoint, EnsembleAverager


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def sample_ohlcv_data():
    """Generate sample OHLCV data for testing."""
    dates = pd.date_range(start="2023-01-01", periods=500, freq="1H")

    # Generate realistic price data
    np.random.seed(42)
    price = 100.0
    prices = []

    for _ in range(len(dates)):
        price += np.random.normal(0, 1)
        prices.append(price)

    df = pd.DataFrame({
        "date": dates,
        "open": prices,
        "high": [p + abs(np.random.normal(0, 0.5)) for p in prices],
        "low": [p - abs(np.random.normal(0, 0.5)) for p in prices],
        "close": [p + np.random.normal(0, 0.3) for p in prices],
        "volume": [np.random.randint(1000000, 10000000) for _ in prices],
    })

    return df


@pytest.fixture
def multi_timeframe_data(sample_ohlcv_data):
    """Generate data for multiple timeframes."""
    # Resample to different timeframes
    df = sample_ohlcv_data.set_index("date")

    data_by_tf = {
        "5min": df.resample("5T").agg({
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum"
        }).dropna().reset_index(),
        "15min": df.resample("15T").agg({
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum"
        }).dropna().reset_index(),
        "1hr": df.resample("1H").agg({
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum"
        }).dropna().reset_index(),
        "4hr": df.resample("4H").agg({
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum"
        }).dropna().reset_index(),
        "1day": df.resample("1D").agg({
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum"
        }).dropna().reset_index(),
    }

    return data_by_tf


# ============================================================================
# Unit Tests
# ============================================================================

class TestMultiTimeframeExtractor:
    """Test MultiTimeframeExtractor functionality."""

    def test_initialization(self):
        """Test extractor initialization."""
        extractor = MultiTimeframeExtractor()

        assert len(extractor.timeframes) == 6
        assert extractor.timeframes == ["1min", "5min", "15min", "1hr", "4hr", "1day"]
        assert extractor.enable_cross_tf_features is True
        assert len(extractor.extractors) == 6

    def test_custom_timeframes(self):
        """Test initialization with custom timeframes."""
        custom_tfs = ["5min", "1hr", "1day"]
        extractor = MultiTimeframeExtractor(timeframes=custom_tfs)

        assert len(extractor.timeframes) == 3
        assert extractor.timeframes == custom_tfs

    def test_extract_aligned_features(self, multi_timeframe_data):
        """Test feature extraction across timeframes."""
        extractor = MultiTimeframeExtractor(
            timeframes=["5min", "1hr", "1day"],
            enable_cross_tf_features=True
        )

        target_timestamp = multi_timeframe_data["1day"]["date"].iloc[-10]

        features = extractor.extract_aligned_features(
            data_by_timeframe=multi_timeframe_data,
            target_timestamp=target_timestamp,
            symbol="TEST"
        )

        # Verify structure
        assert isinstance(features, MultiTimeframeFeatureSet)
        assert features.symbol == "TEST"
        assert features.timestamp == target_timestamp

        # Verify timeframe features
        assert len(features.timeframe_features) == 3
        assert "5min" in features.timeframe_features
        assert "1hr" in features.timeframe_features
        assert "1day" in features.timeframe_features

        # Verify cross-TF features
        assert len(features.cross_timeframe_features) == 8
        assert "trend_alignment" in features.cross_timeframe_features
        assert "rsi_divergence" in features.cross_timeframe_features
        assert "momentum_cascade" in features.cross_timeframe_features

        # Verify feature count
        # 3 timeframes * 55 features + 8 cross-TF = 173 total
        assert features.num_features == 173

    def test_to_array_conversion(self, multi_timeframe_data):
        """Test conversion to numpy array."""
        extractor = MultiTimeframeExtractor(
            timeframes=["5min", "1hr"],
            enable_cross_tf_features=True
        )

        target_timestamp = multi_timeframe_data["1day"]["date"].iloc[-5]

        features = extractor.extract_aligned_features(
            data_by_timeframe=multi_timeframe_data,
            target_timestamp=target_timestamp,
            symbol="TEST"
        )

        # Convert to array
        arr = features.to_array()

        # Verify shape: 2 TFs * 55 features + 8 cross-TF = 118
        assert arr.shape == (118,)
        assert isinstance(arr, np.ndarray)
        assert not np.any(np.isnan(arr))


class TestHierarchicalTimeframeNet:
    """Test HierarchicalTimeframeNet neural network."""

    def test_initialization(self):
        """Test model initialization."""
        model = HierarchicalTimeframeNet(
            num_timeframes=3,
            features_per_tf=55,
            cross_tf_features=8,
            hidden_dim=64,
            num_heads=2
        )

        # Verify architecture
        assert model.num_timeframes == 3
        assert model.features_per_tf == 55
        assert model.cross_tf_features == 8
        assert model.hidden_dim == 64
        assert model.total_features == (3 * 55) + 8  # 173

        # Verify components exist
        assert len(model.encoders) == 3
        assert model.attention is not None
        assert model.fusion is not None
        assert model.classifier is not None

    def test_forward_pass(self):
        """Test forward pass through network."""
        model = HierarchicalTimeframeNet(
            num_timeframes=3,
            features_per_tf=55,
            cross_tf_features=8,
            hidden_dim=64
        )

        # Create batch of inputs: batch_size=4, features=173
        batch_size = 4
        total_features = (3 * 55) + 8
        x = torch.randn(batch_size, total_features)

        # Forward pass
        logits = model(x)

        # Verify output shape: (batch_size, num_classes=3)
        assert logits.shape == (batch_size, 3)
        assert not torch.any(torch.isnan(logits))

    def test_predict_method(self):
        """Test predict method with confidence scores."""
        model = HierarchicalTimeframeNet(
            num_timeframes=2,
            features_per_tf=55,
            cross_tf_features=8,
            hidden_dim=32
        )

        # Create input
        x = torch.randn(10, (2 * 55) + 8)

        # Predict
        actions, confidences = model.predict(x)

        # Verify outputs
        assert actions.shape == (10,)
        assert confidences.shape == (10,)
        assert torch.all((actions >= 0) & (actions <= 2))  # Buy/Hold/Sell
        assert torch.all((confidences >= 0) & (confidences <= 1))

    def test_attention_weights(self):
        """Test attention weight extraction."""
        model = HierarchicalTimeframeNet(
            num_timeframes=3,
            features_per_tf=55,
            num_heads=2
        )

        x = torch.randn(1, (3 * 55) + 8)

        # Get attention weights
        attn_weights = model.get_attention_weights(x)

        # Verify shape: (batch_size, num_heads, num_timeframes, num_timeframes)
        assert attn_weights.shape == (1, 2, 3, 3)

        # Verify attention sums to 1 along last dimension
        assert torch.allclose(
            attn_weights.sum(dim=-1),
            torch.ones(1, 2, 3),
            atol=1e-5
        )


class TestWalkForwardValidator:
    """Test walk-forward validation framework."""

    def test_initialization(self):
        """Test validator initialization."""
        config = WalkForwardConfig(
            train_days=100,
            test_days=30,
            step_days=10,
            batch_size=16,
            epochs=10
        )

        validator = WalkForwardValidator(config)

        assert validator.config.train_days == 100
        assert validator.config.test_days == 30
        assert validator.config.step_days == 10

    def test_generate_splits(self, sample_ohlcv_data):
        """Test train/test split generation."""
        config = WalkForwardConfig(
            train_days=100,
            test_days=30,
            step_days=20,
            min_train_days=50
        )

        validator = WalkForwardValidator(config)

        # Generate splits
        splits = validator.generate_splits(sample_ohlcv_data, date_column="date")

        # Verify splits were generated
        assert len(splits) > 0

        # Verify each split structure
        for train_df, test_df in splits:
            assert isinstance(train_df, pd.DataFrame)
            assert isinstance(test_df, pd.DataFrame)
            assert len(train_df) > 0
            assert len(test_df) > 0

            # Verify temporal ordering
            assert train_df.index[-1] < test_df.index[0]


class TestRegularizationUtilities:
    """Test regularization and training utilities."""

    def test_early_stopping(self):
        """Test early stopping callback."""
        early_stop = EarlyStopping(
            patience=3,
            metric="loss",
            mode="min",
            verbose=False
        )

        # Simulate improving then plateauing
        metrics_sequence = [
            {"loss": 1.0},
            {"loss": 0.8},
            {"loss": 0.7},
            {"loss": 0.71},  # Plateau starts
            {"loss": 0.72},
            {"loss": 0.73},
        ]

        for epoch, metrics in enumerate(metrics_sequence):
            early_stop.on_epoch_end(epoch, metrics)

        # Should stop after 3 epochs of no improvement
        assert early_stop.should_stop is True
        assert early_stop.best_value == 0.7

    def test_ensemble_averager(self):
        """Test ensemble averaging."""
        averager = EnsembleAverager(num_models=3, voting="soft")

        # Create simple models
        for _ in range(3):
            model = torch.nn.Linear(10, 3)
            averager.add_model(model)

        assert averager.is_complete() is True

        # Test prediction
        x = torch.randn(5, 10)
        predictions = averager.predict(x)

        assert predictions.shape == (5,)
        assert torch.all((predictions >= 0) & (predictions <= 2))


# ============================================================================
# Integration Tests
# ============================================================================

class TestEndToEndIntegration:
    """Test complete end-to-end pipeline."""

    def test_feature_extraction_to_model_prediction(self, multi_timeframe_data):
        """Test features → model → predictions pipeline."""
        # Step 1: Extract features
        extractor = MultiTimeframeExtractor(
            timeframes=["5min", "1hr", "1day"],
            enable_cross_tf_features=True
        )

        target_timestamp = multi_timeframe_data["1day"]["date"].iloc[-5]

        features = extractor.extract_aligned_features(
            data_by_timeframe=multi_timeframe_data,
            target_timestamp=target_timestamp,
            symbol="TEST"
        )

        # Step 2: Convert to tensor
        feature_array = features.to_array()
        x = torch.FloatTensor(feature_array).unsqueeze(0)  # Add batch dim

        # Step 3: Initialize model
        model = HierarchicalTimeframeNet(
            num_timeframes=3,
            features_per_tf=55,
            cross_tf_features=8,
            hidden_dim=64
        )

        # Step 4: Make prediction
        actions, confidences = model.predict(x)

        # Verify prediction
        assert actions.shape == (1,)
        assert actions[0] in [0, 1, 2]  # Buy, Hold, Sell
        assert 0.0 <= confidences[0] <= 1.0

    def test_batch_processing(self, multi_timeframe_data):
        """Test processing multiple timestamps in batch."""
        extractor = MultiTimeframeExtractor(
            timeframes=["5min", "1hr"],
            enable_cross_tf_features=True
        )

        # Extract features for last 5 timestamps
        timestamps = multi_timeframe_data["1day"]["date"].iloc[-5:]

        feature_arrays = []
        for ts in timestamps:
            features = extractor.extract_aligned_features(
                data_by_timeframe=multi_timeframe_data,
                target_timestamp=ts,
                symbol="TEST"
            )
            feature_arrays.append(features.to_array())

        # Stack into batch
        batch = torch.FloatTensor(np.stack(feature_arrays))

        # Model prediction
        model = HierarchicalTimeframeNet(
            num_timeframes=2,
            features_per_tf=55,
            cross_tf_features=8
        )

        actions, confidences = model.predict(batch)

        # Verify batch predictions
        assert actions.shape == (5,)
        assert confidences.shape == (5,)


# ============================================================================
# Performance Tests
# ============================================================================

class TestPerformance:
    """Test computational performance."""

    def test_model_forward_speed(self):
        """Test forward pass speed."""
        import time

        model = HierarchicalTimeframeNet(
            num_timeframes=6,
            features_per_tf=55,
            hidden_dim=128
        )

        # Generate batch
        batch_size = 32
        x = torch.randn(batch_size, 338)  # 6 TFs * 55 + 8 = 338

        # Warmup
        _ = model(x)

        # Time forward passes
        num_iterations = 100
        start_time = time.time()

        for _ in range(num_iterations):
            _ = model(x)

        elapsed = time.time() - start_time
        avg_time = elapsed / num_iterations

        # Should be fast (<100ms per batch)
        assert avg_time < 0.1, f"Forward pass too slow: {avg_time:.3f}s"

        print(f"\nForward pass time: {avg_time*1000:.2f}ms per batch")

    def test_feature_extraction_speed(self, multi_timeframe_data):
        """Test feature extraction speed."""
        import time

        extractor = MultiTimeframeExtractor(
            timeframes=["5min", "1hr", "1day"]
        )

        target_timestamp = multi_timeframe_data["1day"]["date"].iloc[-5]

        # Warmup
        _ = extractor.extract_aligned_features(
            data_by_timeframe=multi_timeframe_data,
            target_timestamp=target_timestamp,
            symbol="TEST"
        )

        # Time extraction
        num_iterations = 50
        start_time = time.time()

        for _ in range(num_iterations):
            _ = extractor.extract_aligned_features(
                data_by_timeframe=multi_timeframe_data,
                target_timestamp=target_timestamp,
                symbol="TEST"
            )

        elapsed = time.time() - start_time
        avg_time = elapsed / num_iterations

        # Should be reasonably fast (<500ms)
        assert avg_time < 0.5, f"Feature extraction too slow: {avg_time:.3f}s"

        print(f"Feature extraction time: {avg_time*1000:.2f}ms")


# ============================================================================
# Main (for direct execution)
# ============================================================================

if __name__ == "__main__":
    # Run with pytest if available, otherwise run basic tests
    try:
        import pytest
        sys.exit(pytest.main([__file__, "-v", "--tb=short"]))
    except ImportError:
        print("pytest not found, running basic tests...")

        # Create fixtures manually
        from datetime import datetime, timedelta

        # Generate sample data
        dates = pd.date_range(start="2023-01-01", periods=500, freq="1H")
        np.random.seed(42)
        price = 100.0
        prices = [price + np.random.normal(0, 1) * i/10 for i in range(len(dates))]

        sample_data = pd.DataFrame({
            "date": dates,
            "open": prices,
            "high": [p + abs(np.random.normal(0, 0.5)) for p in prices],
            "low": [p - abs(np.random.normal(0, 0.5)) for p in prices],
            "close": [p + np.random.normal(0, 0.3) for p in prices],
            "volume": [np.random.randint(1000000, 10000000) for _ in prices],
        })

        print("Running basic integration test...")

        # Test 1: Model initialization
        print("\n1. Testing model initialization...")
        model = HierarchicalTimeframeNet(num_timeframes=3)
        print(f"   ✓ Model created with {sum(p.numel() for p in model.parameters()):,} parameters")

        # Test 2: Forward pass
        print("\n2. Testing forward pass...")
        x = torch.randn(4, 173)
        logits = model(x)
        print(f"   ✓ Forward pass successful: {x.shape} → {logits.shape}")

        # Test 3: Prediction
        print("\n3. Testing prediction...")
        actions, confidences = model.predict(x)
        print(f"   ✓ Predictions: {actions.tolist()}")
        print(f"   ✓ Confidences: {[f'{c:.2f}' for c in confidences.tolist()]}")

        print("\n✓ All basic tests passed!")
