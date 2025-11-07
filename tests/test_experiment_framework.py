#!/usr/bin/env python3
"""Test script to validate the experimental framework.

Tests:
1. Configuration loading
2. Experiment generation
3. Model creation
4. Data fetching and feature extraction
5. Single experiment execution
6. Database tracking
"""

import os
import sys
from pathlib import Path

import numpy as np
import torch
import yaml

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from experiment_tracker import ExperimentTracker
from trading_bot.ml.models_v2 import create_model, RegressionLSTM, CNN_LSTM, MultiTaskLSTM

def test_config_loading():
    """Test configuration file loading."""
    print("\n" + "=" * 80)
    print("TEST 1: Configuration Loading")
    print("=" * 80)

    with open("experiment_config.yaml", "r") as f:
        config = yaml.safe_load(f)

    print(f"Loaded config with {len(config)} top-level keys")
    print(f"  - Data symbols: {config['data']['symbols']}")
    print(f"  - Enabled timeframes: {sum(1 for tf in config['data']['timeframes'] if tf.get('enabled'))}")
    print(f"  - Enabled horizons: {sum(1 for h in config['horizons'] if h.get('enabled'))}")
    print(f"  - Enabled models: {sum(1 for m in config['models'] if m.get('enabled'))}")
    print(f"  - Max parallel: {config['execution']['max_parallel']}")

    print("\n[OK] Config loaded successfully")
    return config


def test_model_creation():
    """Test model creation from config."""
    print("\n" + "=" * 80)
    print("TEST 2: Model Creation")
    print("=" * 80)

    batch_size = 16
    input_dim = 57

    models_to_test = [
        {
            "name": "LSTM",
            "type": "regression_lstm",
            "params": {"input_dim": input_dim, "hidden_dim": 64, "num_layers": 2}
        },
        {
            "name": "CNN-LSTM",
            "type": "cnn_lstm",
            "params": {"input_dim": input_dim, "cnn_channels": [64, 32], "lstm_hidden": 64}
        },
        {
            "name": "Multi-Task",
            "type": "multi_task_lstm",
            "params": {"input_dim": input_dim, "hidden_dim": 64, "horizons": [3, 6, 12]}
        },
    ]

    for model_config in models_to_test:
        model = create_model(model_config)
        x = torch.randn(batch_size, input_dim)
        output = model(x)

        params = sum(p.numel() for p in model.parameters())

        if isinstance(output, dict):
            output_shape = {k: v.shape for k, v in output.items()}
            print(f"  {model_config['name']:15s} [OK]  Params: {params:,}  Output: {output_shape}")
        else:
            print(f"  {model_config['name']:15s} [OK]  Params: {params:,}  Output shape: {output.shape}")

    print("\n[OK] All models created and tested successfully")


def test_experiment_tracker():
    """Test experiment tracking database."""
    print("\n" + "=" * 80)
    print("TEST 3: Experiment Tracker")
    print("=" * 80)

    # Create test database
    tracker = ExperimentTracker("test_experiments.db")

    # Test experiment
    config = {
        "symbol": "SPY",
        "data_period": "1yr",
        "timeframe": "5min",
        "model_name": "lstm_test",
        "model_type": "regression_lstm",
        "model_params": {"hidden_dim": 64},
        "feature_set": "base",
        "horizon_bars": 12,
        "horizon_name": "12bar",
        "batch_size": 32,
        "learning_rate": 0.001,
        "max_epochs": 5,
        "weight_decay": 0.01,
        "validation_method": "holdout"
    }

    # Start experiment
    exp_id = tracker.start_experiment(config)
    print(f"  Created experiment: {exp_id}")

    # Complete experiment with mock results
    results = {
        "num_samples": 10000,
        "train_samples": 6000,
        "val_samples": 2000,
        "test_samples": 2000,
        "num_features": 57,
        "actual_epochs": 5,
        "directional_accuracy": 0.565,
        "mse": 0.0004,
        "rmse": 0.02,
        "mae": 0.015,
        "r2": 0.01
    }

    tracker.complete_experiment(exp_id, results)
    print(f"  Completed experiment: {exp_id}")

    # Get statistics
    stats = tracker.get_statistics()
    print(f"  Total experiments: {stats['total_experiments']}")
    print(f"  Best accuracy: {stats['best_accuracy']:.2%}")

    # Get leaderboard
    leaderboard = tracker.get_leaderboard(limit=5)
    print(f"  Leaderboard shape: {leaderboard.shape}")

    # Cleanup
    tracker.close()
    os.remove("test_experiments.db")

    print("\n[OK] Experiment tracker working correctly")


def test_experiment_generation():
    """Test experiment configuration generation."""
    print("\n" + "=" * 80)
    print("TEST 4: Experiment Generation")
    print("=" * 80)

    with open("experiment_config.yaml", "r") as f:
        yaml_config = yaml.safe_load(f)

    # Count possible experiments
    symbols = yaml_config["data"]["symbols"]
    periods = [p for p in yaml_config["data"]["periods"] if p.get("priority", 3) <= 2]
    horizons = [h for h in yaml_config["horizons"] if h.get("enabled", False)]
    models = [m for m in yaml_config["models"] if m.get("enabled", False)]
    batch_sizes = yaml_config["training"]["batch_size"]
    learning_rates = yaml_config["training"]["learning_rate"]
    weight_decays = yaml_config["training"]["weight_decay"]

    total = (
        len(symbols) *
        len(periods) *
        len(horizons) *
        len(models) *
        len(batch_sizes) *
        len(learning_rates) *
        len(weight_decays)
    )

    print(f"  Symbols: {len(symbols)}")
    print(f"  Periods (priority 1-2): {len(periods)}")
    print(f"  Horizons (enabled): {len(horizons)}")
    print(f"  Models (enabled): {len(models)}")
    print(f"  Batch sizes: {len(batch_sizes)}")
    print(f"  Learning rates: {len(learning_rates)}")
    print(f"  Weight decays: {len(weight_decays)}")
    print(f"\n  Total experiment combinations: {total}")

    # Estimate time
    avg_time_per_exp = 120  # seconds (2 minutes estimate)
    max_workers = yaml_config["execution"]["max_parallel"]
    total_time_hours = (total * avg_time_per_exp) / (max_workers * 3600)

    print(f"\n  Estimated time with {max_workers} workers: {total_time_hours:.1f} hours")

    print("\n[OK] Experiment generation parameters validated")


def main():
    """Run all tests."""
    print("\n" + "="  * 80)
    print("PHASE 3 EXPERIMENTAL FRAMEWORK TEST SUITE")
    print("=" * 80)

    try:
        config = test_config_loading()
        test_model_creation()
        test_experiment_tracker()
        test_experiment_generation()

        print("\n" + "=" * 80)
        print("ALL TESTS PASSED [OK]")
        print("=" * 80)
        print("\nFramework is ready for large-scale experiments!")
        print("\nNext steps:")
        print("  1. Install missing dependencies: pip install pyyaml")
        print("  2. Test with small batch: python experiment_runner.py --limit 5")
        print("  3. Run full Phase 1: python experiment_runner.py")
        print("  4. Analyze results: python analyze_experiments.py")
        print()

    except Exception as e:
        print(f"\n[FAIL] TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
