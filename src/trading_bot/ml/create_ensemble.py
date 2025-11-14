#!/usr/bin/env python3
"""Ensemble Creation Script

Creates and analyzes strategy ensembles with correlation analysis.

Usage:
    # Create ensemble from top strategies
    python -m trading_bot.ml.create_ensemble \
        --strategy-file ml_strategies/AAPL_20251103_201838.json \
        --top-n 5 \
        --method sharpe_weighted \
        --report ensemble_report.md
"""

import argparse
import json
import logging
import sys
from pathlib import Path

from trading_bot.ml.ensemble_builder import EnsembleBuilder, create_ensemble_from_selection
from trading_bot.ml.models import MLStrategy, StrategyGene, StrategyMetrics, StrategyStatus, StrategyType
from trading_bot.ml.strategy_selector import StrategySelector

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


def load_strategies_from_json(file_path: Path) -> list[MLStrategy]:
    """Load strategies from JSON file.

    Args:
        file_path: Path to JSON file

    Returns:
        List of MLStrategy objects
    """
    with open(file_path, 'r') as f:
        data = json.load(f)

    symbol = data.get("symbol", "UNKNOWN")
    strategies = []

    for strat_data in data.get("strategies", []):
        # Reconstruct StrategyGene
        gene_data = strat_data.get("gene", {})

        # Parse features from tree string
        tree_str = gene_data.get("tree", "")
        features_used = set()

        # Extract features from tree (simple parsing)
        for feature in ["rsi", "macd", "ema_12", "ema_26", "sma_20", "sma_50", "atr", "volume", "close"]:
            if feature in tree_str:
                features_used.add(feature)

        gene = StrategyGene(
            tree=tree_str,
            depth=gene_data.get("depth", 0),
            num_nodes=gene_data.get("num_nodes", 0),
            features_used=features_used,
        )

        # Reconstruct StrategyMetrics
        metrics_data = strat_data.get("metrics", {})
        metrics = StrategyMetrics(
            sharpe_ratio=metrics_data.get("sharpe_ratio", 0.0),
            max_drawdown=metrics_data.get("max_drawdown", 0.0),
            win_rate=metrics_data.get("win_rate", 0.0),
            profit_factor=metrics_data.get("profit_factor", 0.0),
            num_trades=metrics_data.get("num_trades", 0),
            total_return=metrics_data.get("total_return", 0.0),
        )

        # Create MLStrategy
        strategy = MLStrategy(
            name=strat_data.get("name", "Unknown"),
            type=StrategyType(strat_data.get("type", "genetic_programming")),
            status=StrategyStatus(strat_data.get("status", "generated")),
            entry_logic=strat_data.get("entry_logic", ""),
            gene=gene,
            backtest_metrics=metrics,
        )

        # Store symbol separately
        strategy._symbol = symbol

        strategies.append(strategy)

    logger.info(f"Loaded {len(strategies)} strategies from {file_path.name}")
    return strategies


