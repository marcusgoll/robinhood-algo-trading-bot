"""
Phase 5: Ensemble Approach - Multiple Models with Averaged Predictions

Strategy: Train 5 baseline models with different random seeds and average
their predictions. This leverages the baseline's stability while reducing
variance through ensemble averaging.

Expected: 61-62% accuracy with high stability (better than single model).
"""

import os
import numpy as np
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import TensorDataset, DataLoader
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

# Import Phase 4 components
from multi_timeframe_features import create_multi_tf_dataset
from validate_phase4 import AttentionLSTM


def set_seed(seed: int):
    """Set random seeds for reproducibility."""
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def train_model(X_train, y_train, X_val, y_val, seed: int,
                learning_rate=0.0001, batch_size=32, max_epochs=30,
                patience=5, device='cpu'):
    """Train a single model with specified seed."""
    set_seed(seed)

    model = AttentionLSTM(input_dim=X_train.shape[1], hidden_dim=64,
                         num_layers=2, dropout=0.3).to(device)
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=learning_rate)

    # Data loaders
    train_loader = DataLoader(
        TensorDataset(torch.FloatTensor(X_train), torch.FloatTensor(y_train)),
        batch_size=batch_size, shuffle=True
    )
    val_loader = DataLoader(
        TensorDataset(torch.FloatTensor(X_val), torch.FloatTensor(y_val)),
        batch_size=batch_size, shuffle=False
    )

    best_val_loss = float('inf')
    patience_counter = 0

    for epoch in range(max_epochs):
        # Training
        model.train()
        for X_batch, y_batch in train_loader:
            X_batch, y_batch = X_batch.to(device), y_batch.to(device).unsqueeze(1)
            optimizer.zero_grad()
            outputs = model(X_batch)
            loss = criterion(outputs, y_batch)
            loss.backward()
            optimizer.step()

        # Validation
        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for X_batch, y_batch in val_loader:
                X_batch, y_batch = X_batch.to(device), y_batch.to(device).unsqueeze(1)
                outputs = model(X_batch)
                val_loss += criterion(outputs, y_batch).item()

        val_loss /= len(val_loader)

        # Early stopping
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            patience_counter = 0
        else:
            patience_counter += 1
            if patience_counter >= patience:
                break

    return model


def evaluate_model(model, X_test, y_test, device='cpu'):
    """Evaluate a single model and return predictions."""
    model = model.to(device)
    model.eval()

    with torch.no_grad():
        X_tensor = torch.FloatTensor(X_test).to(device)
        predictions = model(X_tensor).cpu().numpy().flatten()

    return predictions


def evaluate_ensemble(predictions_list, y_test):
    """Evaluate ensemble by averaging predictions."""
    # Average predictions across all models
    ensemble_predictions = np.mean(predictions_list, axis=0)

    # Calculate metrics
    mse = mean_squared_error(y_test, ensemble_predictions)
    rmse = np.sqrt(mse)
    mae = mean_absolute_error(y_test, ensemble_predictions)
    r2 = r2_score(y_test, ensemble_predictions)

    # Directional accuracy
    y_test_direction = np.sign(y_test)
    pred_direction = np.sign(ensemble_predictions)
    directional_accuracy = np.mean(y_test_direction == pred_direction) * 100

    return {
        'directional_accuracy': directional_accuracy,
        'mse': mse,
        'rmse': rmse,
        'mae': mae,
        'r2': r2,
        'ensemble_predictions': ensemble_predictions
    }


