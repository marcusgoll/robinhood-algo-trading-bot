#!/usr/bin/env python3
"""
Trading Workflow State Machine

Manages workflow states and transitions for the LLM-enhanced trading bot.
Each workflow represents a phase in the trading day with specific actions.
"""

from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, time
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


class WorkflowState(Enum):
    """Trading workflow states"""
    IDLE = "idle"
    PRE_MARKET_SCREENING = "pre_market_screening"
    TRADE_ANALYSIS = "trade_analysis"
    POSITION_OPTIMIZATION = "position_optimization"
    MARKET_EXECUTION = "market_execution"
    INTRADAY_MONITORING = "intraday_monitoring"
    END_OF_DAY_REVIEW = "end_of_day_review"
    WEEKLY_REVIEW = "weekly_review"
    BACKTESTING = "backtesting"
    ERROR = "error"


class WorkflowTransition(Enum):
    """Valid state transitions"""
    START_PRE_MARKET = "start_pre_market"
    SCREENING_COMPLETE = "screening_complete"
    ANALYSIS_COMPLETE = "analysis_complete"
    OPTIMIZATION_COMPLETE = "optimization_complete"
    MARKET_OPEN = "market_open"
    EXECUTION_COMPLETE = "execution_complete"
    START_MONITORING = "start_monitoring"
    MARKET_CLOSE = "market_close"
    REVIEW_COMPLETE = "review_complete"
    START_WEEKLY_REVIEW = "start_weekly_review"
    START_BACKTEST = "start_backtest"
    BACKTEST_COMPLETE = "backtest_complete"
    ERROR_OCCURRED = "error_occurred"
    RESET = "reset"


@dataclass
class WorkflowContext:
    """Context data passed between workflow states"""
    current_state: WorkflowState = WorkflowState.IDLE
    timestamp: datetime = field(default_factory=datetime.now)

    # Screening results
    watchlist: List[Dict[str, Any]] = field(default_factory=list)

    # Analysis results
    analyzed_symbols: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # Optimization results
    optimized_trades: List[Dict[str, Any]] = field(default_factory=list)

    # Execution tracking
    executed_trades: List[Dict[str, Any]] = field(default_factory=list)

    # Performance tracking
    daily_pnl: float = 0.0
    trade_count: int = 0

    # Error tracking
    errors: List[str] = field(default_factory=list)

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)