def main():
    """Main ensemble creation entry point."""
    parser = argparse.ArgumentParser(description="Create and analyze strategy ensembles")

    parser.add_argument("--strategy-file", type=str, required=True, help="Path to strategy JSON file")
    parser.add_argument("--top-n", type=int, default=5, help="Number of top strategies to include")
    parser.add_argument("--method", type=str, default="sharpe_weighted",
                        choices=["equal_weight", "sharpe_weighted", "inverse_variance"],
                        help="Weighting method")
    parser.add_argument("--report", type=str, help="Output report file (markdown)")
    parser.add_argument("--name", type=str, default="ML_Ensemble_v1", help="Ensemble name")

    args = parser.parse_args()

    logger.info("="*80)
    logger.info("ENSEMBLE CREATION")
    logger.info("="*80)
    logger.info(f"Input file: {args.strategy_file}")
    logger.info(f"Top N strategies: {args.top_n}")
    logger.info(f"Weighting method: {args.method}")
    logger.info(f"Ensemble name: {args.name}")
    logger.info("="*80)

    # Load strategies
    strategy_file = Path(args.strategy_file)
    if not strategy_file.exists():
        logger.error(f"Strategy file not found: {strategy_file}")
        sys.exit(1)

    strategies = load_strategies_from_json(strategy_file)

    if not strategies:
        logger.error("No strategies loaded")
        sys.exit(1)

    # Rank strategies to select best ones
    selector = StrategySelector()
    ranked = selector.rank_strategies(strategies)

    # Select top N
    top_strategies = [score.strategy for score in ranked[:args.top_n]]

    logger.info(f"\nSelected top {len(top_strategies)} strategies:")
    for i, strat in enumerate(top_strategies, 1):
        logger.info(f"  {i}. {strat.name}: Sharpe={strat.backtest_metrics.sharpe_ratio:.2f}")

    # Create and analyze ensemble
    logger.info(f"\n{'='*80}")
    logger.info("CREATING ENSEMBLE")
    logger.info("="*80)

    ensemble, analysis = create_ensemble_from_selection(
        selected_strategies=top_strategies,
        weighting_method=args.method,
        ensemble_name=args.name,
    )

    # Display results
    logger.info(f"\n{'='*80}")
    logger.info("ENSEMBLE ANALYSIS")
    logger.info("="*80)
    logger.info(f"Ensemble: {ensemble.name}")
    logger.info(f"Strategies: {len(ensemble.strategies)}")
    logger.info(f"\nDiversity Metrics:")
    logger.info(f"  Average correlation: {analysis.avg_correlation:.2f}")
    logger.info(f"  Diversity score: {analysis.diversity_score:.1f}/100")
    logger.info(f"  Weight concentration: {analysis.weight_concentration:.2f}")
    logger.info(f"\nExpected Performance:")
    logger.info(f"  Expected Sharpe: {analysis.expected_sharpe:.2f}")
    logger.info(f"  Expected return: {analysis.expected_return:.1%}")
    logger.info(f"  Expected max DD: {analysis.expected_drawdown:.1%}")

    # Display correlation matrix
    logger.info(f"\nCorrelation Matrix:")
    n = len(ensemble.strategies)
    header = "     " + " ".join([f"S{i:2d}" for i in range(1, n + 1)])
    logger.info(header)

    for i, row in enumerate(analysis.correlation_matrix):
        row_str = f"S{i+1:2d}  " + " ".join([f"{val:4.2f}" for val in row])
        logger.info(row_str)

    # Generate detailed report
    if args.report:
        report_path = Path(args.report)
        report_path.parent.mkdir(parents=True, exist_ok=True)

        builder = EnsembleBuilder()
        report = builder.generate_report(analysis)

        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)

        logger.info(f"\nDetailed report saved to: {report_path}")

    # Save ensemble configuration
    ensemble_config_path = strategy_file.parent / f"{args.name.replace(' ', '_')}_config.json"

    ensemble_data = {
        "name": ensemble.name,
        "created_at": ensemble.created_at.isoformat(),
        "aggregation_method": ensemble.aggregation_method,
        "strategies": [
            {
                "name": strat.name,
                "weight": weight,
                "entry_logic": strat.entry_logic,
                "metrics": {
                    "sharpe_ratio": strat.backtest_metrics.sharpe_ratio,
                    "max_drawdown": strat.backtest_metrics.max_drawdown,
                    "win_rate": strat.backtest_metrics.win_rate,
                }
            }
            for strat, weight in zip(ensemble.strategies, ensemble.weights)
        ],
        "analysis": {
            "avg_correlation": analysis.avg_correlation,
            "diversity_score": analysis.diversity_score,
            "weight_concentration": analysis.weight_concentration,
            "expected_sharpe": analysis.expected_sharpe,
            "expected_return": analysis.expected_return,
            "expected_drawdown": analysis.expected_drawdown,
        }
    }

    with open(ensemble_config_path, 'w', encoding='utf-8') as f:
        json.dump(ensemble_data, f, indent=2)

    logger.info(f"Ensemble configuration saved to: {ensemble_config_path}")

    logger.info("\n" + "="*80)
    logger.info("ENSEMBLE CREATION COMPLETE")
    logger.info("="*80)


if __name__ == "__main__":
    main()
