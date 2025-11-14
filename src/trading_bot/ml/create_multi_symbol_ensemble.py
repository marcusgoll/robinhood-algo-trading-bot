#!/usr/bin/env python3
"""Multi-Symbol Ensemble Creation

Combines top strategies from multiple symbols to create a diverse ensemble.

Usage:
    python -m trading_bot.ml.create_multi_symbol_ensemble \
        --strategy-dir ml_strategies/ \
        --symbols SPY QQQ NVDA TSLA \
        --strategies-per-symbol 2 \
        --method sharpe_weighted \
        --report diverse_ensemble_report.md
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
    """Load strategies from JSON file with feature extraction.

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

        # Extract features from tree string
        tree_str = gene_data.get("tree", "")
        features_used = set()

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
            name=f"{symbol}_{strat_data.get('name', 'Unknown')}",  # Prefix with symbol
            type=StrategyType(strat_data.get("type", "genetic_programming")),
            status=StrategyStatus(strat_data.get("status", "generated")),
            entry_logic=strat_data.get("entry_logic", ""),
            gene=gene,
            backtest_metrics=metrics,
        )

        # Store symbol
        strategy._symbol = symbol

        strategies.append(strategy)

    return strategies


def find_latest_strategy_file(directory: Path, symbol: str) -> Path | None:
    """Find the most recent strategy file for a symbol.

    Args:
        directory: Directory to search
        symbol: Symbol to find

    Returns:
        Path to latest file or None
    """
    pattern = f"{symbol}_*.json"
    files = list(directory.glob(pattern))

    if not files:
        return None

    # Sort by modification time (newest first)
    files.sort(key=lambda f: f.stat().st_mtime, reverse=True)

    return files[0]


