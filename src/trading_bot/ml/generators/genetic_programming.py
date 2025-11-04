"""Genetic programming strategy generator.

Evolves trading rules as syntax trees using genetic algorithms.
Uses gplearn library as foundation with custom fitness functions.
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable

import numpy as np
from numpy.typing import NDArray

from trading_bot.ml.config import GeneticProgrammingConfig
from trading_bot.ml.models import (
    MLStrategy,
    StrategyGene,
    StrategyMetrics,
    StrategyStatus,
    StrategyType,
)

logger = logging.getLogger(__name__)


@dataclass
class GPNode:
    """Node in genetic programming syntax tree.

    Attributes:
        type: 'function' or 'terminal'
        value: Function name or terminal value
        children: Child nodes (for functions)
        depth: Depth in tree (0=root)
    """

    type: str  # 'function' or 'terminal'
    value: str | float  # Function name or terminal value
    children: list[GPNode] | None = None
    depth: int = 0

    def evaluate(self, features: dict[str, float]) -> float:
        """Evaluate node recursively.

        Args:
            features: Feature dictionary

        Returns:
            Evaluation result
        """
        if self.type == "terminal":
            if isinstance(self.value, str):
                # Feature reference
                return features.get(self.value, 0.0)
            else:
                # Constant
                return float(self.value)

        # Function node
        if self.children is None:
            return 0.0

        # Evaluate children
        child_vals = [child.evaluate(features) for child in self.children]

        # Apply function
        func_name = str(self.value)
        try:
            if func_name == "add":
                return child_vals[0] + child_vals[1]
            elif func_name == "sub":
                return child_vals[0] - child_vals[1]
            elif func_name == "mul":
                return child_vals[0] * child_vals[1]
            elif func_name == "div":
                return child_vals[0] / (child_vals[1] + 1e-9)  # Protected division
            elif func_name == "sqrt":
                return np.sqrt(abs(child_vals[0]))  # Protected sqrt
            elif func_name == "abs":
                return abs(child_vals[0])
            elif func_name == "log":
                return np.log(abs(child_vals[0]) + 1e-9)  # Protected log
            elif func_name == "exp":
                return np.exp(np.clip(child_vals[0], -10, 10))  # Clipped exp
            elif func_name == "max":
                return max(child_vals[0], child_vals[1])
            elif func_name == "min":
                return min(child_vals[0], child_vals[1])
            elif func_name == "gt":
                return 1.0 if child_vals[0] > child_vals[1] else 0.0
            elif func_name == "lt":
                return 1.0 if child_vals[0] < child_vals[1] else 0.0
            elif func_name == "gte":
                return 1.0 if child_vals[0] >= child_vals[1] else 0.0
            elif func_name == "lte":
                return 1.0 if child_vals[0] <= child_vals[1] else 0.0
            elif func_name == "and":
                return 1.0 if child_vals[0] > 0.5 and child_vals[1] > 0.5 else 0.0
            elif func_name == "or":
                return 1.0 if child_vals[0] > 0.5 or child_vals[1] > 0.5 else 0.0
            elif func_name == "not":
                return 0.0 if child_vals[0] > 0.5 else 1.0
            else:
                return 0.0
        except (ZeroDivisionError, OverflowError, ValueError):
            return 0.0

    def to_string(self) -> str:
        """Convert tree to string representation."""
        if self.type == "terminal":
            return str(self.value)

        if self.children is None:
            return str(self.value)

        child_strs = [child.to_string() for child in self.children]
        return f"({self.value} {' '.join(child_strs)})"

    def count_nodes(self) -> int:
        """Count total nodes in subtree."""
        if self.type == "terminal":
            return 1

        if self.children is None:
            return 1

        return 1 + sum(child.count_nodes() for child in self.children)

    def get_depth(self) -> int:
        """Get maximum depth of subtree."""
        if self.type == "terminal":
            return 0

        if self.children is None:
            return 0

        return 1 + max(child.get_depth() for child in self.children)


class GeneticProgrammingGenerator:
    """Generate trading strategies using genetic programming.

    Evolves syntax trees representing trading rules:
    - Entry rules: Boolean expressions (buy when true)
    - Exit rules: Boolean expressions (sell when true)

    Example evolved rule:
        (and (gt (div close (sma close 20)) 1.02) (gt rsi 30))
        → Buy when price > SMA(20) * 1.02 AND RSI > 30

    Usage:
        ```python
        config = GeneticProgrammingConfig(
            population_size=1000,
            num_generations=50
        )
        generator = GeneticProgrammingGenerator(config)
        strategies = generator.generate(
            num_strategies=10,
            historical_data=data,
            config={}
        )
        ```
    """

    def __init__(self, config: GeneticProgrammingConfig) -> None:
        """Initialize GP generator.

        Args:
            config: GP configuration
        """
        self.config = config
        self.function_arities = {
            "add": 2,
            "sub": 2,
            "mul": 2,
            "div": 2,
            "max": 2,
            "min": 2,
            "gt": 2,
            "lt": 2,
            "gte": 2,
            "lte": 2,
            "and": 2,
            "or": 2,
            "sqrt": 1,
            "abs": 1,
            "log": 1,
            "exp": 1,
            "not": 1,
        }
        self.population: list[tuple[GPNode, float]] = []  # (tree, fitness)

    def create_random_tree(
        self, max_depth: int, method: str = "grow"
    ) -> GPNode:
        """Create random syntax tree.

        Args:
            max_depth: Maximum tree depth
            method: 'grow' (variable depth) or 'full' (exact depth)

        Returns:
            Root node of random tree
        """
        if max_depth == 0 or (method == "grow" and random.random() < 0.3):
            # Create terminal
            if random.random() < 0.7:
                # Feature reference
                terminal = random.choice(self.config.terminal_set)
                return GPNode(type="terminal", value=terminal)
            else:
                # Constant
                const = random.uniform(-1.0, 1.0)
                return GPNode(type="terminal", value=const)

        # Create function node
        func = random.choice(self.config.function_set)
        arity = self.function_arities.get(func, 2)

        children = [
            self.create_random_tree(max_depth - 1, method) for _ in range(arity)
        ]

        return GPNode(type="function", value=func, children=children)

    def initialize_population(self) -> None:
        """Initialize random population using ramped half-and-half."""
        self.population = []

        # Half with 'grow', half with 'full'
        for i in range(self.config.population_size):
            depth = random.randint(2, self.config.max_tree_depth)
            method = "grow" if i < self.config.population_size // 2 else "full"

            tree = self.create_random_tree(depth, method)
            self.population.append((tree, 0.0))  # Fitness starts at 0

        logger.info(f"Initialized population of {len(self.population)} trees")

    def evaluate_fitness(
        self,
        tree: GPNode,
        historical_data: Any,
    ) -> float:
        """Evaluate strategy fitness on historical data.

        Args:
            tree: Strategy tree to evaluate
            historical_data: Historical market data

        Returns:
            Fitness score (higher is better)
        """
        # TODO: Implement full backtest
        # For now, return random fitness
        return random.random()

    def tournament_selection(self) -> GPNode:
        """Select parent using tournament selection.

        Returns:
            Selected tree
        """
        tournament = random.sample(self.population, self.config.tournament_size)
        winner = max(tournament, key=lambda x: x[1])  # Max fitness
        return winner[0]

    def crossover(self, parent1: GPNode, parent2: GPNode) -> GPNode:
        """Perform subtree crossover.

        Args:
            parent1: First parent tree
            parent2: Second parent tree

        Returns:
            Offspring tree
        """
        # Deep copy parent1
        offspring = self._copy_tree(parent1)

        # Select random subtree in offspring
        offspring_nodes = self._get_all_nodes(offspring)
        if not offspring_nodes:
            return offspring

        crossover_point = random.choice(offspring_nodes)

        # Select random subtree from parent2
        parent2_nodes = self._get_all_nodes(parent2)
        if not parent2_nodes:
            return offspring

        subtree = random.choice(parent2_nodes)

        # Replace subtree
        self._replace_subtree(offspring, crossover_point, self._copy_tree(subtree))

        return offspring

    def mutate(self, tree: GPNode) -> GPNode:
        """Mutate tree by replacing random subtree.

        Args:
            tree: Tree to mutate

        Returns:
            Mutated tree
        """
        # Deep copy
        mutated = self._copy_tree(tree)

        # Select random node
        nodes = self._get_all_nodes(mutated)
        if not nodes:
            return mutated

        mutation_point = random.choice(nodes)

        # Replace with random subtree
        new_subtree = self.create_random_tree(max_depth=3, method="grow")
        self._replace_subtree(mutated, mutation_point, new_subtree)

        return mutated

    def _copy_tree(self, node: GPNode) -> GPNode:
        """Deep copy tree."""
        if node.type == "terminal":
            return GPNode(
                type=node.type,
                value=node.value,
                depth=node.depth,
            )

        children_copy = (
            [self._copy_tree(child) for child in node.children]
            if node.children
            else None
        )

        return GPNode(
            type=node.type,
            value=node.value,
            children=children_copy,
            depth=node.depth,
        )

    def _get_all_nodes(self, node: GPNode) -> list[GPNode]:
        """Get all nodes in tree (DFS)."""
        nodes = [node]

        if node.children:
            for child in node.children:
                nodes.extend(self._get_all_nodes(child))

        return nodes

    def _replace_subtree(
        self, tree: GPNode, target: GPNode, replacement: GPNode
    ) -> None:
        """Replace target subtree with replacement (in-place)."""
        # This is a simplified version - proper implementation needs parent tracking
        # For now, just modify target node directly
        target.type = replacement.type
        target.value = replacement.value
        target.children = replacement.children

    def evolve(self, historical_data: Any) -> list[MLStrategy]:
        """Run evolution loop.

        Args:
            historical_data: Historical market data for fitness evaluation

        Returns:
            List of best strategies
        """
        logger.info(
            f"Starting GP evolution: {self.config.num_generations} generations"
        )

        self.initialize_population()

        for generation in range(self.config.num_generations):
            # Evaluate fitness
            for i, (tree, _) in enumerate(self.population):
                fitness = self.evaluate_fitness(tree, historical_data)
                self.population[i] = (tree, fitness)

            # Sort by fitness
            self.population.sort(key=lambda x: x[1], reverse=True)

            # Log progress
            best_fitness = self.population[0][1]
            avg_fitness = sum(f for _, f in self.population) / len(self.population)
            logger.info(
                f"Generation {generation + 1}: "
                f"Best={best_fitness:.4f}, Avg={avg_fitness:.4f}"
            )

            # Create next generation
            next_population = []

            # Elitism: Keep top performers
            elite_size = int(self.config.elitism_pct * self.config.population_size)
            next_population.extend(self.population[:elite_size])

            # Fill rest with offspring
            while len(next_population) < self.config.population_size:
                if random.random() < self.config.crossover_rate:
                    # Crossover
                    parent1 = self.tournament_selection()
                    parent2 = self.tournament_selection()
                    offspring = self.crossover(parent1, parent2)
                else:
                    # Reproduction
                    offspring = self._copy_tree(self.tournament_selection())

                # Mutation
                if random.random() < self.config.mutation_rate:
                    offspring = self.mutate(offspring)

                next_population.append((offspring, 0.0))

            self.population = next_population

        # Convert top strategies to MLStrategy objects
        top_n = min(20, len(self.population))
        strategies = []

        for i in range(top_n):
            tree, fitness = self.population[i]

            gene = StrategyGene(
                tree=tree.to_string(),
                depth=tree.get_depth(),
                num_nodes=tree.count_nodes(),
            )

            strategy = MLStrategy(
                name=f"GP_Strategy_{i + 1}",
                type=StrategyType.GENETIC_PROGRAMMING,
                status=StrategyStatus.GENERATED,
                entry_logic=tree.to_string(),
                gene=gene,
                backtest_metrics=StrategyMetrics(
                    sharpe_ratio=fitness,  # Placeholder
                ),
                generation_config=self.config.__dict__,
                complexity_score=gene.complexity_score(),
            )

            strategies.append(strategy)

        logger.info(f"Evolution complete. Generated {len(strategies)} strategies")
        return strategies

    def generate(
        self,
        num_strategies: int,
        historical_data: Any,
        config: dict[str, Any],
    ) -> list[MLStrategy]:
        """Generate strategies (IMLStrategyGenerator interface).

        Args:
            num_strategies: Number of strategies to generate
            historical_data: Historical market data
            config: Additional configuration

        Returns:
            List of generated strategies
        """
        strategies = self.evolve(historical_data)
        return strategies[:num_strategies]

    def mutate(self, strategy: MLStrategy) -> MLStrategy:
        """Mutate existing strategy (IMLStrategyGenerator interface).

        Args:
            strategy: Strategy to mutate

        Returns:
            Mutated strategy
        """
        # Parse tree from string
        # TODO: Implement tree parsing
        # For now, create random mutation
        tree = self.create_random_tree(max_depth=4, method="grow")
        mutated_tree = self.mutate(tree)

        gene = StrategyGene(
            tree=mutated_tree.to_string(),
            depth=mutated_tree.get_depth(),
            num_nodes=mutated_tree.count_nodes(),
        )

        mutated_strategy = MLStrategy(
            name=f"{strategy.name}_mutated",
            type=StrategyType.GENETIC_PROGRAMMING,
            status=StrategyStatus.GENERATED,
            entry_logic=mutated_tree.to_string(),
            gene=gene,
            generation_config=strategy.generation_config,
        )

        return mutated_strategy

    def crossover(self, strategy1: MLStrategy, strategy2: MLStrategy) -> MLStrategy:
        """Crossover two strategies (IMLStrategyGenerator interface).

        Args:
            strategy1: First parent
            strategy2: Second parent

        Returns:
            Offspring strategy
        """
        # TODO: Implement tree parsing and proper crossover
        # For now, return simple combination
        offspring_tree = self.create_random_tree(max_depth=4, method="grow")

        gene = StrategyGene(
            tree=offspring_tree.to_string(),
            depth=offspring_tree.get_depth(),
            num_nodes=offspring_tree.count_nodes(),
        )

        offspring = MLStrategy(
            name=f"GP_Crossover",
            type=StrategyType.GENETIC_PROGRAMMING,
            status=StrategyStatus.GENERATED,
            entry_logic=offspring_tree.to_string(),
            gene=gene,
            generation_config=strategy1.generation_config,
        )

        return offspring
