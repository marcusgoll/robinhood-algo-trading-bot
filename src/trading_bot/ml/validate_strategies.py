#!/usr/bin/env python3
"""Strategy Validation Script

Validates ML-generated strategies using walk-forward analysis and
production readiness checks.

Usage:
    python -m trading_bot.ml.validate_strategies \
        --strategy-file ml_strategies/AAPL_20251103_201838.json \
        --span year

    python -m trading_bot.ml.validate_strategies \
        --strategy-dir ml_strategies/ \
        --min-sharpe 2.0
"""

import argparse
import json
import logging
import sys
from pathlib import Path

from trading_bot.auth import AlpacaAuth
from trading_bot.config import Config
from trading_bot.market_data.market_data_service import MarketDataService
from trading_bot.ml.backtesting.validator import StrategyValidator
from trading_bot.ml.config import BacktestConfig
from trading_bot.ml.models import MLStrategy, StrategyGene, StrategyMetrics, StrategyStatus, StrategyType

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

        # Store symbol separately for later use (not part of model)
        strategy._symbol = symbol  # Internal attribute for tracking

        strategies.append(strategy)

    logger.info(f"Loaded {len(strategies)} strategies from {file_path.name}")
    return strategies


def main():
    """Main validation entry point."""
    parser = argparse.ArgumentParser(description="Validate ML trading strategies")

    parser.add_argument("--strategy-file", type=str, help="Path to strategy JSON file")
    parser.add_argument("--strategy-dir", type=str, help="Directory containing strategy JSON files")
    parser.add_argument("--span", type=str, default="year", choices=["month", "3month", "year", "5year"], help="Historical data span")
    parser.add_argument("--min-sharpe", type=float, default=1.5, help="Minimum Sharpe ratio filter")
    parser.add_argument("--max-drawdown", type=float, default=0.20, help="Maximum drawdown filter")
    parser.add_argument("--output", type=str, help="Output file for validated strategies")

    args = parser.parse_args()

    # Determine strategy files to process
    strategy_files = []
    if args.strategy_file:
        strategy_files.append(Path(args.strategy_file))
    elif args.strategy_dir:
        strategy_dir = Path(args.strategy_dir)
        strategy_files = list(strategy_dir.glob("*.json"))
    else:
        logger.error("Must specify --strategy-file or --strategy-dir")
        parser.print_help()
        sys.exit(1)

    logger.info(f"{'='*80}")
    logger.info(f"STRATEGY VALIDATION")
    logger.info(f"{'='*80}")
    logger.info(f"Files to process: {len(strategy_files)}")
    logger.info(f"Validation span: {args.span}")
    logger.info(f"Min Sharpe: {args.min_sharpe}")
    logger.info(f"Max Drawdown: {args.max_drawdown}")
    logger.info(f"{'='*80}\n")

    # Initialize services
    config = Config.from_env_and_json()
    logger.info("Authenticating with Alpaca...")
    auth = AlpacaAuth(config)
    auth.login()
    market_data_service = MarketDataService(auth)

    # Initialize validator
    backtest_config = BacktestConfig()
    validator = StrategyValidator(backtest_config)

    # Process each file
    all_results = []
    passed_strategies = []

    for strategy_file in strategy_files:
        try:
            logger.info(f"\n{'='*80}")
            logger.info(f"Processing: {strategy_file.name}")
            logger.info(f"{'='*80}")

            # Load strategies
            strategies = load_strategies_from_json(strategy_file)

            # Get symbol from first strategy
            symbol = getattr(strategies[0], '_symbol', "UNKNOWN") if strategies else "UNKNOWN"

            # Fetch market data
            logger.info(f"Fetching {args.span} of data for {symbol}...")
            historical_data = market_data_service.get_historical_data(
                symbol=symbol,
                interval="day",
                span=args.span
            )
            logger.info(f"  Fetched {len(historical_data)} bars")

            # Validate each strategy
            for strategy in strategies:
                logger.info(f"\nValidating {strategy.name}...")

                try:
                    result = validator.validate(strategy, historical_data)
                    all_results.append(result)

                    if result.passed:
                        logger.info(f"  ✓ PASSED")
                        passed_strategies.append(strategy)
                    else:
                        logger.warning(f"  ✗ FAILED: {', '.join(result.failure_reasons)}")

                    # Display metrics
                    logger.info(f"  Backtest Sharpe: {result.backtest_metrics.sharpe_ratio:.2f}")
                    logger.info(f"  Walk-Forward Train Sharpe: {result.walk_forward_result.avg_train_sharpe:.2f}")
                    logger.info(f"  Walk-Forward Test Sharpe: {result.walk_forward_result.avg_test_sharpe:.2f}")
                    logger.info(f"  Degradation: {result.walk_forward_result.avg_degradation_pct:.1f}%")
                    logger.info(f"  Overfit: {'YES' if result.walk_forward_result.is_overfit else 'NO'}")

                except Exception as e:
                    logger.error(f"  Validation failed: {e}")
                    import traceback
                    traceback.print_exc()

        except Exception as e:
            logger.error(f"Failed to process {strategy_file.name}: {e}")
            import traceback
            traceback.print_exc()

    # Final summary
    logger.info(f"\n{'='*80}")
    logger.info("VALIDATION COMPLETE")
    logger.info(f"{'='*80}")
    logger.info(f"Total strategies tested: {len(all_results)}")
    logger.info(f"Passed validation: {len(passed_strategies)}")
    logger.info(f"Failed validation: {len(all_results) - len(passed_strategies)}")
    logger.info(f"Success rate: {len(passed_strategies) / len(all_results) * 100:.1f}%" if all_results else "N/A")

    if passed_strategies:
        logger.info(f"\nTop validated strategies:")
        sorted_strategies = sorted(passed_strategies, key=lambda s: s.backtest_metrics.sharpe_ratio, reverse=True)
        for i, strategy in enumerate(sorted_strategies[:5], 1):
            logger.info(f"  {i}. {strategy.name}: Sharpe={strategy.backtest_metrics.sharpe_ratio:.2f}, DD={strategy.backtest_metrics.max_drawdown:.1%}")

    # Save validated strategies
    if args.output and passed_strategies:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        validated_data = []
        for strategy in passed_strategies:
            validated_data.append({
                "name": strategy.name,
                "symbol": getattr(strategy, '_symbol', 'UNKNOWN'),
                "entry_logic": strategy.entry_logic,
                "gene": {
                    "tree": strategy.gene.tree if strategy.gene else "",
                    "complexity": strategy.gene.complexity_score() if strategy.gene else 0.0,
                },
                "metrics": {
                    "sharpe_ratio": float(strategy.backtest_metrics.sharpe_ratio),
                    "max_drawdown": float(strategy.backtest_metrics.max_drawdown),
                    "win_rate": float(strategy.backtest_metrics.win_rate),
                    "profit_factor": float(strategy.backtest_metrics.profit_factor),
                    "num_trades": int(strategy.backtest_metrics.num_trades),
                },
            })

        with open(output_path, 'w') as f:
            json.dump({
                "validated_count": len(validated_data),
                "validation_date": str(Path().cwd()),
                "strategies": validated_data,
            }, f, indent=2)

        logger.info(f"\nSaved {len(validated_data)} validated strategies to: {output_path}")


if __name__ == "__main__":
    main()
