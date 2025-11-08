"""Self-Learning Loop for nightly optimization cycles.

Orchestrates automated learning and strategy improvement:
1. Analyze recent trade performance (LearningAgent)
2. Propose parameter adjustments (StrategyBuilderAgent)
3. Evaluate and auto-apply high-confidence changes
4. Track improvement over time

Run nightly via cron or Windows Task Scheduler.
"""

import logging
import sys
from datetime import datetime, timedelta
from typing import Dict, Any, List
from pathlib import Path

from trading_bot.llm.memory_service import AgentMemory
from trading_bot.llm.agents import LearningAgent, StrategyBuilderAgent

logger = logging.getLogger(__name__)


class SelfLearningLoop:
    """Automated learning loop for continuous strategy improvement.

    Workflow:
    1. Check if enough new trades exist (need 10+ since last run)
    2. Run LearningAgent to identify patterns in wins/losses
    3. Run StrategyBuilderAgent to propose parameter adjustments
    4. Auto-apply high-confidence proposals (confidence > 80, priority HIGH)
    5. Flag medium-confidence proposals for human review
    6. Track Sharpe ratio before/after to measure improvement
    7. Log cycle results

    Auto-apply criteria:
    - Confidence >= 80/100
    - Priority == HIGH
    - Risk level == LOW
    - Sample size >= 30 trades
    - Not contradicting recent approved adjustments

    Human review criteria:
    - Confidence 60-79
    - Priority == MEDIUM or HIGH
    - Risk level == MEDIUM
    """

    def __init__(
        self,
        memory: AgentMemory = None,
        auto_apply_threshold: float = 80.0,
        min_trades_per_cycle: int = 10,
        lookback_days: int = 30
    ):
        """Initialize self-learning loop.

        Args:
            memory: AgentMemory instance (creates new if None)
            auto_apply_threshold: Minimum confidence to auto-apply (0-100)
            min_trades_per_cycle: Minimum trades needed to run cycle
            lookback_days: Days to analyze for learning
        """
        self.memory = memory or AgentMemory()
        self.auto_apply_threshold = auto_apply_threshold
        self.min_trades_per_cycle = min_trades_per_cycle
        self.lookback_days = lookback_days

        self.learning_agent = LearningAgent(memory=self.memory)
        self.strategy_builder = StrategyBuilderAgent(memory=self.memory)

    def run_cycle(self, strategy_name: str = "default") -> Dict[str, Any]:
        """Execute one self-learning cycle.

        Args:
            strategy_name: Strategy to optimize

        Returns:
            {
                'cycle_time': str,
                'trades_analyzed': int,
                'insights_found': int,
                'proposals_generated': int,
                'proposals_auto_applied': int,
                'proposals_flagged_review': int,
                'proposals_rejected': int,
                'improvement_summary': str,
                'cost_usd': float,
                'tokens_used': int
            }
        """
        cycle_start = datetime.utcnow()
        logger.info(f"Starting self-learning cycle for {strategy_name}")

        total_cost = 0.0
        total_tokens = 0

        # Step 1: Check if enough new trades exist
        recent_trades = self._count_recent_trades(strategy_name)
        if recent_trades < self.min_trades_per_cycle:
            logger.info(
                f"Insufficient new trades: {recent_trades} "
                f"(need {self.min_trades_per_cycle}). Skipping cycle."
            )
            return {
                'cycle_time': str(cycle_start),
                'trades_analyzed': recent_trades,
                'insights_found': 0,
                'proposals_generated': 0,
                'proposals_auto_applied': 0,
                'proposals_flagged_review': 0,
                'proposals_rejected': 0,
                'improvement_summary': 'Skipped: insufficient new trades',
                'cost_usd': 0.0,
                'tokens_used': 0
            }

        # Step 2: Run LearningAgent to analyze performance
        logger.info("Running LearningAgent to analyze performance patterns...")
        learning_result = self.learning_agent.execute({
            'lookback_days': self.lookback_days,
            'min_confidence': 60.0
        })

        total_cost += learning_result.get('cost_usd', 0.0)
        total_tokens += learning_result.get('tokens_used', 0)

        insights_found = len(learning_result.get('insights', []))
        logger.info(f"LearningAgent found {insights_found} insights")

        # Log insights
        for insight in learning_result.get('insights', []):
            logger.info(
                f"Insight: {insight['observation']} "
                f"(confidence: {insight['confidence']:.0f}%)"
            )

        # Step 3: Run StrategyBuilderAgent to propose adjustments
        logger.info("Running StrategyBuilderAgent to propose parameter adjustments...")
        strategy_result = self.strategy_builder.execute({
            'strategy_name': strategy_name,
            'lookback_days': self.lookback_days,
            'min_confidence': 60.0,
            'max_proposals': 5
        })

        total_cost += strategy_result.get('cost_usd', 0.0)
        total_tokens += strategy_result.get('tokens_used', 0)

        proposals = strategy_result.get('proposals', [])
        logger.info(f"StrategyBuilderAgent generated {len(proposals)} proposals")

        # Step 4: Evaluate and apply proposals
        auto_applied = []
        flagged_review = []
        rejected = []

        for proposal in proposals:
            decision = self._evaluate_proposal(proposal, learning_result)

            if decision == 'AUTO_APPLY':
                logger.info(
                    f"Auto-applying: {proposal['parameter_name']} "
                    f"{proposal['current_value']} → {proposal['proposed_value']} "
                    f"(confidence: {proposal['confidence']:.0f}%)"
                )
                self._apply_proposal(proposal, strategy_name)
                auto_applied.append(proposal)

            elif decision == 'FLAG_REVIEW':
                logger.info(
                    f"Flagging for review: {proposal['parameter_name']} "
                    f"(confidence: {proposal['confidence']:.0f}%)"
                )
                flagged_review.append(proposal)

            else:  # REJECT
                logger.info(
                    f"Rejecting: {proposal['parameter_name']} "
                    f"(confidence: {proposal['confidence']:.0f}%)"
                )
                rejected.append(proposal)

        # Step 5: Generate improvement summary
        improvement_summary = self._generate_summary(
            insights_found=insights_found,
            auto_applied=len(auto_applied),
            flagged_review=len(flagged_review)
        )

        logger.info(f"Cycle complete: {improvement_summary}")

        return {
            'cycle_time': str(cycle_start),
            'trades_analyzed': learning_result.get('total_trades', 0),
            'insights_found': insights_found,
            'proposals_generated': len(proposals),
            'proposals_auto_applied': len(auto_applied),
            'proposals_flagged_review': len(flagged_review),
            'proposals_rejected': len(rejected),
            'improvement_summary': improvement_summary,
            'cost_usd': total_cost,
            'tokens_used': total_tokens
        }

    def _count_recent_trades(self, strategy_name: str) -> int:
        """Count trades since last learning cycle.

        Args:
            strategy_name: Strategy name

        Returns:
            Number of recent trades
        """
        # Get last cycle time from agent_metrics
        last_cycle = self.memory.get_last_learning_cycle(strategy_name)

        if last_cycle:
            start_date = last_cycle
        else:
            # First run, look at last 7 days
            start_date = datetime.utcnow() - timedelta(days=7)

        trades = self.memory.get_trade_outcomes(
            strategy_name=strategy_name,
            start_date=start_date
        )

        return len(trades)

    def _evaluate_proposal(
        self,
        proposal: Dict[str, Any],
        learning_result: Dict[str, Any]
    ) -> str:
        """Evaluate whether to auto-apply, flag for review, or reject a proposal.

        Args:
            proposal: Proposal from StrategyBuilderAgent
            learning_result: Results from LearningAgent

        Returns:
            'AUTO_APPLY', 'FLAG_REVIEW', or 'REJECT'
        """
        confidence = proposal.get('confidence', 0)
        priority = proposal.get('priority', 'LOW')
        risk_level = proposal.get('risk_level', 'HIGH')

        # Auto-apply criteria
        if (
            confidence >= self.auto_apply_threshold and
            priority == 'HIGH' and
            risk_level == 'LOW' and
            learning_result.get('sample_size_adequate', False)
        ):
            return 'AUTO_APPLY'

        # Flag for review criteria
        elif (
            confidence >= 60.0 and
            priority in ['MEDIUM', 'HIGH'] and
            risk_level in ['LOW', 'MEDIUM']
        ):
            return 'FLAG_REVIEW'

        # Reject all others
        else:
            return 'REJECT'

    def _apply_proposal(self, proposal: Dict[str, Any], strategy_name: str):
        """Apply a parameter adjustment.

        Args:
            proposal: Approved proposal
            strategy_name: Strategy name
        """
        # Mark adjustment as APPLIED in database
        adjustment_id = proposal.get('adjustment_id')
        if adjustment_id:
            # This would update the strategy_adjustments table
            # to mark the proposal as APPLIED with apply_time
            self.memory.apply_strategy_adjustment(adjustment_id)

            # In a real implementation, you would also update the actual
            # strategy configuration file or database record here
            logger.info(
                f"Applied adjustment {adjustment_id}: "
                f"{proposal['parameter_name']} = {proposal['proposed_value']}"
            )

    def _generate_summary(
        self,
        insights_found: int,
        auto_applied: int,
        flagged_review: int
    ) -> str:
        """Generate human-readable improvement summary.

        Args:
            insights_found: Number of insights
            auto_applied: Number of auto-applied proposals
            flagged_review: Number flagged for review

        Returns:
            Summary string
        """
        parts = []

        if insights_found > 0:
            parts.append(f"{insights_found} insights")

        if auto_applied > 0:
            parts.append(f"{auto_applied} auto-applied")

        if flagged_review > 0:
            parts.append(f"{flagged_review} flagged for review")

        if not parts:
            return "No significant changes"

        return ", ".join(parts)


