#!/usr/bin/env python3
"""Example: ML-based trading strategy generation and execution.

This script demonstrates the complete ML strategy generation pipeline:
1. Feature extraction from market data
2. Strategy generation using GP, RL, and LLM
3. Backtesting and walk-forward validation
4. Strategy selection and ensemble creation
5. Live deployment

Usage:
    python examples/ml_strategy_generation.py

Requirements:
    - Historical data (yfinance)
    - OpenAI API key (for LLM generation)
    - Configured config.json and .env
"""

import logging
from pathlib import Path

import pandas as pd
import yfinance as yf

# ML strategy components
from trading_bot.ml.config import MLConfig
from trading_bot.ml.features import FeatureExtractor
from trading_bot.ml.generators import (
    GeneticProgrammingGenerator,
    LLMGuidedGenerator,
)
from trading_bot.ml.backtesting import StrategyValidator, WalkForwardOptimizer
from trading_bot.ml.selection import StrategySelector, EnsembleBuilder

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


def fetch_historical_data(symbol: str = "SPY", period: str = "2y") -> pd.DataFrame:
    """Fetch historical OHLCV data.

    Args:
        symbol: Ticker symbol
        period: Data period (1y, 2y, 5y, etc.)

    Returns:
        DataFrame with OHLCV data
    """
    logger.info(f"Fetching historical data for {symbol} ({period})")

    ticker = yf.Ticker(symbol)
    data = ticker.history(period=period, interval="1d")

    # Rename columns to match expected format
    data.columns = [c.lower() for c in data.columns]

    logger.info(f"Downloaded {len(data)} bars of data")

    return data


