"""Smoke tests for phase system.

Validates basic initialization and performance requirements.
Tests: T175-T176 from specs/022-pos-scale-progress/tasks.md
"""

import pytest
import time
from decimal import Decimal
from datetime import date

from trading_bot.config import Config
from trading_bot.phase import Phase, PhaseManager
from trading_bot.phase.trade_limiter import TradeLimiter


class TestPhaseSystemSmoke:
    """Smoke tests for phase system initialization and performance."""

    def test_phase_system_initializes(self):
        """Smoke test: Phase system loads without errors (T175).

        Validates:
        - Config loads phase configuration
        - PhaseManager initializes successfully
        - Current phase is valid
        - Phase enum converts string correctly
        """
        # Load configuration
        config = Config.from_env_and_json()

        # Create PhaseManager
        manager = PhaseManager(config)

        # Validate current phase is valid
        valid_phases = ["experience", "proof", "trial", "scaling"]
        assert manager.config.current_phase in valid_phases, (
            f"Invalid phase: {manager.config.current_phase}"
        )

        # Validate Phase enum conversion
        current_phase_enum = Phase.from_string(manager.config.current_phase)
        assert isinstance(current_phase_enum, Phase)

        # Validate phase name mapping
        phase_names = {
            Phase.EXPERIENCE: "Experience",
            Phase.PROOF_OF_CONCEPT: "Proof of Concept",
            Phase.REAL_MONEY_TRIAL: "Real Money Trial",
            Phase.SCALING: "Scaling"
        }
        assert current_phase_enum in phase_names

    def test_phase_transition_performance(self):
        """Smoke test: Phase validation completes in <50ms (T176).

        Validates:
        - validate_transition() executes quickly
        - Performance target: <50ms
        - No blocking I/O during validation
        """
        # Load configuration
        config = Config.from_env_and_json()
        manager = PhaseManager(config)

        # Test phase transition validation performance
        target_phase = Phase.PROOF_OF_CONCEPT

        # Warm-up run (exclude from timing)
        _ = manager.validate_transition(target_phase)

        # Timed run
        start = time.perf_counter()
        result = manager.validate_transition(target_phase)
        elapsed = (time.perf_counter() - start) * 1000  # Convert to ms

        # Validate performance target
        assert elapsed < 50, (
            f"Phase validation took {elapsed:.2f}ms (target: <50ms)"
        )

        # Validate result structure
        assert hasattr(result, 'can_advance')
        assert hasattr(result, 'criteria_met')
        assert hasattr(result, 'missing_requirements')
        assert hasattr(result, 'metrics_summary')

        # Validate result types
        assert isinstance(result.can_advance, bool)
        assert isinstance(result.criteria_met, dict)
        assert isinstance(result.missing_requirements, list)
        assert isinstance(result.metrics_summary, dict)

    def test_phase_enum_values(self):
        """Smoke test: Phase enum has all expected values.

        Validates:
        - All four phases defined
        - String conversion works bidirectionally
        - Phase value matches config format
        """
        expected_phases = {
            Phase.EXPERIENCE: "experience",
            Phase.PROOF_OF_CONCEPT: "proof",
            Phase.REAL_MONEY_TRIAL: "trial",
            Phase.SCALING: "scaling"
        }

        # Validate enum values
        for phase_enum, phase_string in expected_phases.items():
            assert phase_enum.value == phase_string
            assert Phase.from_string(phase_string) == phase_enum

        # Validate invalid phase raises error
        with pytest.raises(ValueError, match="Invalid phase"):
            Phase.from_string("invalid_phase")

    def test_phase_manager_attributes(self):
        """Smoke test: PhaseManager has required attributes.

        Validates:
        - Config attribute exists
        - Trade limiter initialized
        - All validators accessible
        """
        config = Config.from_env_and_json()
        manager = PhaseManager(config)

        # Validate required attributes
        assert hasattr(manager, 'config')
        assert hasattr(manager, 'trade_limiter')
        assert hasattr(manager, 'validators')

        # Validate attribute types
        assert isinstance(manager.config, Config)
        assert isinstance(manager.trade_limiter, TradeLimiter)

        # Validate validators dictionary
        assert isinstance(manager.validators, dict)
        expected_transitions = [
            ("experience", "proof"),
            ("proof", "trial"),
            ("trial", "scaling")
        ]
        for transition in expected_transitions:
            assert transition in manager.validators