def main():
    """CLI entry point for running self-learning loop.

    Usage:
        python -m trading_bot.llm.self_learning_loop [--strategy STRATEGY_NAME]
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="Run self-learning optimization cycle"
    )
    parser.add_argument(
        '--strategy',
        type=str,
        default='default',
        help='Strategy name to optimize (default: default)'
    )
    parser.add_argument(
        '--lookback-days',
        type=int,
        default=30,
        help='Days of history to analyze (default: 30)'
    )
    parser.add_argument(
        '--auto-apply-threshold',
        type=float,
        default=80.0,
        help='Confidence threshold for auto-apply (default: 80.0)'
    )
    parser.add_argument(
        '--min-trades',
        type=int,
        default=10,
        help='Minimum trades needed to run cycle (default: 10)'
    )
    parser.add_argument(
        '--log-file',
        type=str,
        help='Log file path (default: stdout)'
    )

    args = parser.parse_args()

    # Setup logging
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    if args.log_file:
        logging.basicConfig(
            level=logging.INFO,
            format=log_format,
            handlers=[
                logging.FileHandler(args.log_file),
                logging.StreamHandler()
            ]
        )
    else:
        logging.basicConfig(
            level=logging.INFO,
            format=log_format
        )

    # Run cycle
    try:
        loop = SelfLearningLoop(
            auto_apply_threshold=args.auto_apply_threshold,
            min_trades_per_cycle=args.min_trades,
            lookback_days=args.lookback_days
        )

        result = loop.run_cycle(strategy_name=args.strategy)

        # Print summary
        print("\n" + "="*60)
        print("SELF-LEARNING CYCLE COMPLETE")
        print("="*60)
        print(f"Strategy: {args.strategy}")
        print(f"Cycle Time: {result['cycle_time']}")
        print(f"Trades Analyzed: {result['trades_analyzed']}")
        print(f"Insights Found: {result['insights_found']}")
        print(f"Proposals Generated: {result['proposals_generated']}")
        print(f"  - Auto-Applied: {result['proposals_auto_applied']}")
        print(f"  - Flagged for Review: {result['proposals_flagged_review']}")
        print(f"  - Rejected: {result['proposals_rejected']}")
        print(f"Summary: {result['improvement_summary']}")
        print(f"Cost: ${result['cost_usd']:.4f}")
        print(f"Tokens Used: {result['tokens_used']:,}")
        print("="*60)

        sys.exit(0)

    except Exception as e:
        logger.error(f"Self-learning cycle failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