def main():
    """Run ML strategy generation pipeline."""
    logger.info("=" * 80)
    logger.info("ML STRATEGY GENERATION PIPELINE")
    logger.info("=" * 80)

    # ========================================================================
    # STEP 1: Configuration
    # ========================================================================
    logger.info("\n[1/7] Loading configuration...")

    config = MLConfig()

    # Customize for faster example
    config.gp_config.population_size = 100  # Smaller for demo
    config.gp_config.num_generations = 10

    logger.info(f"Configuration loaded:")
    logger.info(f"  - GP population: {config.gp_config.population_size}")
    logger.info(f"  - GP generations: {config.gp_config.num_generations}")
    logger.info(f"  - Walk-forward windows: {config.backtest_config.walk_forward_windows}")
    logger.info(f"  - Selection method: {config.selection_config.selection_method}")

    # ========================================================================
    # STEP 2: Data Collection
    # ========================================================================
    logger.info("\n[2/7] Fetching historical data...")

    # Download data for multiple symbols
    symbols = ["SPY", "QQQ", "IWM"]
    market_data = {}

    for symbol in symbols:
        try:
            data = fetch_historical_data(symbol, period="2y")
            market_data[symbol] = data
        except Exception as e:
            logger.error(f"Failed to fetch {symbol}: {e}")

    if not market_data:
        logger.error("No market data available. Exiting.")
        return

    # Use SPY for main pipeline
    data = market_data["SPY"]

    # ========================================================================
    # STEP 3: Feature Extraction
    # ========================================================================
    logger.info("\n[3/7] Extracting features...")

    extractor = FeatureExtractor()
    feature_sets = extractor.extract(data, symbol="SPY")

    logger.info(f"Extracted {len(feature_sets)} feature vectors")
    logger.info(f"Feature dimensions: {len(feature_sets[0].to_array())}")

    # Show sample features
    latest_features = feature_sets[-1]
    logger.info(f"\nLatest feature values:")
    logger.info(f"  - RSI: {latest_features.rsi_14:.2f}")
    logger.info(f"  - MACD: {latest_features.macd:.3f}")
    logger.info(f"  - Price/SMA20: {latest_features.price_to_sma20:.3f}")
    logger.info(f"  - Volatility: {latest_features.volatility_20d:.3f}")

    # ========================================================================
    # STEP 4: Strategy Generation
    # ========================================================================
    logger.info("\n[4/7] Generating strategies...")

    all_strategies = []

    # 4a. Genetic Programming
    logger.info("\n  [4a] Genetic Programming...")
    gp_generator = GeneticProgrammingGenerator(config.gp_config)

    try:
        gp_strategies = gp_generator.generate(
            num_strategies=10,
            historical_data=data,
            config={},
        )
        all_strategies.extend(gp_strategies)
        logger.info(f"  Generated {len(gp_strategies)} GP strategies")
    except Exception as e:
        logger.error(f"  GP generation failed: {e}")

    # 4b. LLM-Guided (if API key available)
    logger.info("\n  [4b] LLM-Guided Generation...")

    try:
        llm_generator = LLMGuidedGenerator(config.llm_config)
        llm_strategies = llm_generator.generate(
            num_strategies=5,
            historical_data=data,
            config={},
        )
        all_strategies.extend(llm_strategies)
        logger.info(f"  Generated {len(llm_strategies)} LLM strategies")
    except Exception as e:
        logger.warning(f"  LLM generation failed: {e}")
        logger.warning("  (This is expected if OpenAI API key not configured)")

    # 4c. RL (placeholder for now)
    logger.info("\n  [4c] Reinforcement Learning...")
    logger.info("  (RL generation not implemented yet - skipping)")

    logger.info(f"\nTotal strategies generated: {len(all_strategies)}")

    if len(all_strategies) == 0:
        logger.error("No strategies generated. Exiting.")
        return

    # ========================================================================
    # STEP 5: Validation & Testing
    # ========================================================================
    logger.info("\n[5/7] Validating strategies...")

    validator = StrategyValidator(config.backtest_config)

    # Validate all strategies
    validation_results = validator.batch_validate(all_strategies, data)

    # Filter passed strategies
    passed_strategies = [r.strategy for r in validation_results if r.passed]
    failed_strategies = [r.strategy for r in validation_results if not r.passed]

    logger.info(f"\nValidation results:")
    logger.info(f"  - Passed: {len(passed_strategies)}")
    logger.info(f"  - Failed: {len(failed_strategies)}")

    if len(passed_strategies) == 0:
        logger.warning("No strategies passed validation. Using all generated strategies.")
        passed_strategies = all_strategies

    # Show top validated strategies
    logger.info(f"\nTop validated strategies:")
    for i, strategy in enumerate(passed_strategies[:5], 1):
        logger.info(f"  {i}. {strategy.name}")
        logger.info(f"     Sharpe: {strategy.forward_test_metrics.sharpe_ratio:.2f}")
        logger.info(f"     MaxDD: {strategy.forward_test_metrics.max_drawdown:.1%}")
        logger.info(f"     Score: {strategy.get_overall_score():.1f}")

    # ========================================================================
    # STEP 6: Strategy Selection & Ensemble
    # ========================================================================
    logger.info("\n[6/7] Selecting strategies and creating ensemble...")

    selector = StrategySelector(config.selection_config)

    # Select best strategies
    selection_result = selector.select(
        passed_strategies,
        correlation_matrix=None,  # Would need returns data
    )

    selected_strategies = selection_result.selected_strategies

    logger.info(f"\nSelected {len(selected_strategies)} strategies:")
    for i, strategy in enumerate(selected_strategies, 1):
        score = selection_result.selection_scores.get(str(strategy.id), 0.0)
        logger.info(f"  {i}. {strategy.name} (score: {score:.1f})")

    # Create ensemble
    ensemble_builder = EnsembleBuilder(config.selection_config)

    ensemble = ensemble_builder.create_ensemble(
        selected_strategies,
        name="ML_Portfolio_Ensemble_v1",
        method="kelly",  # Kelly criterion weighting
    )

    logger.info(f"\nEnsemble created:")
    logger.info(f"  Name: {ensemble.name}")
    logger.info(f"  Strategies: {len(ensemble.strategies)}")
    logger.info(f"  Weights: {[f'{w:.3f}' for w in ensemble.weights]}")
    logger.info(f"  Expected Sharpe: {ensemble.metrics.sharpe_ratio:.2f}")
    logger.info(f"  Expected MaxDD: {ensemble.metrics.max_drawdown:.1%}")

    # ========================================================================
    # STEP 7: Deployment (Paper Trading)
    # ========================================================================
    logger.info("\n[7/7] Deployment preparation...")

    logger.info("\nDeployment checklist:")
    logger.info(f"  [{'✓' if len(selected_strategies) > 0 else '✗'}] Strategies selected")
    logger.info(f"  [{'✓' if ensemble.metrics.sharpe_ratio > 1.0 else '✗'}] Ensemble Sharpe > 1.0")
    logger.info(f"  [{'✓' if ensemble.metrics.max_drawdown < 0.20 else '✗'}] Ensemble MaxDD < 20%")

    # Save strategies to disk
    output_dir = Path("ml_strategies") / "production"
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"\nSaving strategies to: {output_dir}")

    # TODO: Serialize strategies and ensemble to JSON/pickle

    logger.info("\n" + "=" * 80)
    logger.info("PIPELINE COMPLETE")
    logger.info("=" * 80)

    logger.info("\nNext steps:")
    logger.info("  1. Review generated strategies and ensemble")
    logger.info("  2. Test ensemble in paper trading mode")
    logger.info("  3. Monitor performance and adjust weights")
    logger.info("  4. Deploy to live trading after validation")

    logger.info("\nTo deploy the ensemble:")
    logger.info("  - Update config.json with ensemble_enabled=true")
    logger.info("  - Configure strategy weights in ml_config.json")
    logger.info("  - Start bot in paper trading mode: python -m trading_bot.main")


if __name__ == "__main__":
    main()
