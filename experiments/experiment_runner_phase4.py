"""
Phase 4A Experiment Runner - Multi-Timeframe Feature Engineering

This runner tests different timeframe combinations while keeping the model
and horizon fixed at Phase 3 winner settings.

Goal: Improve from 59.65% to 60-61% accuracy via multi-timeframe features.
"""

import os
import yaml
import argparse
from typing import Dict, Any, List
from concurrent.futures import ProcessPoolExecutor, as_completed
import pandas as pd
import numpy as np
from dotenv import load_dotenv

# Import our modules
from multi_timeframe_features import create_multi_tf_dataset
from models_v2 import create_model
from experiment_tracker import ExperimentTracker

import warnings
warnings.filterwarnings('ignore')


def load_phase4_config(config_path: str = "phase4_feature_config.yaml") -> Dict[str, Any]:
    """Load Phase 4 configuration."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def generate_phase4_experiments(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Generate experiment configurations for Phase 4A.

    Returns list of experiments, each testing a different feature set.
    """
    experiments = []

    # Fixed parameters from Phase 3 winner
    model_config = config['model']
    horizon_config = config['horizon']
    training_config = config['training']

    # Variable: feature sets
    for feature_set in config['feature_sets']:
        if not feature_set.get('enabled', True):
            continue

        # For each symbol
        for symbol_config in config['symbols']:
            if not symbol_config.get('enabled', True):
                continue

            exp = {
                # Fixed from Phase 3
                'model_name': model_config['name'],
                'model_type': model_config['type'],
                'hidden_dim': model_config['params']['hidden_dim'],
                'num_layers': model_config['params']['num_layers'],
                'dropout': model_config['params']['dropout'],
                'horizon_name': horizon_config['name'],
                'horizon_bars': horizon_config['bars'],
                'learning_rate': training_config['learning_rate'],
                'batch_size': training_config['batch_size'],
                'max_epochs': training_config['max_epochs'],

                # Variable: feature set
                'feature_set_name': feature_set['name'],
                'primary_timeframe': feature_set['primary_timeframe'],
                'additional_timeframes': feature_set['additional_timeframes'],

                # Symbol and data
                'symbol': symbol_config['symbol'],
                'data_days': symbol_config['data_days'],
            }

            experiments.append(exp)

    print(f"Generated {len(experiments)} Phase 4A experiments")
    return experiments


def train_model_with_early_stopping(model, X_train, y_train, X_val, y_val,
                                   learning_rate=0.0001, batch_size=32,
                                   max_epochs=50, patience=5, device='cpu'):
    """Train model with early stopping - same as Phase 3."""
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import TensorDataset, DataLoader

    model = model.to(device)
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=learning_rate)

    # Create data loaders
    train_dataset = TensorDataset(
        torch.FloatTensor(X_train),
        torch.FloatTensor(y_train)
    )
    val_dataset = TensorDataset(
        torch.FloatTensor(X_val),
        torch.FloatTensor(y_val)
    )

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)

    best_val_loss = float('inf')
    patience_counter = 0

    for epoch in range(max_epochs):
        # Training
        model.train()
        train_loss = 0.0
        for X_batch, y_batch in train_loader:
            X_batch = X_batch.to(device)
            y_batch = y_batch.to(device).unsqueeze(1)

            optimizer.zero_grad()
            outputs = model(X_batch)
            loss = criterion(outputs, y_batch)
            loss.backward()
            optimizer.step()

            train_loss += loss.item()

        # Validation
        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for X_batch, y_batch in val_loader:
                X_batch = X_batch.to(device)
                y_batch = y_batch.to(device).unsqueeze(1)
                outputs = model(X_batch)
                loss = criterion(outputs, y_batch)
                val_loss += loss.item()

        val_loss /= len(val_loader)

        # Early stopping check
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            patience_counter = 0
        else:
            patience_counter += 1
            if patience_counter >= patience:
                return epoch + 1  # Return actual epochs trained

    return max_epochs


