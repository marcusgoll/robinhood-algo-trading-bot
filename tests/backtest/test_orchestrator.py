"""
Tests for StrategyOrchestrator initialization and weight validation.

Following TDD RED phase - tests written before StrategyOrchestrator implementation.
Tests will FAIL until T016 implements the StrategyOrchestrator class.
"""

import pytest
from decimal import Decimal
from typing import List, Tuple

from src.trading_bot.backtest.models import HistoricalDataBar, Position
from src.trading_bot.backtest.strategy_protocol import IStrategy


# Import will FAIL because StrategyOrchestrator doesn't exist yet (TDD RED phase)
# This is expected and will be resolved in T015/T016
from src.trading_bot.backtest.orchestrator import StrategyOrchestrator


class TestOrchestratorInitialization:
    """
    Test Suite: StrategyOrchestrator Initialization and Weight Validation

    Tests weight validation logic as specified in:
    - spec.md FR-002: Weights must sum to ≤1.0 (≤100%)
    - spec.md NFR-003: Fail-fast validation at initialization
    - tasks.md T010: Orchestrator initialization validates weight sum ≤1.0

    TDD Phase: RED - tests WILL FAIL until StrategyOrchestrator implemented in T016
    """

    def test_init_valid_weights_passes(self, sample_strategies: List[IStrategy]):
        """
        Test: Orchestrator accepts valid weights that sum to ≤1.0 (100%).

        **Acceptance Criteria** (spec.md FR-002, US1):
        GIVEN: List of (strategy, weight) tuples with sum ≤1.0
        WHEN: StrategyOrchestrator.__init__() is called
        THEN: Initialization succeeds without raising errors

        **Test Scenarios**:
        1. Weights sum to exactly 1.0 (100% allocation)
        2. Weights sum to less than 1.0 (partial allocation, e.g., 70%)

        **From**: spec.md FR-002, tasks.md T010
        **Pattern**: tests/backtest/test_engine.py initialization tests
        **TDD Phase**: RED - will fail with ImportError until orchestrator.py created
        """
        # SCENARIO 1: Weights sum to exactly 1.0 (100%)
        # GIVEN: 3 strategies with weights summing to 1.0
        strategies_with_weights: List[Tuple[IStrategy, Decimal]] = [
            (sample_strategies[0], Decimal("0.40")),  # 40%
            (sample_strategies[1], Decimal("0.35")),  # 35%
            (sample_strategies[2], Decimal("0.25")),  # 25%
        ]

        # WHEN: Orchestrator initialized with valid weights
        # THEN: No exception should be raised
        try:
            orchestrator = StrategyOrchestrator(strategies_with_weights)
            # Verify orchestrator was created successfully
            assert orchestrator is not None, "Orchestrator should be initialized"
        except ValueError as e:
            pytest.fail(
                f"Orchestrator should accept weights summing to 1.0, "
                f"but raised ValueError: {e}"
            )

        # SCENARIO 2: Weights sum to less than 1.0 (partial allocation)
        # GIVEN: 2 strategies with weights summing to 0.70 (70%)
        partial_allocation: List[Tuple[IStrategy, Decimal]] = [
            (sample_strategies[0], Decimal("0.50")),  # 50%
            (sample_strategies[1], Decimal("0.20")),  # 20%
        ]

        # WHEN: Orchestrator initialized with partial allocation
        # THEN: No exception should be raised (partial allocation is allowed)
        try:
            orchestrator_partial = StrategyOrchestrator(partial_allocation)
            assert orchestrator_partial is not None, (
                "Orchestrator should accept weights summing to <1.0 (partial allocation)"
            )
        except ValueError as e:
            pytest.fail(
                f"Orchestrator should accept weights summing to 0.70, "
                f"but raised ValueError: {e}"
            )

    def test_init_invalid_weights_raises_value_error(self, sample_strategies: List[IStrategy]):
        """
        Test: Orchestrator rejects weights that sum to >1.0 (>100%).

        **Acceptance Criteria** (spec.md FR-002, NFR-003):
        GIVEN: Weights summing to >1.0 (over-allocation)
        WHEN: StrategyOrchestrator.__init__() is called
        THEN: Raises ValueError with descriptive message

        **Fail-Fast Principle** (spec.md NFR-003):
        System must validate all configuration at initialization to prevent
        runtime errors during backtest execution.

        **Test Scenarios**:
        1. Weights sum to 1.5 (150% over-allocation)
        2. Weights sum to slightly over 1.0 (edge case: 1.01)

        **From**: spec.md FR-002, NFR-003, tasks.md T010
        **Pattern**: tests/backtest/test_engine.py validation tests
        **TDD Phase**: RED - will fail with ImportError until orchestrator.py created
        """
        # SCENARIO 1: Obvious over-allocation (150%)
        # GIVEN: 3 strategies with weights summing to 1.5
        over_allocated_weights: List[Tuple[IStrategy, Decimal]] = [
            (sample_strategies[0], Decimal("0.60")),  # 60%
            (sample_strategies[1], Decimal("0.50")),  # 50%
            (sample_strategies[2], Decimal("0.40")),  # 40%
        ]

        # WHEN: Orchestrator initialized with over-allocated weights
        # THEN: Should raise ValueError
        with pytest.raises(ValueError) as exc_info:
            StrategyOrchestrator(over_allocated_weights)

        # Verify error message is descriptive
        error_message = str(exc_info.value).lower()
        assert "weight" in error_message or "allocation" in error_message, (
            "Error message should mention 'weight' or 'allocation'"
        )
        assert "1.0" in error_message or "100" in error_message, (
            "Error message should mention the 1.0 (100%) limit"
        )

        # SCENARIO 2: Edge case - slightly over 1.0 (101%)
        # GIVEN: 2 strategies with weights summing to 1.01
        edge_case_weights: List[Tuple[IStrategy, Decimal]] = [
            (sample_strategies[0], Decimal("0.51")),  # 51%
            (sample_strategies[1], Decimal("0.50")),  # 50%
        ]

        # WHEN: Orchestrator initialized with edge case over-allocation
        # THEN: Should raise ValueError (strict validation)
        with pytest.raises(ValueError) as exc_info:
            StrategyOrchestrator(edge_case_weights)

        # Verify error message includes actual sum
        error_message = str(exc_info.value)
        assert "1.01" in error_message, (
            f"Error message should show actual weight sum (1.01). "
            f"Got: {error_message}"
        )