class WorkflowStateMachine:
    """
    State machine for trading workflow orchestration.

    Manages transitions between different trading phases and ensures
    proper sequencing of LLM operations.
    """

    # Define valid state transitions
    _transitions: Dict[WorkflowState, Dict[WorkflowTransition, WorkflowState]] = {
        WorkflowState.IDLE: {
            WorkflowTransition.START_PRE_MARKET: WorkflowState.PRE_MARKET_SCREENING,
            WorkflowTransition.START_MONITORING: WorkflowState.INTRADAY_MONITORING,  # Allow monitoring from IDLE for after-hours/existing positions
            WorkflowTransition.START_WEEKLY_REVIEW: WorkflowState.WEEKLY_REVIEW,
            WorkflowTransition.START_BACKTEST: WorkflowState.BACKTESTING,
        },
        WorkflowState.PRE_MARKET_SCREENING: {
            WorkflowTransition.SCREENING_COMPLETE: WorkflowState.TRADE_ANALYSIS,
            WorkflowTransition.ERROR_OCCURRED: WorkflowState.ERROR,
            WorkflowTransition.RESET: WorkflowState.IDLE,
        },
        WorkflowState.TRADE_ANALYSIS: {
            WorkflowTransition.ANALYSIS_COMPLETE: WorkflowState.POSITION_OPTIMIZATION,
            WorkflowTransition.ERROR_OCCURRED: WorkflowState.ERROR,
            WorkflowTransition.RESET: WorkflowState.IDLE,
        },
        WorkflowState.POSITION_OPTIMIZATION: {
            WorkflowTransition.OPTIMIZATION_COMPLETE: WorkflowState.MARKET_EXECUTION,
            WorkflowTransition.MARKET_OPEN: WorkflowState.MARKET_EXECUTION,
            WorkflowTransition.ERROR_OCCURRED: WorkflowState.ERROR,
            WorkflowTransition.RESET: WorkflowState.IDLE,
        },
        WorkflowState.MARKET_EXECUTION: {
            WorkflowTransition.EXECUTION_COMPLETE: WorkflowState.INTRADAY_MONITORING,
            WorkflowTransition.START_MONITORING: WorkflowState.INTRADAY_MONITORING,
            WorkflowTransition.ERROR_OCCURRED: WorkflowState.ERROR,
            WorkflowTransition.RESET: WorkflowState.IDLE,
        },
        WorkflowState.INTRADAY_MONITORING: {
            WorkflowTransition.START_MONITORING: WorkflowState.INTRADAY_MONITORING,  # Allow continuous monitoring (after-hours scans)
            WorkflowTransition.MARKET_OPEN: WorkflowState.MARKET_EXECUTION,  # Allow execution when market opens during monitoring
            WorkflowTransition.MARKET_CLOSE: WorkflowState.END_OF_DAY_REVIEW,
            WorkflowTransition.ERROR_OCCURRED: WorkflowState.ERROR,
            WorkflowTransition.RESET: WorkflowState.IDLE,
        },
        WorkflowState.END_OF_DAY_REVIEW: {
            WorkflowTransition.REVIEW_COMPLETE: WorkflowState.IDLE,
            WorkflowTransition.ERROR_OCCURRED: WorkflowState.ERROR,
            WorkflowTransition.RESET: WorkflowState.IDLE,
        },
        WorkflowState.WEEKLY_REVIEW: {
            WorkflowTransition.REVIEW_COMPLETE: WorkflowState.IDLE,
            WorkflowTransition.START_BACKTEST: WorkflowState.BACKTESTING,
            WorkflowTransition.ERROR_OCCURRED: WorkflowState.ERROR,
            WorkflowTransition.RESET: WorkflowState.IDLE,
        },
        WorkflowState.BACKTESTING: {
            WorkflowTransition.BACKTEST_COMPLETE: WorkflowState.IDLE,
            WorkflowTransition.ERROR_OCCURRED: WorkflowState.ERROR,
            WorkflowTransition.RESET: WorkflowState.IDLE,
        },
        WorkflowState.ERROR: {
            WorkflowTransition.RESET: WorkflowState.IDLE,
        },
    }

    def __init__(self):
        self.context = WorkflowContext()
        self.history: List[tuple[WorkflowState, datetime]] = [(WorkflowState.IDLE, datetime.now())]

    def transition(self, transition: WorkflowTransition) -> bool:
        """
        Attempt state transition.

        Args:
            transition: Desired transition

        Returns:
            True if transition successful, False otherwise
        """
        current_state = self.context.current_state

        # Check if transition is valid
        if current_state not in self._transitions:
            logger.error(f"No transitions defined for state {current_state}")
            return False

        if transition not in self._transitions[current_state]:
            logger.error(f"Invalid transition {transition} from state {current_state}")
            return False

        # Perform transition
        new_state = self._transitions[current_state][transition]
        old_state = self.context.current_state

        self.context.current_state = new_state
        self.context.timestamp = datetime.now()
        self.history.append((new_state, datetime.now()))

        logger.info(f"Workflow transition: {old_state.value} -> {new_state.value} (via {transition.value})")

        return True

    def can_transition(self, transition: WorkflowTransition) -> bool:
        """Check if transition is valid from current state."""
        current_state = self.context.current_state

        if current_state not in self._transitions:
            return False

        return transition in self._transitions[current_state]

    def reset(self):
        """Reset to IDLE state and clear context."""
        self.context = WorkflowContext()
        self.history.append((WorkflowState.IDLE, datetime.now()))
        logger.info("Workflow reset to IDLE")

    def add_error(self, error_msg: str):
        """Add error to context and transition to ERROR state."""
        self.context.errors.append(f"{datetime.now()}: {error_msg}")
        logger.error(f"Workflow error: {error_msg}")
        self.transition(WorkflowTransition.ERROR_OCCURRED)

    def get_current_state(self) -> WorkflowState:
        """Get current workflow state."""
        return self.context.current_state

    def get_context(self) -> WorkflowContext:
        """Get current workflow context."""
        return self.context

    def get_history(self) -> List[tuple[WorkflowState, datetime]]:
        """Get state transition history."""
        return self.history.copy()

    def is_idle(self) -> bool:
        """Check if workflow is idle."""
        return self.context.current_state == WorkflowState.IDLE

    def is_error(self) -> bool:
        """Check if workflow is in error state."""
        return self.context.current_state == WorkflowState.ERROR