def evaluate_model(model, X_test, y_test, device='cpu'):
    """Evaluate model - same as Phase 3."""
    import torch

    model = model.to(device)
    model.eval()

    with torch.no_grad():
        X_tensor = torch.FloatTensor(X_test).to(device)
        predictions = model(X_tensor).cpu().numpy().flatten()

    # Calculate metrics
    from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

    mse = mean_squared_error(y_test, predictions)
    rmse = np.sqrt(mse)
    mae = mean_absolute_error(y_test, predictions)
    r2 = r2_score(y_test, predictions)

    # Directional accuracy
    y_test_direction = np.sign(y_test)
    pred_direction = np.sign(predictions)
    directional_accuracy = np.mean(y_test_direction == pred_direction) * 100

    return {
        'directional_accuracy': directional_accuracy,
        'mse': mse,
        'rmse': rmse,
        'mae': mae,
        'r2': r2
    }


def run_single_phase4_experiment(config: Dict[str, Any], db_path: str = "experiments_phase4.db") -> Dict[str, Any]:
    """
    Run a single Phase 4 experiment.

    This is similar to Phase 3 but uses multi-timeframe feature extraction.
    """
    tracker = ExperimentTracker(db_path)

    # Check if already completed
    existing = tracker.get_experiment_by_config(config)
    if existing:
        print(f"[CACHE HIT] {config['feature_set_name']} - using cached result")
        tracker.close()
        return existing

    exp_id = tracker.start_experiment(config)

    try:
        # Load credentials
        load_dotenv()
        api_key = os.getenv('ALPACA_API_KEY')
        api_secret = os.getenv('ALPACA_SECRET_KEY')

        if not api_key or not api_secret:
            raise ValueError("Missing Alpaca credentials")

        print(f"[{config['feature_set_name']}] Fetching data...")

        # Fetch multi-timeframe data
        if len(config['additional_timeframes']) == 0:
            # Baseline: single timeframe (use Phase 3 approach)
            from experiment_runner import fetch_data, extract_features_and_targets
            df = fetch_data(
                symbol=config['symbol'],
                timeframe=config['primary_timeframe'],
                days=config['data_days'],
                api_key=api_key,
                api_secret=api_secret
            )
            X, y = extract_features_and_targets(df, config['horizon_bars'])
        else:
            # Multi-timeframe
            X, y, feature_names = create_multi_tf_dataset(
                symbol=config['symbol'],
                primary_timeframe=config['primary_timeframe'],
                additional_timeframes=config['additional_timeframes'],
                horizon_bars=config['horizon_bars'],
                days=config['data_days'],
                api_key=api_key,
                api_secret=api_secret
            )

        print(f"[{config['feature_set_name']}] Dataset: {X.shape[0]} samples, {X.shape[1]} features")

        # Train/val/test split (60/20/20)
        n = len(X)
        train_end = int(0.6 * n)
        val_end = int(0.8 * n)

        X_train, y_train = X[:train_end], y[:train_end]
        X_val, y_val = X[train_end:val_end], y[train_end:val_end]
        X_test, y_test = X[val_end:], y[val_end:]

        # Create model
        model_config_dict = {
            'model_type': config['model_type'],
            'input_dim': X.shape[1],
            'hidden_dim': config['hidden_dim'],
            'num_layers': config['num_layers'],
            'dropout': config['dropout']
        }
        model = create_model(model_config_dict)

        print(f"[{config['feature_set_name']}] Training...")

        # Train
        actual_epochs = train_model_with_early_stopping(
            model=model,
            X_train=X_train,
            y_train=y_train,
            X_val=X_val,
            y_val=y_val,
            learning_rate=config['learning_rate'],
            batch_size=config['batch_size'],
            max_epochs=config['max_epochs'],
            patience=5,
            device='cpu'
        )

        # Evaluate
        metrics = evaluate_model(model, X_test, y_test, device='cpu')

        print(f"[{config['feature_set_name']}] Result: {metrics['directional_accuracy']:.2f}% accuracy")

        # Record results
        results = {
            **config,
            **metrics,
            'num_samples': len(X),
            'num_features': X.shape[1],
            'actual_epochs': actual_epochs
        }

        tracker.complete_experiment(exp_id, results, status="completed")
        tracker.close()
        return results

    except Exception as e:
        error_msg = str(e)
        print(f"[{config['feature_set_name']}] ERROR: {error_msg}")
        tracker.complete_experiment(exp_id, {"error_message": error_msg}, status="failed")
        tracker.close()
        return {"status": "failed", "error": error_msg, **config}


