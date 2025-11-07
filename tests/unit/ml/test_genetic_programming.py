"""Tests for genetic programming strategy generator.

TDD approach: Write failing tests before implementation.
"""

import pytest
import numpy as np

from src.trading_bot.ml.generators.genetic_programming import (
    GPNode,
    GeneticProgrammingGenerator,
)
from src.trading_bot.ml.config import GeneticProgrammingConfig


class TestGPNode:
    """Tests for GPNode syntax tree node."""

    def test_terminal_node_evaluation_with_feature(self):
        """Test: Terminal node returns feature value.

        Given: Terminal node referencing 'close' feature
        When: Evaluating with features dict
        Then: Returns close price value
        """
        # Given
        node = GPNode(type="terminal", value="close", depth=0)
        features = {"close": 150.0, "rsi": 65.0}

        # When
        result = node.evaluate(features)

        # Then
        assert result == 150.0

    def test_terminal_node_evaluation_with_constant(self):
        """Test: Terminal node returns constant value.

        Given: Terminal node with numeric constant
        When: Evaluating
        Then: Returns constant value
        """
        # Given
        node = GPNode(type="terminal", value=42.5, depth=0)
        features = {}

        # When
        result = node.evaluate(features)

        # Then
        assert result == 42.5

    def test_terminal_node_missing_feature_returns_zero(self):
        """Test: Terminal node returns 0.0 for missing feature.

        Given: Terminal node referencing missing feature
        When: Evaluating with incomplete features dict
        Then: Returns 0.0 (default value)
        """
        # Given
        node = GPNode(type="terminal", value="volume", depth=0)
        features = {"close": 150.0}  # volume missing

        # When
        result = node.evaluate(features)

        # Then
        assert result == 0.0

    def test_add_function_evaluation(self):
        """Test: Add function returns sum of children.

        Given: Add node with two constant children
        When: Evaluating
        Then: Returns sum
        """
        # Given: (add 10 20) = 30
        child1 = GPNode(type="terminal", value=10.0, depth=1)
        child2 = GPNode(type="terminal", value=20.0, depth=1)
        add_node = GPNode(
            type="function", value="add", children=[child1, child2], depth=0
        )

        # When
        result = add_node.evaluate({})

        # Then
        assert result == 30.0

    def test_sub_function_evaluation(self):
        """Test: Sub function returns difference.

        Given: Sub node with two constants
        When: Evaluating
        Then: Returns difference
        """
        # Given: (sub 50 20) = 30
        child1 = GPNode(type="terminal", value=50.0, depth=1)
        child2 = GPNode(type="terminal", value=20.0, depth=1)
        sub_node = GPNode(
            type="function", value="sub", children=[child1, child2], depth=0
        )

        # When
        result = sub_node.evaluate({})

        # Then
        assert result == 30.0

    def test_mul_function_evaluation(self):
        """Test: Mul function returns product.

        Given: Mul node with two constants
        When: Evaluating
        Then: Returns product
        """
        # Given: (mul 5 6) = 30
        child1 = GPNode(type="terminal", value=5.0, depth=1)
        child2 = GPNode(type="terminal", value=6.0, depth=1)
        mul_node = GPNode(
            type="function", value="mul", children=[child1, child2], depth=0
        )

        # When
        result = mul_node.evaluate({})

        # Then
        assert result == 30.0

    def test_div_function_protected_division(self):
        """Test: Div function protects against division by zero.

        Given: Div node with zero divisor
        When: Evaluating
        Then: Returns result using protected division (adds epsilon)
        """
        # Given: (div 10 0) with protected division
        child1 = GPNode(type="terminal", value=10.0, depth=1)
        child2 = GPNode(type="terminal", value=0.0, depth=1)
        div_node = GPNode(
            type="function", value="div", children=[child1, child2], depth=0
        )

        # When
        result = div_node.evaluate({})

        # Then: Should not raise error, returns large finite value
        assert np.isfinite(result)
        assert result > 0  # Positive because 10 / epsilon

    def test_sqrt_function_protected_sqrt(self):
        """Test: Sqrt function protects against negative input.

        Given: Sqrt node with negative value
        When: Evaluating
        Then: Returns sqrt of absolute value
        """
        # Given: (sqrt -25) = sqrt(25) = 5
        child = GPNode(type="terminal", value=-25.0, depth=1)
        sqrt_node = GPNode(type="function", value="sqrt", children=[child], depth=0)

        # When
        result = sqrt_node.evaluate({})

        # Then
        assert result == pytest.approx(5.0)

    def test_log_function_protected_log(self):
        """Test: Log function protects against log(0) and log(negative).

        Given: Log node with zero or negative value
        When: Evaluating
        Then: Returns log of (abs(value) + epsilon)
        """
        # Given: (log 0) with protected log
        child = GPNode(type="terminal", value=0.0, depth=1)
        log_node = GPNode(type="function", value="log", children=[child], depth=0)

        # When
        result = log_node.evaluate({})

        # Then: Should return finite value (log of small epsilon)
        assert np.isfinite(result)
        assert result < 0  # log of small number is negative

    def test_exp_function_clipped_exp(self):
        """Test: Exp function clips input to prevent overflow.

        Given: Exp node with large value (>10)
        When: Evaluating
        Then: Returns exp of clipped value
        """
        # Given: (exp 100) clipped to exp(10)
        child = GPNode(type="terminal", value=100.0, depth=1)
        exp_node = GPNode(type="function", value="exp", children=[child], depth=0)

        # When
        result = exp_node.evaluate({})

        # Then: Should equal exp(10) (clipped)
        assert result == pytest.approx(np.exp(10))
        assert np.isfinite(result)

    def test_max_function_evaluation(self):
        """Test: Max function returns maximum of children.

        Given: Max node with two values
        When: Evaluating
        Then: Returns maximum value
        """
        # Given: (max 15 25) = 25
        child1 = GPNode(type="terminal", value=15.0, depth=1)
        child2 = GPNode(type="terminal", value=25.0, depth=1)
        max_node = GPNode(
            type="function", value="max", children=[child1, child2], depth=0
        )

        # When
        result = max_node.evaluate({})

        # Then
        assert result == 25.0

    def test_gt_function_comparison(self):
        """Test: Greater-than function returns 1.0 or 0.0.

        Given: GT node comparing two values
        When: Evaluating
        Then: Returns 1.0 if true, 0.0 if false
        """
        # Given: (gt 30 20) = 1.0
        child1 = GPNode(type="terminal", value=30.0, depth=1)
        child2 = GPNode(type="terminal", value=20.0, depth=1)
        gt_node = GPNode(
            type="function", value="gt", children=[child1, child2], depth=0
        )

        # When
        result = gt_node.evaluate({})

        # Then
        assert result == 1.0

        # Given: (gt 10 20) = 0.0
        child1_false = GPNode(type="terminal", value=10.0, depth=1)
        gt_node_false = GPNode(
            type="function", value="gt", children=[child1_false, child2], depth=0
        )

        # When
        result_false = gt_node_false.evaluate({})

        # Then
        assert result_false == 0.0

    def test_and_function_boolean_logic(self):
        """Test: And function returns 1.0 if both > 0.5.

        Given: And node with two boolean values
        When: Evaluating
        Then: Returns 1.0 if both > 0.5, else 0.0
        """
        # Given: (and 1.0 1.0) = 1.0
        child1 = GPNode(type="terminal", value=1.0, depth=1)
        child2 = GPNode(type="terminal", value=1.0, depth=1)
        and_node = GPNode(
            type="function", value="and", children=[child1, child2], depth=0
        )

        # When
        result = and_node.evaluate({})

        # Then
        assert result == 1.0

        # Given: (and 1.0 0.0) = 0.0
        child2_false = GPNode(type="terminal", value=0.0, depth=1)
        and_node_false = GPNode(
            type="function", value="and", children=[child1, child2_false], depth=0
        )

        # When
        result_false = and_node_false.evaluate({})

        # Then
        assert result_false == 0.0

    def test_or_function_boolean_logic(self):
        """Test: Or function returns 1.0 if either > 0.5.

        Given: Or node with two boolean values
        When: Evaluating
        Then: Returns 1.0 if either > 0.5, else 0.0
        """
        # Given: (or 0.0 1.0) = 1.0
        child1 = GPNode(type="terminal", value=0.0, depth=1)
        child2 = GPNode(type="terminal", value=1.0, depth=1)
        or_node = GPNode(
            type="function", value="or", children=[child1, child2], depth=0
        )

        # When
        result = or_node.evaluate({})

        # Then
        assert result == 1.0

    def test_not_function_boolean_negation(self):
        """Test: Not function returns boolean negation.

        Given: Not node with boolean value
        When: Evaluating
        Then: Returns 0.0 if > 0.5, else 1.0
        """
        # Given: (not 1.0) = 0.0
        child = GPNode(type="terminal", value=1.0, depth=1)
        not_node = GPNode(type="function", value="not", children=[child], depth=0)

        # When
        result = not_node.evaluate({})

        # Then
        assert result == 0.0

        # Given: (not 0.0) = 1.0
        child_false = GPNode(type="terminal", value=0.0, depth=1)
        not_node_true = GPNode(
            type="function", value="not", children=[child_false], depth=0
        )

        # When
        result_true = not_node_true.evaluate({})

        # Then
        assert result_true == 1.0

    def test_nested_tree_evaluation(self):
        """Test: Nested tree evaluates correctly.

        Given: Complex nested tree: (add (mul 2 3) (sub 10 5))
        When: Evaluating
        Then: Returns (2*3) + (10-5) = 6 + 5 = 11
        """
        # Given: (add (mul 2 3) (sub 10 5))
        mul_left = GPNode(
            type="function",
            value="mul",
            children=[
                GPNode(type="terminal", value=2.0, depth=2),
                GPNode(type="terminal", value=3.0, depth=2),
            ],
            depth=1,
        )

        sub_right = GPNode(
            type="function",
            value="sub",
            children=[
                GPNode(type="terminal", value=10.0, depth=2),
                GPNode(type="terminal", value=5.0, depth=2),
            ],
            depth=1,
        )

        add_root = GPNode(
            type="function", value="add", children=[mul_left, sub_right], depth=0
        )

        # When
        result = add_root.evaluate({})

        # Then
        assert result == 11.0

    def test_to_string_terminal_node(self):
        """Test: Terminal node converts to string correctly.

        Given: Terminal node with value
        When: Converting to string
        Then: Returns string representation of value
        """
        # Given
        node = GPNode(type="terminal", value="close", depth=0)

        # When
        result = node.to_string()

        # Then
        assert result == "close"

    def test_to_string_function_node(self):
        """Test: Function node converts to s-expression format.

        Given: Function node with children
        When: Converting to string
        Then: Returns (func child1 child2) format
        """
        # Given: (add 10 20)
        child1 = GPNode(type="terminal", value=10.0, depth=1)
        child2 = GPNode(type="terminal", value=20.0, depth=1)
        add_node = GPNode(
            type="function", value="add", children=[child1, child2], depth=0
        )

        # When
        result = add_node.to_string()

        # Then
        assert result == "(add 10.0 20.0)"

    def test_count_nodes_terminal(self):
        """Test: count_nodes returns 1 for terminal.

        Given: Terminal node
        When: Counting nodes
        Then: Returns 1
        """
        # Given
        node = GPNode(type="terminal", value=42.0, depth=0)

        # When
        count = node.count_nodes()

        # Then
        assert count == 1

    def test_count_nodes_function_tree(self):
        """Test: count_nodes returns total nodes in tree.

        Given: Function tree with multiple nodes
        When: Counting nodes
        Then: Returns total count
        """
        # Given: (add (mul 2 3) 5) = 5 nodes
        mul_node = GPNode(
            type="function",
            value="mul",
            children=[
                GPNode(type="terminal", value=2.0, depth=2),
                GPNode(type="terminal", value=3.0, depth=2),
            ],
            depth=1,
        )

        add_node = GPNode(
            type="function",
            value="add",
            children=[mul_node, GPNode(type="terminal", value=5.0, depth=1)],
            depth=0,
        )

        # When
        count = add_node.count_nodes()

        # Then: 1 (add) + 1 (mul) + 1 (2.0) + 1 (3.0) + 1 (5.0) = 5
        assert count == 5

    def test_get_depth_terminal(self):
        """Test: get_depth returns 0 for terminal.

        Given: Terminal node
        When: Getting depth
        Then: Returns 0
        """
        # Given
        node = GPNode(type="terminal", value=42.0, depth=0)

        # When
        depth = node.get_depth()

        # Then
        assert depth == 0

    def test_get_depth_nested_tree(self):
        """Test: get_depth returns maximum depth.

        Given: Nested tree with depth 2
        When: Getting depth
        Then: Returns 2
        """
        # Given: (add (mul 2 3) 5) - depth 2
        mul_node = GPNode(
            type="function",
            value="mul",
            children=[
                GPNode(type="terminal", value=2.0, depth=2),
                GPNode(type="terminal", value=3.0, depth=2),
            ],
            depth=1,
        )

        add_node = GPNode(
            type="function",
            value="add",
            children=[mul_node, GPNode(type="terminal", value=5.0, depth=1)],
            depth=0,
        )

        # When
        depth = add_node.get_depth()

        # Then
        assert depth == 2


