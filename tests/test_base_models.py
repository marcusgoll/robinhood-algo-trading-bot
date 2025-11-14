#!/usr/bin/env python3
"""Unit tests for base models in Phase 3 ensemble system.

Tests LSTM, GRU, and Transformer models for:
- Correct input/output dimensions
- Forward pass execution
- Prediction probability generation
- Model initialization
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import numpy as np
import torch

from trading_bot.ml.ensemble.base_models import (
    BaseModel,
    LSTMModel,
    GRUModel,
    TransformerModel,
)


def test_lstm_model():
    """Test LSTM model architecture and forward pass."""
    print("[TEST] LSTMModel")
    print("-" * 80)

    # Initialize model
    model = LSTMModel(
        input_dim=52,
        hidden_dim=128,
        num_layers=2,
        dropout=0.3,
        output_dim=3
    )
    print("[OK] Model initialized")

    # Test forward pass with single feature vector
    batch_size = 32
    x_single = torch.randn(batch_size, 52)
    logits = model.forward(x_single)

    assert logits.shape == (batch_size, 3), f"Expected shape (32, 3), got {logits.shape}"
    print(f"[OK] Forward pass (single vector): {x_single.shape} -> {logits.shape}")

    # Test forward pass with sequence
    seq_len = 10
    x_seq = torch.randn(batch_size, seq_len, 52)
    logits_seq = model.forward(x_seq)

    assert logits_seq.shape == (batch_size, 3), f"Expected shape (32, 3), got {logits_seq.shape}"
    print(f"[OK] Forward pass (sequence): {x_seq.shape} -> {logits_seq.shape}")

    # Test predict_proba
    x_numpy = np.random.randn(100, 52).astype(np.float64)
    probs = model.predict_proba(x_numpy)

    assert probs.shape == (100, 3), f"Expected shape (100, 3), got {probs.shape}"
    assert np.allclose(probs.sum(axis=1), 1.0, atol=1e-5), "Probabilities should sum to 1"
    assert (probs >= 0).all() and (probs <= 1).all(), "Probabilities should be in [0, 1]"
    print(f"[OK] predict_proba: {x_numpy.shape} -> {probs.shape}")
    print(f"     Sample probs: {probs[0]}")
    print()


def test_gru_model():
    """Test GRU model architecture and forward pass."""
    print("[TEST] GRUModel")
    print("-" * 80)

    # Initialize model
    model = GRUModel(
        input_dim=52,
        hidden_dim=128,
        num_layers=2,
        dropout=0.3,
        output_dim=3
    )
    print("[OK] Model initialized")

    # Test forward pass with single feature vector
    batch_size = 32
    x_single = torch.randn(batch_size, 52)
    logits = model.forward(x_single)

    assert logits.shape == (batch_size, 3), f"Expected shape (32, 3), got {logits.shape}"
    print(f"[OK] Forward pass (single vector): {x_single.shape} -> {logits.shape}")

    # Test forward pass with sequence
    seq_len = 10
    x_seq = torch.randn(batch_size, seq_len, 52)
    logits_seq = model.forward(x_seq)

    assert logits_seq.shape == (batch_size, 3), f"Expected shape (32, 3), got {logits_seq.shape}"
    print(f"[OK] Forward pass (sequence): {x_seq.shape} -> {logits_seq.shape}")

    # Test predict_proba
    x_numpy = np.random.randn(100, 52).astype(np.float64)
    probs = model.predict_proba(x_numpy)

    assert probs.shape == (100, 3), f"Expected shape (100, 3), got {probs.shape}"
    assert np.allclose(probs.sum(axis=1), 1.0, atol=1e-5), "Probabilities should sum to 1"
    assert (probs >= 0).all() and (probs <= 1).all(), "Probabilities should be in [0, 1]"
    print(f"[OK] predict_proba: {x_numpy.shape} -> {probs.shape}")
    print(f"     Sample probs: {probs[0]}")
    print()


def test_transformer_model():
    """Test Transformer model architecture and forward pass."""
    print("[TEST] TransformerModel")
    print("-" * 80)

    # Initialize model
    model = TransformerModel(
        input_dim=52,
        d_model=128,
        nhead=4,
        num_layers=2,
        dim_feedforward=512,
        dropout=0.3,
        output_dim=3
    )
    print("[OK] Model initialized")

    # Test forward pass with single feature vector
    batch_size = 32
    x_single = torch.randn(batch_size, 52)
    logits = model.forward(x_single)

    assert logits.shape == (batch_size, 3), f"Expected shape (32, 3), got {logits.shape}"
    print(f"[OK] Forward pass (single vector): {x_single.shape} -> {logits.shape}")

    # Test forward pass with sequence
    seq_len = 10
    x_seq = torch.randn(batch_size, seq_len, 52)
    logits_seq = model.forward(x_seq)

    assert logits_seq.shape == (batch_size, 3), f"Expected shape (32, 3), got {logits_seq.shape}"
    print(f"[OK] Forward pass (sequence): {x_seq.shape} -> {logits_seq.shape}")

    # Test predict_proba
    x_numpy = np.random.randn(100, 52).astype(np.float64)
    probs = model.predict_proba(x_numpy)

    assert probs.shape == (100, 3), f"Expected shape (100, 3), got {probs.shape}"
    assert np.allclose(probs.sum(axis=1), 1.0, atol=1e-5), "Probabilities should sum to 1"
    assert (probs >= 0).all() and (probs <= 1).all(), "Probabilities should be in [0, 1]"
    print(f"[OK] predict_proba: {x_numpy.shape} -> {probs.shape}")
    print(f"     Sample probs: {probs[0]}")
    print()


def test_model_diversity():
    """Test that different models produce different predictions (diverse biases)."""
    print("[TEST] Model Diversity")
    print("-" * 80)

    # Initialize all models
    lstm = LSTMModel()
    gru = GRUModel()
    transformer = TransformerModel()

    # Generate random input
    x = np.random.randn(50, 52).astype(np.float64)

    # Get predictions from each model
    lstm_pred = lstm.predict_proba(x)
    gru_pred = gru.predict_proba(x)
    trans_pred = transformer.predict_proba(x)

    print("[OK] Generated predictions from all 3 models")

    # Calculate correlation between predictions
    # (Diversity is important - we want LOW correlation)
    lstm_flat = lstm_pred.flatten()
    gru_flat = gru_pred.flatten()
    trans_flat = trans_pred.flatten()

    corr_lstm_gru = np.corrcoef(lstm_flat, gru_flat)[0, 1]
    corr_lstm_trans = np.corrcoef(lstm_flat, trans_flat)[0, 1]
    corr_gru_trans = np.corrcoef(gru_flat, trans_flat)[0, 1]

    print(f"[INFO] Prediction correlations (lower = more diverse):")
    print(f"       LSTM vs GRU:         {corr_lstm_gru:.4f}")
    print(f"       LSTM vs Transformer: {corr_lstm_trans:.4f}")
    print(f"       GRU vs Transformer:  {corr_gru_trans:.4f}")

    # Models should have different predictions (not perfectly correlated)
    # Note: With random initialization, correlations will be near 0
    assert abs(corr_lstm_gru) < 0.5, "LSTM and GRU too correlated (not diverse enough)"
    assert abs(corr_lstm_trans) < 0.5, "LSTM and Transformer too correlated"
    assert abs(corr_gru_trans) < 0.5, "GRU and Transformer too correlated"

    print("[OK] Models show sufficient diversity (correlations < 0.5)")
    print()


def test_parameter_counts():
    """Test that models have reasonable parameter counts."""
    print("[TEST] Parameter Counts")
    print("-" * 80)

    lstm = LSTMModel()
    gru = GRUModel()
    transformer = TransformerModel()

    def count_parameters(model):
        return sum(p.numel() for p in model.parameters() if p.requires_grad)

    lstm_params = count_parameters(lstm)
    gru_params = count_parameters(gru)
    trans_params = count_parameters(transformer)

    print(f"[INFO] Model parameter counts:")
    print(f"       LSTM:        {lstm_params:,} parameters")
    print(f"       GRU:         {gru_params:,} parameters")
    print(f"       Transformer: {trans_params:,} parameters")

    # Sanity checks
    assert lstm_params > 10000, "LSTM should have reasonable number of parameters"
    assert gru_params > 10000, "GRU should have reasonable number of parameters"
    assert trans_params > 10000, "Transformer should have reasonable number of parameters"

    # GRU should have fewer parameters than LSTM (simpler architecture)
    assert gru_params < lstm_params, "GRU should have fewer parameters than LSTM"

    print("[OK] All models have reasonable parameter counts")
    print()


def main():
    """Run all base model tests."""
    print("=" * 80)
    print("PHASE 3 BASE MODEL UNIT TESTS")
    print("=" * 80)
    print()

    try:
        test_lstm_model()
        test_gru_model()
        test_transformer_model()
        test_model_diversity()
        test_parameter_counts()

        print("=" * 80)
        print("TEST RESULTS")
        print("=" * 80)
        print("[OK] All base model tests passed!")
        print()
        print("Base models are ready for integration with meta-learner.")
        print()
        return 0

    except AssertionError as e:
        print(f"\n[ERROR] Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
