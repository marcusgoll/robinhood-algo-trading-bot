"""LLM-guided strategy generator.

Uses OpenAI GPT-4 to generate interpretable trading strategies.
Integrates with existing trading_bot.llm.openai_client module.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from trading_bot.llm.openai_client import OpenAIClient
from trading_bot.ml.config import LLMConfig
from trading_bot.ml.models import (
    MLStrategy,
    StrategyStatus,
    StrategyType,
)

logger = logging.getLogger(__name__)


class LLMGuidedGenerator:
    """Generate trading strategies using LLM guidance.

    Leverages GPT-4 to create interpretable rule-based strategies:
    1. Analyze market regime
    2. Generate strategy ideas
    3. Convert to executable code
    4. Validate syntax and logic

    Example output:
        ```json
        {
            "name": "RSI Mean Reversion",
            "entry_conditions": [
                "RSI < 30",
                "Price below SMA(20)",
                "Volume > 1.5x average"
            ],
            "exit_conditions": [
                "RSI > 70",
                "Profit >= 2%",
                "Stop loss >= 3%"
            ]
        }
        ```
    """

    def __init__(self, config: LLMConfig) -> None:
        """Initialize LLM generator.

        Args:
            config: LLM configuration
        """
        self.config = config
        self.llm_client = OpenAIClient()

    def analyze_market_regime(self, historical_data: Any) -> str:
        """Analyze current market regime using LLM.

        Args:
            historical_data: Historical market data

        Returns:
            Market regime description (trending, ranging, volatile, etc.)
        """
        # TODO: Calculate market statistics
        # For now, return placeholder
        return "trending"

    def generate_strategies_from_llm(
        self, market_regime: str, num_strategies: int
    ) -> list[dict[str, Any]]:
        """Generate strategies using LLM.

        Args:
            market_regime: Current market regime
            num_strategies: Number of strategies to generate

        Returns:
            List of strategy definitions (JSON)
        """
        prompt = self.config.system_prompt_template.format(
            num_strategies=num_strategies,
            market_regime=market_regime,
        )

        try:
            response = self.llm_client.chat_completion(
                messages=[
                    {"role": "system", "content": prompt},
                    {
                        "role": "user",
                        "content": f"Generate {num_strategies} trading strategies for {market_regime} market conditions.",
                    },
                ],
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )

            # Parse JSON response
            content = response["choices"][0]["message"]["content"]
            strategies_json = json.loads(content)

            if isinstance(strategies_json, list):
                return strategies_json
            else:
                return [strategies_json]

        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            return []

    def validate_strategy(self, strategy_json: dict[str, Any]) -> bool:
        """Validate LLM-generated strategy.

        Args:
            strategy_json: Strategy definition

        Returns:
            True if valid
        """
        required_fields = ["name", "entry_conditions", "exit_conditions"]

        for field in required_fields:
            if field not in strategy_json:
                logger.warning(f"Missing required field: {field}")
                return False

        return True

    def json_to_strategy(self, strategy_json: dict[str, Any]) -> MLStrategy:
        """Convert JSON definition to MLStrategy object.

        Args:
            strategy_json: Strategy definition

        Returns:
            MLStrategy instance
        """
        entry_logic = " AND ".join(strategy_json.get("entry_conditions", []))
        exit_logic = " OR ".join(strategy_json.get("exit_conditions", []))

        strategy = MLStrategy(
            name=strategy_json.get("name", "LLM_Strategy"),
            type=StrategyType.LLM_GENERATED,
            status=StrategyStatus.GENERATED,
            entry_logic=entry_logic,
            exit_logic=exit_logic,
            parameters=strategy_json.get("risk_params", {}),
            llm_prompt=str(strategy_json),
            generation_config=self.config.__dict__,
        )

        return strategy

    def generate(
        self,
        num_strategies: int,
        historical_data: Any,
        config: dict[str, Any],
    ) -> list[MLStrategy]:
        """Generate strategies using LLM (IMLStrategyGenerator interface).

        Args:
            num_strategies: Number of strategies to generate
            historical_data: Historical market data
            config: Additional configuration

        Returns:
            List of generated strategies
        """
        # Analyze market regime
        if self.config.market_regime_analysis:
            market_regime = self.analyze_market_regime(historical_data)
        else:
            market_regime = "general"

        logger.info(
            f"Generating {num_strategies} LLM-guided strategies for {market_regime} market"
        )

        # Generate strategies from LLM
        strategies = []
        attempts = 0
        max_attempts = self.config.max_retries

        while len(strategies) < num_strategies and attempts < max_attempts:
            strategies_json = self.generate_strategies_from_llm(
                market_regime, num_strategies - len(strategies)
            )

            # Validate and convert
            for strategy_json in strategies_json:
                if self.validate_strategy(strategy_json):
                    strategy = self.json_to_strategy(strategy_json)
                    strategies.append(strategy)

            attempts += 1

        logger.info(
            f"Generated {len(strategies)} valid strategies after {attempts} attempts"
        )
        return strategies

    def mutate(self, strategy: MLStrategy) -> MLStrategy:
        """Mutate LLM strategy by asking LLM to create variant.

        Args:
            strategy: Strategy to mutate

        Returns:
            Mutated strategy
        """
        prompt = f"""Create a variant of this trading strategy:

{strategy.llm_prompt}

Make ONE significant change (different indicator, threshold, or logic).
Keep the same output format.
"""

        try:
            response = self.llm_client.chat_completion(
                messages=[
                    {"role": "system", "content": "You are a trading strategy expert."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.8,
                max_tokens=1000,
            )

            content = response["choices"][0]["message"]["content"]
            strategy_json = json.loads(content)

            if self.validate_strategy(strategy_json):
                mutated = self.json_to_strategy(strategy_json)
                mutated.name = f"{strategy.name}_mutated"
                return mutated

        except Exception as e:
            logger.error(f"Mutation failed: {e}")

        return strategy

    def crossover(
        self, strategy1: MLStrategy, strategy2: MLStrategy
    ) -> MLStrategy:
        """Combine two LLM strategies by asking LLM to merge them.

        Args:
            strategy1: First parent
            strategy2: Second parent

        Returns:
            Offspring strategy
        """
        prompt = f"""Combine these two trading strategies into one:

Strategy 1:
{strategy1.llm_prompt}

Strategy 2:
{strategy2.llm_prompt}

Create a hybrid that takes the best elements from both.
Keep the same output format.
"""

        try:
            response = self.llm_client.chat_completion(
                messages=[
                    {"role": "system", "content": "You are a trading strategy expert."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
                max_tokens=1500,
            )

            content = response["choices"][0]["message"]["content"]
            strategy_json = json.loads(content)

            if self.validate_strategy(strategy_json):
                offspring = self.json_to_strategy(strategy_json)
                offspring.name = f"LLM_Crossover"
                return offspring

        except Exception as e:
            logger.error(f"Crossover failed: {e}")

        return strategy1
