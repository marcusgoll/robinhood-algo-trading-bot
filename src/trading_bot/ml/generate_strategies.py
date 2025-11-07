#!/usr/bin/env python3
"""ML Strategy Generation - Production Script

Generates trading strategies using genetic programming with real market data.
Uses existing infrastructure (MarketDataService, FeatureExtractor) following DRY.

Usage:
    python -m trading_bot.ml.generate_strategies --symbol AAPL
    python -m trading_bot.ml.generate_strategies --from-watchlist --limit 5
    python -m trading_bot.ml.generate_strategies --symbol SPY --generations 20
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

from trading_bot.auth.robinhood_auth import RobinhoodAuth
from trading_bot.config import Config
from trading_bot.market_data.market_data_service import MarketDataService
from trading_bot.ml.config import MLConfig
from trading_bot.ml.features import FeatureExtractor
from trading_bot.ml.generators import GeneticProgrammingGenerator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


class MLStrategyGenerator:
    """Main orchestrator for ML strategy generation with real market data."""

    def __init__(self, ml_config: MLConfig | None = None):
        """Initialize generator with existing infrastructure.

        Args:
            ml_config: Optional ML configuration (uses defaults if not provided)
        """
        self.ml_config = ml_config or MLConfig()

        # Load config for auth (DRY - reuse existing infrastructure)
        config = Config.from_env_and_json()

        # Initialize market data service (DRY - reuse existing auth)
        logger.info("Authenticating with Robinhood...")
        self.auth = RobinhoodAuth(config)
        self.auth.login()

        self.market_data_service = MarketDataService(self.auth)

        # Initialize ML components
        self.feature_extractor = FeatureExtractor()
        self.gp_generator = GeneticProgrammingGenerator(self.ml_config.gp_config)

    def get_watchlist_symbols(self, limit: int | None = None) -> list[str]:
        """Get symbols from config watchlist (DRY).

        Args:
            limit: Optional limit on number of symbols

        Returns:
            List of stock symbols
        """
        # Load config directly (DRY)
        with open("config.json", "r") as f:
            config = json.load(f)

        symbols = config.get("momentum_scanning", {}).get("symbols", [])

        if not symbols:
            logger.warning("No symbols in momentum_scanning.symbols, using defaults")
            symbols = ["SPY", "QQQ", "AAPL"]

        if limit:
            symbols = symbols[:limit]

        logger.info(f"Loaded {len(symbols)} symbols from watchlist")
        return symbols

    def fetch_market_data(self, symbol: str, span: str = "year") -> dict:
        """Fetch historical market data using existing service (DRY).

        Args:
            symbol: Stock symbol
            span: Time span (day, week, month, 3month, year, 5year)

        Returns:
            Dict with symbol and DataFrame
        """
        logger.info(f"Fetching {span} of data for {symbol}...")

        try:
            df = self.market_data_service.get_historical_data(
                symbol=symbol,
                interval="day",
                span=span
            )

            logger.info(f"  Fetched {len(df)} bars ({df['date'].min()} to {df['date'].max()})")

            return {"symbol": symbol, "data": df}

        except Exception as e:
            logger.error(f"  Failed to fetch {symbol}: {e}")
            return None

    def generate_strategies(
        self,
        symbol: str,
        num_strategies: int = 5,
        span: str = "year"
    ) -> list:
        """Generate strategies for a symbol using existing infrastructure (DRY).

        Args:
            symbol: Stock symbol
            num_strategies: Number of strategies to generate
            span: Historical data span

        Returns:
            List of generated MLStrategy objects
        """
        logger.info(f"\n{'='*80}")
        logger.info(f"GENERATING STRATEGIES FOR {symbol}")
        logger.info(f"{'='*80}")

        # Step 1: Fetch market data (reuse MarketDataService)
        market_data = self.fetch_market_data(symbol, span)
        if not market_data:
            logger.error(f"Skipping {symbol} - no data available")
            return []

        df = market_data["data"]

        # Step 2: Extract features (reuse FeatureExtractor)
        logger.info(f"\nExtracting features for {symbol}...")
        try:
            feature_sets = self.feature_extractor.extract(df, symbol=symbol)
            logger.info(f"  Extracted {len(feature_sets)} feature vectors ({len(feature_sets[0].to_array())} dimensions)")

            # Show sample features
            latest = feature_sets[-1]
            logger.info(f"  Latest RSI: {latest.rsi_14:.2f}")
            logger.info(f"  Latest MACD: {latest.macd:.3f}")
            logger.info(f"  Latest Price/SMA20: {latest.price_to_sma20:.3f}")

        except Exception as e:
            logger.error(f"  Feature extraction failed: {e}")
            return []

        # Step 3: Generate strategies (reuse GeneticProgrammingGenerator)
        logger.info(f"\nGenerating {num_strategies} strategies...")
        logger.info(f"  Population: {self.ml_config.gp_config.population_size}")
        logger.info(f"  Generations: {self.ml_config.gp_config.num_generations}")

        try:
            strategies = self.gp_generator.generate(
                num_strategies=num_strategies,
                historical_data=df,
                config={"symbol": symbol}
            )

            logger.info(f"\n  Generated {len(strategies)} strategies")
            return strategies

        except Exception as e:
            logger.error(f"  Strategy generation failed: {e}")
            import traceback
            traceback.print_exc()
            return []

    def display_strategies(self, strategies: list, symbol: str):
        """Display generated strategies with metrics.

        Args:
            strategies: List of MLStrategy objects
            symbol: Stock symbol
        """
        if not strategies:
            logger.warning(f"No strategies generated for {symbol}")
            return

        logger.info(f"\n{'='*80}")
        logger.info(f"STRATEGIES FOR {symbol}")
        logger.info(f"{'='*80}")

        production_ready = 0

        for i, strategy in enumerate(strategies, 1):
            logger.info(f"\n{i}. {strategy.name}")
            logger.info(f"   Rule: {strategy.gene.tree if hasattr(strategy, 'gene') else strategy.entry_logic}")

            if hasattr(strategy, 'gene'):
                logger.info(f"   Complexity: {strategy.gene.complexity_score():.2f}")

            if strategy.backtest_metrics:
                metrics = strategy.backtest_metrics
                logger.info(f"   Sharpe: {metrics.sharpe_ratio:.2f}")
                logger.info(f"   Max DD: {metrics.max_drawdown:.1%}")
                logger.info(f"   Win Rate: {metrics.win_rate:.1%}")
                logger.info(f"   Fitness: {metrics.get_fitness_score():.1f}")

                is_ready = metrics.is_production_ready()
                logger.info(f"   Production Ready: {'YES' if is_ready else 'NO'}")

                if is_ready:
                    production_ready += 1

        logger.info(f"\n{'='*80}")
        logger.info(f"Summary: {production_ready}/{len(strategies)} production-ready ({production_ready/len(strategies)*100:.1f}%)")
        logger.info(f"{'='*80}")

    def save_strategies(self, strategies: list, symbol: str):
        """Save strategies to JSON file.

        Args:
            strategies: List of MLStrategy objects
            symbol: Stock symbol
        """
        if not strategies:
            return

        output_dir = Path("ml_strategies")
        output_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = output_dir / f"{symbol}_{timestamp}.json"

        # Convert strategies to dict
        strategies_data = []
        for strategy in strategies:
            data = {
                "name": strategy.name,
                "type": strategy.type.value,
                "status": strategy.status.value,
                "entry_logic": strategy.entry_logic,
                "created_at": strategy.created_at.isoformat() if strategy.created_at else None,
            }

            if hasattr(strategy, 'gene'):
                data["gene"] = {
                    "tree": strategy.gene.tree,
                    "depth": strategy.gene.depth,
                    "num_nodes": strategy.gene.num_nodes,
                    "complexity": strategy.gene.complexity_score(),
                }

            if strategy.backtest_metrics:
                # Convert numpy types to Python native types for JSON serialization
                data["metrics"] = {
                    "sharpe_ratio": float(strategy.backtest_metrics.sharpe_ratio),
                    "max_drawdown": float(strategy.backtest_metrics.max_drawdown),
                    "win_rate": float(strategy.backtest_metrics.win_rate),
                    "profit_factor": float(strategy.backtest_metrics.profit_factor),
                    "num_trades": int(strategy.backtest_metrics.num_trades) if strategy.backtest_metrics.num_trades else 0,
                    "total_return": float(strategy.backtest_metrics.total_return) if strategy.backtest_metrics.total_return else 0.0,
                    "fitness_score": float(strategy.backtest_metrics.get_fitness_score()),
                    "production_ready": bool(strategy.backtest_metrics.is_production_ready()),
                }

            strategies_data.append(data)

        # Save to file
        with open(filename, 'w') as f:
            json.dump({
                "symbol": symbol,
                "generated_at": timestamp,
                "num_strategies": len(strategies),
                "config": {
                    "population_size": self.ml_config.gp_config.population_size,
                    "num_generations": self.ml_config.gp_config.num_generations,
                },
                "strategies": strategies_data,
            }, f, indent=2)

        logger.info(f"\nSaved strategies to: {filename}")


def main():
    """Main entry point for ML strategy generation."""
    parser = argparse.ArgumentParser(description="Generate ML trading strategies")

    parser.add_argument("--symbol", type=str, help="Single symbol to generate strategies for")
    parser.add_argument("--from-watchlist", action="store_true", help="Use symbols from config watchlist")
    parser.add_argument("--limit", type=int, help="Limit number of symbols from watchlist")
    parser.add_argument("--num-strategies", type=int, default=5, help="Number of strategies to generate per symbol")
    parser.add_argument("--population", type=int, default=200, help="GP population size")
    parser.add_argument("--generations", type=int, default=10, help="Number of GP generations")
    parser.add_argument("--span", type=str, default="year", choices=["month", "3month", "year", "5year"], help="Historical data span")
    parser.add_argument("--save", action="store_true", help="Save strategies to JSON file")

    args = parser.parse_args()

    # Configure ML
    ml_config = MLConfig()
    ml_config.gp_config.population_size = args.population
    ml_config.gp_config.num_generations = args.generations

    # Initialize generator
    generator = MLStrategyGenerator(ml_config)

    # Determine symbols
    if args.symbol:
        symbols = [args.symbol.upper()]
    elif args.from_watchlist:
        symbols = generator.get_watchlist_symbols(args.limit)
    else:
        logger.error("Must specify --symbol or --from-watchlist")
        parser.print_help()
        sys.exit(1)

    logger.info(f"\n{'='*80}")
    logger.info(f"ML STRATEGY GENERATION")
    logger.info(f"{'='*80}")
    logger.info(f"Symbols: {', '.join(symbols)}")
    logger.info(f"Population: {args.population}")
    logger.info(f"Generations: {args.generations}")
    logger.info(f"Data span: {args.span}")
    logger.info(f"{'='*80}\n")

    # Generate strategies for each symbol
    all_results = {}

    for symbol in symbols:
        try:
            strategies = generator.generate_strategies(
                symbol=symbol,
                num_strategies=args.num_strategies,
                span=args.span
            )

            generator.display_strategies(strategies, symbol)

            if args.save:
                generator.save_strategies(strategies, symbol)

            all_results[symbol] = strategies

        except KeyboardInterrupt:
            logger.info("\nInterrupted by user")
            break
        except Exception as e:
            logger.error(f"Failed to generate for {symbol}: {e}")
            import traceback
            traceback.print_exc()

    # Final summary
    logger.info(f"\n{'='*80}")
    logger.info("GENERATION COMPLETE")
    logger.info(f"{'='*80}")

    total_strategies = sum(len(s) for s in all_results.values())
    total_production_ready = sum(
        sum(1 for strat in strategies if strat.backtest_metrics and strat.backtest_metrics.is_production_ready())
        for strategies in all_results.values()
    )

    logger.info(f"Symbols processed: {len(all_results)}")
    logger.info(f"Total strategies: {total_strategies}")
    logger.info(f"Production-ready: {total_production_ready}")

    if total_strategies > 0:
        logger.info(f"Success rate: {total_production_ready/total_strategies*100:.1f}%")


if __name__ == "__main__":
    main()