def main():
    """Main multi-symbol ensemble creation entry point."""
    parser = argparse.ArgumentParser(description="Create diverse ensemble from multiple symbols")

    parser.add_argument("--strategy-dir", type=str, default="ml_strategies/",
                        help="Directory containing strategy JSON files")
    parser.add_argument("--symbols", nargs='+', required=True,
                        help="Symbols to include (e.g., SPY QQQ NVDA TSLA)")
    parser.add_argument("--strategies-per-symbol", type=int, default=2,
                        help="Number of best strategies to select from each symbol")
    parser.add_argument("--method", type=str, default="sharpe_weighted",
                        choices=["equal_weight", "sharpe_weighted", "inverse_variance"],
                        help="Weighting method")
    parser.add_argument("--report", type=str, help="Output report file (markdown)")
    parser.add_argument("--name", type=str, default="Multi_Symbol_Ensemble",
                        help="Ensemble name")
    parser.add_argument("--min-score", type=float, default=30.0,
                        help="Minimum strategy score threshold")

    args = parser.parse_args()

    logger.info("="*80)
    logger.info("MULTI-SYMBOL ENSEMBLE CREATION")
    logger.info("="*80)
    logger.info(f"Strategy directory: {args.strategy_dir}")
    logger.info(f"Symbols: {', '.join(args.symbols)}")
    logger.info(f"Strategies per symbol: {args.strategies_per_symbol}")
    logger.info(f"Weighting method: {args.method}")
    logger.info(f"Min score threshold: {args.min_score}")
    logger.info("="*80)

    strategy_dir = Path(args.strategy_dir)
    if not strategy_dir.exists():
        logger.error(f"Strategy directory not found: {strategy_dir}")
        sys.exit(1)

    # Load strategies from all symbols
    all_strategies = []
    symbol_strategies = {}

    for symbol in args.symbols:
        # Find latest strategy file for symbol
        strategy_file = find_latest_strategy_file(strategy_dir, symbol)

        if not strategy_file:
            logger.warning(f"No strategy file found for {symbol}, skipping")
            continue

        logger.info(f"\nLoading {symbol} strategies from: {strategy_file.name}")

        try:
            strategies = load_strategies_from_json(strategy_file)
            symbol_strategies[symbol] = strategies
            all_strategies.extend(strategies)

            logger.info(f"  Loaded {len(strategies)} strategies for {symbol}")

        except Exception as e:
            logger.error(f"Failed to load {symbol} strategies: {e}")
            continue

    if not all_strategies:
        logger.error("No strategies loaded from any symbol")
        sys.exit(1)

    logger.info(f"\n{'='*80}")
    logger.info(f"Total strategies loaded: {len(all_strategies)} from {len(symbol_strategies)} symbols")
    logger.info("="*80)

    # Rank all strategies across all symbols
    selector = StrategySelector()
    ranked = selector.rank_strategies(all_strategies)

    # Select top N from each symbol
    selected_strategies = []
    logger.info(f"\nSelecting top {args.strategies_per_symbol} from each symbol:")

    for symbol in args.symbols:
        if symbol not in symbol_strategies:
            continue

        # Get strategies for this symbol
        symbol_strats = symbol_strategies[symbol]

        # Rank them
        symbol_ranked = selector.rank_strategies(symbol_strats)

        # Filter by min score
        qualified = [s for s in symbol_ranked if s.composite_score >= args.min_score]

        # Take top N
        top_n = qualified[:args.strategies_per_symbol]

        logger.info(f"\n{symbol}:")
        for i, score in enumerate(top_n, 1):
            logger.info(
                f"  {i}. {score.strategy.name}: "
                f"Score={score.composite_score:.1f}, "
                f"Sharpe={score.strategy.backtest_metrics.sharpe_ratio:.2f}"
            )
            selected_strategies.append(score.strategy)

    if not selected_strategies:
        logger.error("No strategies met the minimum score threshold")
        sys.exit(1)

    logger.info(f"\nTotal selected: {len(selected_strategies)} strategies")

    # Create and analyze ensemble
    logger.info(f"\n{'='*80}")
    logger.info("CREATING DIVERSE ENSEMBLE")
    logger.info("="*80)

    builder = EnsembleBuilder()

    # Create ensemble
    ensemble = builder.create_ensemble(
        strategies=selected_strategies,
        method=args.method,
        name=args.name,
    )

    # Analyze
    analysis = builder.analyze_ensemble(ensemble)

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
    header = "      " + " ".join([f"S{i:2d}" for i in range(1, n + 1)])
    logger.info(header)

    for i, row in enumerate(analysis.correlation_matrix):
        row_str = f"S{i+1:2d}   " + " ".join([f"{val:4.2f}" for val in row])
        logger.info(row_str)

    # Symbol breakdown
    logger.info(f"\nSymbol Breakdown:")
    symbol_counts = {}
    for strat in ensemble.strategies:
        sym = getattr(strat, '_symbol', 'UNKNOWN')
        symbol_counts[sym] = symbol_counts.get(sym, 0) + 1

    for sym, count in symbol_counts.items():
        logger.info(f"  {sym}: {count} strategies ({count/len(ensemble.strategies)*100:.1f}%)")

    # Generate detailed report
    if args.report:
        report_path = Path(args.report)
        report_path.parent.mkdir(parents=True, exist_ok=True)

        report = builder.generate_report(analysis)

        # Add symbol breakdown to report
        report += "\n## Symbol Distribution\n\n"
        report += "| Symbol | Count | Percentage |\n"
        report += "|--------|-------|------------|\n"
        for sym, count in symbol_counts.items():
            pct = count / len(ensemble.strategies) * 100
            report += f"| {sym} | {count} | {pct:.1f}% |\n"
        report += "\n"

        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)

        logger.info(f"\nDetailed report saved to: {report_path}")

    # Save ensemble configuration
    ensemble_config_path = strategy_dir / f"{args.name.replace(' ', '_')}_config.json"

    ensemble_data = {
        "name": ensemble.name,
        "created_at": ensemble.created_at.isoformat(),
        "aggregation_method": ensemble.aggregation_method,
        "symbols": list(symbol_counts.keys()),
        "strategies": [
            {
                "name": strat.name,
                "symbol": getattr(strat, '_symbol', 'UNKNOWN'),
                "weight": weight,
                "entry_logic": strat.entry_logic,
                "metrics": {
                    "sharpe_ratio": float(strat.backtest_metrics.sharpe_ratio),
                    "max_drawdown": float(strat.backtest_metrics.max_drawdown),
                    "win_rate": float(strat.backtest_metrics.win_rate),
                }
            }
            for strat, weight in zip(ensemble.strategies, ensemble.weights)
        ],
        "analysis": {
            "avg_correlation": float(analysis.avg_correlation),
            "diversity_score": float(analysis.diversity_score),
            "weight_concentration": float(analysis.weight_concentration),
            "expected_sharpe": float(analysis.expected_sharpe),
            "expected_return": float(analysis.expected_return),
            "expected_drawdown": float(analysis.expected_drawdown),
        }
    }

    with open(ensemble_config_path, 'w', encoding='utf-8') as f:
        json.dump(ensemble_data, f, indent=2)

    logger.info(f"Ensemble configuration saved to: {ensemble_config_path}")

    logger.info("\n" + "="*80)
    logger.info("MULTI-SYMBOL ENSEMBLE CREATION COMPLETE")
    logger.info("="*80)

    # Final recommendations
    if analysis.diversity_score >= 50:
        logger.info("\n✓ SUCCESS: Ensemble has good diversity across symbols")
    else:
        logger.warning("\n⚠ WARNING: Ensemble diversity is still low despite using multiple symbols")

    if len(symbol_counts) >= 3:
        logger.info(f"✓ SUCCESS: Ensemble includes {len(symbol_counts)} different symbols")
    else:
        logger.warning(f"⚠ WARNING: Ensemble only includes {len(symbol_counts)} symbols - consider adding more")


if __name__ == "__main__":
    main()