def run_phase4_experiments_parallel(experiments: List[Dict[str, Any]],
                                   max_workers: int = 4,
                                   db_path: str = "experiments_phase4.db") -> pd.DataFrame:
    """Run Phase 4 experiments in parallel."""
    results = []

    print(f"\nStarting Phase 4A experiments with {max_workers} workers...")
    print(f"Total experiments: {len(experiments)}")
    print("=" * 80)

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        # Submit all experiments
        future_to_exp = {
            executor.submit(run_single_phase4_experiment, exp, db_path): exp
            for exp in experiments
        }

        # Collect results as they complete
        completed = 0
        for future in as_completed(future_to_exp):
            result = future.result()
            results.append(result)
            completed += 1

            if result.get('status') != 'failed':
                acc = result.get('directional_accuracy', 0)
                print(f"[{completed}/{len(experiments)}] {result['feature_set_name']}: {acc:.2f}%")
            else:
                print(f"[{completed}/{len(experiments)}] {result['feature_set_name']}: FAILED")

    return pd.DataFrame(results)


def main():
    parser = argparse.ArgumentParser(description='Phase 4A Multi-Timeframe Feature Engineering')
    parser.add_argument('--config', type=str, default='phase4_feature_config.yaml',
                       help='Path to Phase 4 config file')
    parser.add_argument('--max-workers', type=int, default=4,
                       help='Number of parallel workers')
    parser.add_argument('--db-path', type=str, default='experiments_phase4.db',
                       help='Database path for tracking')

    args = parser.parse_args()

    # Load config
    config = load_phase4_config(args.config)

    # Generate experiments
    experiments = generate_phase4_experiments(config)

    # Run experiments
    results_df = run_phase4_experiments_parallel(
        experiments=experiments,
        max_workers=args.max_workers,
        db_path=args.db_path
    )

    # Save results
    output_file = 'phase4a_results.csv'
    results_df.to_csv(output_file, index=False)
    print(f"\nResults saved to {output_file}")

    # Show top results
    successful = results_df[results_df['status'] != 'failed']
    if len(successful) > 0:
        print("\n" + "=" * 80)
        print("TOP 5 FEATURE SETS:")
        print("=" * 80)
        top5 = successful.nlargest(5, 'directional_accuracy')
        print(top5[['feature_set_name', 'directional_accuracy', 'rmse', 'r2', 'num_features']].to_string(index=False))

        best = successful.iloc[successful['directional_accuracy'].idxmax()]
        baseline = 59.65  # Phase 3 winner
        improvement = best['directional_accuracy'] - baseline

        print(f"\nBest: {best['feature_set_name']}")
        print(f"Accuracy: {best['directional_accuracy']:.2f}%")
        print(f"Improvement: {improvement:+.2f}%")
        print(f"Features: {best['num_features']}")

        if best['directional_accuracy'] >= 60.50:
            print("\nPHASE 4A TARGET ACHIEVED (60.50%+)!")
        elif best['directional_accuracy'] >= 60.00:
            print("\nGood progress toward target!")
        else:
            print("\nNo significant improvement - may need Phase 4B (sentiment)")


if __name__ == "__main__":
    main()