def main():
    load_dotenv()
    api_key = os.getenv('ALPACA_API_KEY')
    api_secret = os.getenv('ALPACA_SECRET_KEY')

    if not api_key or not api_secret:
        print("ERROR: Missing Alpaca credentials")
        return

    print("=" * 80)
    print("PHASE 5: ENSEMBLE VALIDATION")
    print("=" * 80)
    print()
    print("Strategy: Train 5 baseline models with different seeds")
    print("Method: Average predictions across all models")
    print("Expected: Improved accuracy + reduced variance")
    print()

    # Configuration
    symbol = 'SPY'
    num_models = 5
    seeds = list(range(num_models))

    # Fetch data once (baseline configuration)
    print(f"Fetching data for {symbol}...")
    X, y, features = create_multi_tf_dataset(
        symbol=symbol,
        primary_timeframe='5Min',
        additional_timeframes=[],  # Baseline: 5Min only
        horizon_bars=78,
        days=60,
        api_key=api_key,
        api_secret=api_secret
    )

    print(f"Dataset: {X.shape[0]} samples, {X.shape[1]} features")
    print()

    # Train/val/test split (60/20/20)
    n = len(X)
    train_end = int(0.6 * n)
    val_end = int(0.8 * n)

    X_train, y_train = X[:train_end], y[:train_end]
    X_val, y_val = X[train_end:val_end], y[train_end:val_end]
    X_test, y_test = X[val_end:], y[val_end:]

    print(f"Split: Train={len(X_train)}, Val={len(X_val)}, Test={len(X_test)}")
    print()

    # Train ensemble
    print(f"Training {num_models}-model ensemble...")
    print("-" * 80)

    models = []
    individual_accuracies = []

    for i, seed in enumerate(seeds):
        print(f"Model {i+1}/{num_models} (seed={seed})... ", end="", flush=True)

        model = train_model(
            X_train, y_train, X_val, y_val,
            seed=seed,
            learning_rate=0.0001,
            batch_size=32,
            max_epochs=30,
            patience=5,
            device='cpu'
        )

        # Evaluate individual model
        predictions = evaluate_model(model, X_test, y_test, device='cpu')
        y_test_direction = np.sign(y_test)
        pred_direction = np.sign(predictions)
        acc = np.mean(y_test_direction == pred_direction) * 100

        models.append(model)
        individual_accuracies.append(acc)

        print(f"Accuracy: {acc:.2f}%")

    print()
    print(f"Individual model accuracies: {individual_accuracies}")
    print(f"Mean: {np.mean(individual_accuracies):.2f}% +/- {np.std(individual_accuracies):.2f}%")
    print()

    # Evaluate ensemble
    print("Evaluating ensemble (averaged predictions)...")
    print("-" * 80)

    # Collect predictions from all models
    predictions_list = []
    for model in models:
        predictions = evaluate_model(model, X_test, y_test, device='cpu')
        predictions_list.append(predictions)

    # Evaluate ensemble
    ensemble_results = evaluate_ensemble(predictions_list, y_test)

    print(f"Ensemble Directional Accuracy: {ensemble_results['directional_accuracy']:.2f}%")
    print(f"Ensemble RMSE: {ensemble_results['rmse']:.6f}")
    print(f"Ensemble MAE: {ensemble_results['mae']:.6f}")
    print(f"Ensemble R2: {ensemble_results['r2']:.4f}")
    print()

    # Compare to baseline
    baseline_mean = np.mean(individual_accuracies)
    improvement = ensemble_results['directional_accuracy'] - baseline_mean

    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    print(f"Individual Models (mean): {baseline_mean:.2f}% +/- {np.std(individual_accuracies):.2f}%")
    print(f"Ensemble (averaged):      {ensemble_results['directional_accuracy']:.2f}%")
    print(f"Improvement:              {improvement:+.2f}%")
    print()

    if improvement > 1.0:
        print("SUCCESS: Ensemble provides significant improvement!")
    elif improvement > 0:
        print("MARGINAL: Ensemble provides slight improvement")
    else:
        print("NO BENEFIT: Ensemble does not improve over individual models")

    print()

    # Prediction distribution analysis
    print("Ensemble Prediction Analysis:")
    print(f"  Prediction std (across models): {np.mean([np.std([predictions_list[j][i] for j in range(num_models)]) for i in range(len(y_test))]):.6f}")
    print(f"  Agreement rate (sign): {np.mean([np.std([np.sign(predictions_list[j][i]) for j in range(num_models)]) == 0 for i in range(len(y_test))]) * 100:.2f}%")
    print()

    # Save results
    results = {
        'symbol': symbol,
        'num_models': num_models,
        'individual_mean_acc': baseline_mean,
        'individual_std_acc': np.std(individual_accuracies),
        'ensemble_acc': ensemble_results['directional_accuracy'],
        'improvement': improvement,
        'ensemble_rmse': ensemble_results['rmse'],
        'ensemble_mae': ensemble_results['mae'],
        'ensemble_r2': ensemble_results['r2']
    }

    df = pd.DataFrame([results])
    output_file = 'phase5_ensemble_results.csv'
    df.to_csv(output_file, index=False)
    print(f"Results saved to {output_file}")
    print()
    print("=" * 80)


if __name__ == "__main__":
    main()
