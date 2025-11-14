#!/usr/bin/env python3
"""Strategy Selection Script

Ranks and selects ML strategies using multi-criteria scoring.

Usage:
    # Rank all strategies in a file
    python -m trading_bot.ml.select_strategies \
        --strategy-file ml_strategies/AAPL_20251103_201838.json \
        --report ranking_report.md

    # Select top 5 diverse strategies for ensemble
    python -m trading_bot.ml.select_strategies \
        --strategy-file ml_strategies/AAPL_20251103_201838.json \
        --select-ensemble 5 \
        --diversity-threshold 0.3
"""

import argparse
import json
import logging
import sys
from pathlib import Path

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
        gene = StrategyGene(
            tree=gene_data.get("tree", ""),
            depth=gene_data.get("depth", 0),
            num_nodes=gene_data.get("num_nodes", 0),
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

        # Store symbol separately for later use
        strategy._symbol = symbol

        strategies.append(strategy)

    logger.info(f"Loaded {len(strategies)} strategies from {file_path.name}")
    return strategies


def main():
    """Main selection entry point."""
    parser = argparse.ArgumentParser(description="Rank and select ML trading strategies")

    parser.add_argument("--strategy-file", type=str, required=True, help="Path to strategy JSON file")
    parser.add_argument("--report", type=str, help="Output report file (markdown)")
    parser.add_argument("--top-n", type=int, default=10, help="Number of top strategies to show in detail")
    parser.add_argument("--min-score", type=float, default=30.0, help="Minimum composite score threshold")

    # Ensemble selection
    parser.add_argument("--select-ensemble", type=int, help="Select N strategies for ensemble")
    parser.add_argument("--diversity-threshold", type=float, default=0.5, help="Diversity threshold for ensemble (0-1)")

    # Scoring weights
    parser.add_argument("--performance-weight", type=float, default=0.40, help="Weight for performance (0-1)")
    parser.add_argument("--robustness-weight", type=float, default=0.40, help="Weight for robustness (0-1)")
    parser.add_argument("--simplicity-weight", type=float, default=0.20, help="Weight for simplicity (0-1)")

    args = parser.parse_args()

    logger.info("="*80)
    logger.info("STRATEGY SELECTION")
    logger.info("="*80)
    logger.info(f"Input file: {args.strategy_file}")
    logger.info(f"Performance weight: {args.performance_weight:.0%}")
    logger.info(f"Robustness weight: {args.robustness_weight:.0%}")
    logger.info(f"Simplicity weight: {args.simplicity_weight:.0%}")
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

    # Initialize selector
    selector = StrategySelector(
        performance_weight=args.performance_weight,
        robustness_weight=args.robustness_weight,
        simplicity_weight=args.simplicity_weight,
    )

    # Rank strategies
    # Note: No validation_results provided, will use backtest metrics only
    ranked = selector.rank_strategies(strategies)

    # Display rankings
    logger.info("\nTop Strategies by Composite Score:")
    logger.info("-" * 80)

    for i, score in enumerate(ranked[:args.top_n], 1):
        logger.info(
            f"{i}. {score.strategy.name}: "
            f"Score={score.composite_score:.1f} "
            f"(Perf={score.performance_score:.1f}, "
            f"Robust={score.robustness_score:.1f}, "
            f"Simple={score.simplicity_score:.1f})"
        )

    # Filter by minimum score
    qualified = [s for s in ranked if s.composite_score >= args.min_score]
    logger.info(f"\n{len(qualified)}/{len(ranked)} strategies meet minimum score threshold ({args.min_score:.1f})")

    # Ensemble selection if requested
    if args.select_ensemble:
        logger.info(f"\n{'='*80}")
        logger.info(f"ENSEMBLE SELECTION: Top {args.select_ensemble} diverse strategies")
        logger.info(f"{'='*80}")

        ensemble_strategies = selector.select_for_ensemble(
            ranked,
            n=args.select_ensemble,
            min_score=args.min_score,
            diversity_threshold=args.diversity_threshold,
        )

        if ensemble_strategies:
            logger.info(f"\nSelected {len(ensemble_strategies)} strategies for ensemble:")
            for i, score in enumerate(ensemble_strategies, 1):
                logger.info(
                    f"  {i}. {score.strategy.name}: "
                    f"Score={score.composite_score:.1f}"
                )
        else:
            logger.warning("No strategies qualified for ensemble")

    # Generate detailed report
    if args.report:
        report_path = Path(args.report)
        report_path.parent.mkdir(parents=True, exist_ok=True)

        report = selector.generate_report(ranked, top_n=args.top_n)

        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)

        logger.info(f"\nDetailed report saved to: {report_path}")

    logger.info("\n" + "="*80)
    logger.info("SELECTION COMPLETE")
    logger.info("="*80)


if __name__ == "__main__":
    main()