class TestGeneticProgrammingGenerator:
    """Tests for GeneticProgrammingGenerator."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return GeneticProgrammingConfig(
            population_size=100,
            num_generations=10,
            max_tree_depth=4,
        )

    @pytest.fixture
    def generator(self, config):
        """Create GP generator instance."""
        return GeneticProgrammingGenerator(config)

    def test_initialization(self, generator, config):
        """Test: Generator initializes with config.

        Given: GP configuration
        When: Creating generator
        Then: Stores config and sets up function arities
        """
        # Then
        assert generator.config == config
        assert generator.config.population_size == 100
        assert generator.config.num_generations == 10

        # Check function arities initialized
        assert generator.function_arities["add"] == 2
        assert generator.function_arities["sqrt"] == 1
        assert generator.function_arities["and"] == 2

    def test_function_arities_complete(self, generator):
        """Test: All standard functions have arities defined.

        Given: Initialized generator
        When: Checking function arities
        Then: All operators have correct arities
        """
        # Then: Binary operators
        assert generator.function_arities["add"] == 2
        assert generator.function_arities["sub"] == 2
        assert generator.function_arities["mul"] == 2
        assert generator.function_arities["div"] == 2
        assert generator.function_arities["max"] == 2
        assert generator.function_arities["min"] == 2
        assert generator.function_arities["gt"] == 2
        assert generator.function_arities["lt"] == 2

        # Unary operators
        assert generator.function_arities["sqrt"] == 1
        assert generator.function_arities["abs"] == 1
        assert generator.function_arities["log"] == 1
        assert generator.function_arities["exp"] == 1
        assert generator.function_arities["not"] == 1

    def test_population_starts_empty(self, generator):
        """Test: Population starts as empty list.

        Given: New generator
        When: Checking population
        Then: Population is empty list
        """
        # Then
        assert isinstance(generator.population, list)
        assert len(generator.population) == 0
