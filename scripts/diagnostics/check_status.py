#!/usr/bin/env python3
"""Quick status check for experiment sweep."""

from experiment_tracker import ExperimentTracker
import pandas as pd

t = ExperimentTracker()

# Get statistics
stats = t.get_statistics()
print("===== EXPERIMENT STATS =====")
print(f"Total experiments: {stats['total_experiments']}")

# Count by status
completed = len(pd.read_sql('SELECT * FROM experiments WHERE status="completed"', t.conn))
failed = len(pd.read_sql('SELECT * FROM experiments WHERE status="failed"', t.conn))
running = stats['total_experiments'] - completed - failed

print(f"Completed: {completed}")
print(f"Failed: {failed}")
print(f"Running: {running}")

if completed > 0:
    print(f"Success Rate: {completed/(completed+failed)*100:.1f}%")
print(f"Remaining: {1620 - stats['total_experiments']}")

print()
print("===== TOP 10 LEADERBOARD =====")
lb = t.get_leaderboard(10)
print(lb[['experiment_id', 'model_name', 'horizon_name', 'directional_accuracy', 'rmse', 'r2', 'actual_epochs']].to_string(index=False))

t.close()