class TestStrategyOrchestratorCapitalAllocation:
    """
    Test Suite: Capital Allocation (US1, FR-003)

    Verifies that StrategyOrchestrator correctly allocates capital to strategies
    based on their weights during initialization.

    From: specs/021-strategy-orchestrato/spec.md FR-003
    Pattern: tests/backtest/test_engine.py state verification tests
    """

    def test_capital_allocation_proportional(self, sample_strategies: List[IStrategy]):
        """
        T011 [RED]: Test proportional capital allocation to strategies.

        **Test Scenario**:
        GIVEN: 3 strategies with weights [0.5, 0.3, 0.2]
        AND: Initial capital of $100,000
        WHEN: StrategyOrchestrator is initialized
        THEN: Capital allocations are [50000, 30000, 20000]
        AND: StrategyAllocation objects are created correctly for each strategy

        **Expected Behavior** (FR-003):
        - Strategy 1 (weight 0.5): $100,000 × 0.5 = $50,000 allocated
        - Strategy 2 (weight 0.3): $100,000 × 0.3 = $30,000 allocated
        - Strategy 3 (weight 0.2): $100,000 × 0.2 = $20,000 allocated

        **TDD RED PHASE**: This test WILL FAIL because:
        - StrategyOrchestrator.__init__ doesn't implement capital allocation yet
        - Expected AttributeError or AssertionError

        From: spec.md FR-003 (proportional allocation)
        Pattern: tests/backtest/test_engine.py state verification tests
        """
        # ARRANGE: Setup test data with specific weights for this test
        # Using weights [0.5, 0.3, 0.2] instead of sample_weights fixture
        strategies_with_weights: List[Tuple[IStrategy, Decimal]] = [
            (sample_strategies[0], Decimal("0.5")),  # 50%
            (sample_strategies[1], Decimal("0.3")),  # 30%
            (sample_strategies[2], Decimal("0.2")),  # 20%
        ]
        initial_capital = Decimal("100000.0")

        # Expected allocations after initialization
        expected_allocations = {
            0: Decimal("50000.0"),  # Strategy 1: 100k × 0.5
            1: Decimal("30000.0"),  # Strategy 2: 100k × 0.3
            2: Decimal("20000.0"),  # Strategy 3: 100k × 0.2
        }

        # ACT: Initialize orchestrator with strategies, weights, and initial capital
        # This will FAIL in RED phase because capital allocation not implemented
        orchestrator = StrategyOrchestrator(
            strategies_with_weights=strategies_with_weights,
            initial_capital=initial_capital
        )

        # ASSERT: Verify StrategyAllocation objects created correctly

        # Assert 1: Orchestrator should have 3 strategy allocations
        assert hasattr(orchestrator, '_allocations'), (
            "Orchestrator should have '_allocations' attribute to store StrategyAllocation objects"
        )
        assert len(orchestrator._allocations) == 3, (
            f"Expected 3 strategy allocations, got {len(orchestrator._allocations)}"
        )

        # Assert 2: Verify allocation amounts for each strategy
        for i, allocation in enumerate(orchestrator._allocations):
            expected_capital = expected_allocations[i]

            # Verify StrategyAllocation instance
            assert hasattr(allocation, 'allocated_capital'), (
                f"Allocation {i} should be a StrategyAllocation object with allocated_capital attribute"
            )

            # Verify allocated_capital matches expected
            assert allocation.allocated_capital == expected_capital, (
                f"Strategy index {i}: Expected allocated_capital=${expected_capital}, "
                f"got ${allocation.allocated_capital}"
            )

            # Verify used_capital is 0 initially (no positions opened yet)
            assert allocation.used_capital == Decimal("0.0"), (
                f"Strategy index {i}: Expected initial used_capital=$0, "
                f"got ${allocation.used_capital}"
            )

            # Verify available_capital equals allocated_capital initially
            assert allocation.available_capital == expected_capital, (
                f"Strategy index {i}: Expected available_capital=${expected_capital}, "
                f"got ${allocation.available_capital}"
            )

            # Verify strategy_id is set correctly
            assert hasattr(allocation, 'strategy_id'), (
                f"Allocation {i} should have strategy_id attribute"
            )
            assert allocation.strategy_id is not None, (
                f"Allocation {i} strategy_id should not be None"
            )

        # Assert 3: Verify total allocated capital equals initial capital
        total_allocated = sum(
            allocation.allocated_capital
            for allocation in orchestrator._allocations
        )
        assert total_allocated == initial_capital, (
            f"Total allocated capital (${total_allocated}) must equal "
            f"initial capital (${initial_capital})"
        )

        # Assert 4: Verify strategy IDs are unique
        strategy_ids = [allocation.strategy_id for allocation in orchestrator._allocations]
        assert len(strategy_ids) == len(set(strategy_ids)), (
            f"Strategy IDs must be unique. Got: {strategy_ids}"
        )

        # Assert 5: Verify each allocation is a StrategyAllocation instance
        from src.trading_bot.backtest.models import StrategyAllocation
        for i, allocation in enumerate(orchestrator._allocations):
            assert isinstance(allocation, StrategyAllocation), (
                f"Allocation {i} should be a StrategyAllocation instance, "
                f"got {type(allocation).__name__}"
            )


