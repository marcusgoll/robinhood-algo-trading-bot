#!/usr/bin/env python3
"""Test ML strategy generation with synthetic data.

This is a simplified test version that generates synthetic market data
instead of fetching from yfinance.
"""

import logging
from datetime import datetime, timedelta
import numpy as np
import pandas as pd

from trading_bot.ml.config import MLConfig
from trading_bot.ml.features import FeatureExtractor
from trading_bot.ml.generators import GeneticProgrammingGenerator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


def generate_synthetic_data(
    start_price: float = 100.0,
    num_days: int = 500,
    trend: float = 0.001,
    volatility: float = 0.02,
) -> pd.DataFrame:
    """Generate synthetic OHLCV data with realistic price movement.

    Args:
        start_price: Starting price
        num_days: Number of trading days
        trend: Daily trend (0.001 = 0.1% daily growth)
        volatility: Daily volatility (0.02 = 2% std dev)

    Returns:
        DataFrame with columns: date, open, high, low, close, volume
    """
    np.random.seed(42)

    # Generate dates
    start_date = datetime.now() - timedelta(days=num_days)
    dates = pd.date_range(start=start_date, periods=num_days, freq='D')

    # Generate returns with trend and volatility
    returns = np.random.normal(trend, volatility, num_days)
    close_prices = start_price * np.exp(np.cumsum(returns))

    # Generate OHLC from close prices
    daily_range = np.abs(np.random.normal(0, volatility * 0.5, num_days))

    high = close_prices * (1 + daily_range * 0.8)
    low = close_prices * (1 - daily_range * 0.8)
    open_prices = close_prices * (1 + np.random.normal(0, volatility * 0.3, num_days))

    # Generate volume with some randomness
    base_volume = 1_000_000
    volume = base_volume + np.random.randint(-200_000, 500_000, num_days)
    volume = np.maximum(volume, 100_000)  # Ensure positive

    df = pd.DataFrame({
        'date': dates,
        'open': open_prices,
        'high': high,
        'low': low,
        'close': close_prices,
        'volume': volume,
    })

    df.set_index('date', inplace=True)

    return df


def main():
    """Run simplified ML strategy generation test."""
    logger.info("=" * 80)
    logger.info("ML STRATEGY GENERATION TEST (SYNTHETIC DATA)")
    logger.info("=" * 80)

    # Step 1: Configuration
    logger.info("\n[1/4] Loading configuration...")

    config = MLConfig()
    config.gp_config.population_size = 50  # Very small for quick test
    config.gp_config.num_generations = 5

    logger.info(f"  - GP population: {config.gp_config.population_size}")
    logger.info(f"  - GP generations: {config.gp_config.num_generations}")

    # Step 2: Generate synthetic data
    logger.info("\n[2/4] Generating synthetic market data...")

    data = generate_synthetic_data(
        start_price=100.0,
        num_days=500,
        trend=0.0005,  # Slight uptrend
        volatility=0.02,
    )

    logger.info(f"  Generated {len(data)} days of data")
    logger.info(f"  Price range: ${data['close'].min():.2f} - ${data['close'].max():.2f}")
    logger.info(f"  Latest price: ${data['close'].iloc[-1]:.2f}")

    # Step 3: Extract features
    logger.info("\n[3/4] Extracting features...")

    extractor = FeatureExtractor()

    try:
        feature_sets = extractor.extract(data, symbol="TEST")
        logger.info(f"  Extracted {len(feature_sets)} feature vectors")
        logger.info(f"  Feature dimensions: {len(feature_sets[0].to_array())}")

        # Show sample features
        latest = feature_sets[-1]
        logger.info(f"\n  Latest feature values:")
        logger.info(f"    RSI: {latest.rsi_14:.2f}")
        logger.info(f"    MACD: {latest.macd:.3f}")
        logger.info(f"    Price/SMA20: {latest.price_to_sma20:.3f}")
        logger.info(f"    Volatility: {latest.volatility_20d:.3f}")
    except Exception as e:
        logger.error(f"  Feature extraction failed: {e}")
        logger.info("  Continuing with strategy generation anyway...")

    # Step 4: Generate strategies
    logger.info("\n[4/4] Generating strategies with Genetic Programming...")

    generator = GeneticProgrammingGenerator(config.gp_config)

    try:
        logger.info(f"  Evolving population of {config.gp_config.population_size}...")
        logger.info(f"  Running {config.gp_config.num_generations} generations...")

        strategies = generator.generate(
            num_strategies=5,
            historical_data=data,
            config={},
        )

        logger.info(f"\n  ✓ Generated {len(strategies)} strategies")

        # Display strategies
        logger.info("\n  Generated strategies:")
        for i, strategy in enumerate(strategies, 1):
            logger.info(f"\n  Strategy {i}: {strategy.name}")
            logger.info(f"    Rule: {strategy.gene.tree if hasattr(strategy, 'gene') else 'N/A'}")
            logger.info(f"    Complexity: {strategy.gene.complexity_score():.2f}" if hasattr(strategy, 'gene') else "")

            if strategy.backtest_metrics:
                metrics = strategy.backtest_metrics
                logger.info(f"    Sharpe: {metrics.sharpe_ratio:.2f}")
                logger.info(f"    Max DD: {metrics.max_drawdown:.1%}")
                logger.info(f"    Win Rate: {metrics.win_rate:.1%}")
                logger.info(f"    Fitness: {metrics.get_fitness_score():.1f}")
                logger.info(f"    Production Ready: {'YES' if metrics.is_production_ready() else 'NO'}")

    except Exception as e:
        logger.error(f"  Strategy generation failed: {e}")
        import traceback
        traceback.print_exc()
        return

    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("TEST COMPLETE")
    logger.info("=" * 80)

    if strategies:
        production_ready = sum(1 for s in strategies if s.backtest_metrics and s.backtest_metrics.is_production_ready())
        logger.info(f"\nResults:")
        logger.info(f"  Total strategies: {len(strategies)}")
        logger.info(f"  Production-ready: {production_ready}")
        logger.info(f"  Success rate: {production_ready / len(strategies) * 100:.1f}%")

    logger.info("\nNext steps:")
    logger.info("  1. Increase population_size and num_generations for better results")
    logger.info("  2. Use real market data instead of synthetic data")
    logger.info("  3. Implement full validation and ensemble creation")


if __name__ == "__main__":
    main()