class TestStrategyOrchestratorChronologicalExecution:
    """
    Test Suite: T012 [P1] [US1] - Chronological execution across all strategies

    Verifies that the orchestrator executes all strategies chronologically on every
    historical bar without look-ahead bias. This is critical for backtest validity.

    From: specs/021-strategy-orchestrato/spec.md
    - FR-004: System MUST execute all strategies chronologically on every historical bar
    - FR-015: System MUST maintain chronological order guarantee (no look-ahead bias)

    TDD Phase: RED - StrategyOrchestrator.run() doesn't exist yet
    """

    @pytest.fixture
    def mock_historical_data(self) -> List[HistoricalDataBar]:
        """
        Create 10 bars of mock historical data with unique identifiers.

        Each bar has a unique timestamp and price to make it identifiable.
        This allows us to verify exact execution order and data visibility.

        Returns:
            List of 10 HistoricalDataBar objects with sequential timestamps
        """
        from datetime import datetime, timezone
        bars = []
        base_date = datetime(2024, 1, 2, 9, 30, tzinfo=timezone.utc)  # Trading day

        for i in range(10):
            bar = HistoricalDataBar(
                symbol="TEST",
                timestamp=datetime(2024, 1, 2 + i, 9, 30, tzinfo=timezone.utc),
                open=Decimal(f"{100 + i}.00"),
                high=Decimal(f"{102 + i}.00"),
                low=Decimal(f"{99 + i}.00"),
                close=Decimal(f"{101 + i}.00"),
                volume=1000000 + (i * 10000),
                split_adjusted=True,
                dividend_adjusted=True,
            )
            bars.append(bar)

        return bars

    def test_chronological_execution_all_strategies(
        self,
        mock_historical_data: List[HistoricalDataBar]
    ):
        """
        T012 [P1] [US1]: Test orchestrator executes all strategies chronologically.

        **Acceptance Criteria**:
        1. Orchestrator processes bars in exact chronological order (bar[0] → bar[9])
        2. ALL strategies evaluate EVERY bar in the same chronological order
        3. At bar[i], strategies can only see bars[0:i+1], not future bars[i+1:]
        4. Number of calls to should_enter() equals number of bars (10) for EACH strategy
        5. Each strategy receives the same progressive data (1 bar, then 2, then 3, etc.)
        6. No future bar timestamps are visible when processing current bar

        **Look-Ahead Bias Prevention**:
        - When processing bar at index i=5 (timestamp 2024-01-07):
          * Strategy1 can see bars 0-5 (timestamps 2024-01-02 through 2024-01-07)
          * Strategy2 can see bars 0-5 (timestamps 2024-01-02 through 2024-01-07)
          * Neither strategy can see bars 6-9 (timestamps 2024-01-08 through 2024-01-11)

        **Test Design**:
        - Uses TrackingStrategy that records every call to should_enter()
        - Tracks what data (bars) were visible at each call
        - Verifies no future data leaks into current bar processing

        This test will FAIL because StrategyOrchestrator.run() doesn't exist yet (TDD RED phase).

        From:
        - spec.md FR-004: Execute all strategies chronologically on every bar
        - spec.md FR-015: Maintain chronological order guarantee (no look-ahead bias)
        - tasks.md T012: Write test for chronological execution across all strategies
        - Pattern: tests/backtest/test_engine.py execution order tests
        """
        from dataclasses import dataclass, field
        from datetime import datetime

        # ARRANGE: Create two tracking strategies to monitor execution
        @dataclass
        class TrackingStrategy:
            """
            Test strategy that records method calls to verify chronological execution.

            Tracks:
            - call_timestamps: List of bar timestamps when should_enter() was called
            - call_count: Number of times should_enter() was called
            - visible_bars_history: What bars were visible at each call
            """
            strategy_name: str
            call_timestamps: List[datetime] = field(default_factory=list)
            call_count: int = 0
            visible_bars_history: List[List[HistoricalDataBar]] = field(default_factory=list)

            def should_enter(self, bars: List[HistoricalDataBar]) -> bool:
                """Record what bars are visible and track call order."""
                self.call_count += 1

                if bars:
                    current_bar = bars[-1]
                    self.call_timestamps.append(current_bar.timestamp)
                    # Store a copy of all visible bars at this point
                    self.visible_bars_history.append(bars.copy())

                return False  # Never enter trades

            def should_exit(self, position: Position, bars: List[HistoricalDataBar]) -> bool:
                """Strategy never enters, so this won't be called."""
                return False

            def position_size(self, capital: float, price: float) -> int:
                """Return default position size (not used by this strategy)."""
                return 100

        strategy1 = TrackingStrategy(strategy_name="Strategy1")
        strategy2 = TrackingStrategy(strategy_name="Strategy2")

        strategies_with_weights = [
            (strategy1, Decimal("0.5")),  # 50% allocation
            (strategy2, Decimal("0.5")),  # 50% allocation
        ]

        initial_capital = Decimal("100000.0")

        # ACT: Create orchestrator and run backtest
        # This will FAIL in RED phase because run() method doesn't exist
        orchestrator = StrategyOrchestrator(
            strategies_with_weights=strategies_with_weights,
            initial_capital=initial_capital
        )

        # Run orchestrator with historical data
        # Expected to fail: AttributeError: 'StrategyOrchestrator' object has no attribute 'run'
        result = orchestrator.run(historical_data={"TEST": mock_historical_data})

        # ASSERT 1: Each strategy called exactly once per bar (10 bars = 10 calls)
        expected_calls_per_strategy = 10
        assert strategy1.call_count == expected_calls_per_strategy, (
            f"Strategy1 should be called {expected_calls_per_strategy} times (once per bar), "
            f"got {strategy1.call_count} calls"
        )
        assert strategy2.call_count == expected_calls_per_strategy, (
            f"Strategy2 should be called {expected_calls_per_strategy} times (once per bar), "
            f"got {strategy2.call_count} calls"
        )

        # ASSERT 2: Both strategies see bars in chronological order
        expected_timestamps = [bar.timestamp for bar in mock_historical_data]
        assert strategy1.call_timestamps == expected_timestamps, (
            "Strategy1 bars were not processed in chronological order. "
            f"Expected: {expected_timestamps}, "
            f"Got: {strategy1.call_timestamps}"
        )
        assert strategy2.call_timestamps == expected_timestamps, (
            "Strategy2 bars were not processed in chronological order. "
            f"Expected: {expected_timestamps}, "
            f"Got: {strategy2.call_timestamps}"
        )

        # ASSERT 3: At each step, both strategies could only see past data (no look-ahead bias)
        for strategy_name, strategy in [("Strategy1", strategy1), ("Strategy2", strategy2)]:
            for i, visible_bars_at_step in enumerate(strategy.visible_bars_history):
                # At step i, strategy should see bars[0:i+1]
                expected_count = i + 1
                actual_count = len(visible_bars_at_step)

                assert actual_count == expected_count, (
                    f"{strategy_name}: At bar {i}, should see {expected_count} bars (0 to {i}), "
                    f"but saw {actual_count} bars. This indicates look-ahead bias!"
                )

                # Verify the last visible bar is the current bar being processed
                current_bar = mock_historical_data[i]
                visible_current_bar = visible_bars_at_step[-1]

                assert visible_current_bar.timestamp == current_bar.timestamp, (
                    f"{strategy_name}: At bar {i}, last visible bar timestamp should be {current_bar.timestamp}, "
                    f"but was {visible_current_bar.timestamp}"
                )

                # Verify no future bars are visible
                future_timestamps = [bar.timestamp for bar in mock_historical_data[i+1:]]
                visible_timestamps = [bar.timestamp for bar in visible_bars_at_step]

                for future_ts in future_timestamps:
                    assert future_ts not in visible_timestamps, (
                        f"LOOK-AHEAD BIAS DETECTED in {strategy_name}! "
                        f"At bar {i} ({current_bar.timestamp}), "
                        f"strategy can see future bar {future_ts}"
                    )

        # ASSERT 4: Verify first bar sees only itself, last bar sees all 10 (both strategies)
        assert len(strategy1.visible_bars_history[0]) == 1, "Strategy1: First bar should only see itself"
        assert len(strategy1.visible_bars_history[-1]) == 10, "Strategy1: Last bar should see all 10 bars"
        assert len(strategy2.visible_bars_history[0]) == 1, "Strategy2: First bar should only see itself"
        assert len(strategy2.visible_bars_history[-1]) == 10, "Strategy2: Last bar should see all 10 bars"

        # ASSERT 5: Both strategies see identical data at each step
        for i in range(len(strategy1.visible_bars_history)):
            bars1 = strategy1.visible_bars_history[i]
            bars2 = strategy2.visible_bars_history[i]

            assert len(bars1) == len(bars2), (
                f"At step {i}, strategies see different number of bars: "
                f"Strategy1={len(bars1)}, Strategy2={len(bars2)}"
            )

            for j, (bar1, bar2) in enumerate(zip(bars1, bars2)):
                assert bar1.timestamp == bar2.timestamp, (
                    f"At step {i}, bar {j}: Strategy1 sees {bar1.timestamp}, "
                    f"Strategy2 sees {bar2.timestamp} - data mismatch!"
                )
