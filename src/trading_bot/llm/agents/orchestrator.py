"""Agent orchestrator for coordinating multi-agent trading system.

Responsibilities:
- Route tasks to appropriate agents
- Manage agent instances and lifecycle
- Coordinate multi-agent consensus voting
- Track agent performance metrics
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import date
from collections import defaultdict

from .base_agent import BaseAgent
from ..memory_service import AgentMemory

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """Coordinates multiple agents for collaborative trading decisions.

    Manages agent registration, task routing, and multi-agent voting.
    Tracks daily performance metrics for each agent.
    """

    def __init__(self, memory: Optional[AgentMemory] = None):
        """Initialize orchestrator with shared memory.

        Args:
            memory: Shared AgentMemory instance (creates new if None)
        """
        self.memory = memory or AgentMemory()
        self.agents: Dict[str, BaseAgent] = {}

        # Track daily metrics (reset at midnight)
        self._daily_metrics = defaultdict(lambda: {
            'tasks_completed': 0,
            'total_latency': 0,
            'total_cost': 0,
            'successes': 0,
            'failures': 0,
            'confidence_sum': 0.0
        })
        self._last_metrics_date = date.today()

    def register_agent(self, agent: BaseAgent) -> None:
        """Register an agent with the orchestrator.

        Args:
            agent: Agent instance to register

        Raises:
            ValueError: If agent name already registered
        """
        if agent.agent_name in self.agents:
            raise ValueError(f"Agent '{agent.agent_name}' already registered")

        self.agents[agent.agent_name] = agent
        logger.info(f"Registered agent: {agent.agent_name}")

    def get_agent(self, agent_name: str) -> Optional[BaseAgent]:
        """Get registered agent by name.

        Args:
            agent_name: Name of agent to retrieve

        Returns:
            Agent instance or None if not found
        """
        return self.agents.get(agent_name)

    def route_task(self, agent_name: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Route task to specific agent and track metrics.

        Args:
            agent_name: Name of agent to execute task
            context: Input context for agent

        Returns:
            Agent execution result with added metadata

        Raises:
            ValueError: If agent not registered
        """
        agent = self.get_agent(agent_name)
        if not agent:
            raise ValueError(f"Agent '{agent_name}' not registered")

        logger.info(f"Routing task to {agent_name}")

        try:
            # Execute agent task
            result = agent.execute(context)

            # Track success metrics
            self._update_metrics(
                agent_name=agent_name,
                success=True,
                latency_ms=result.get('latency_ms', 0),
                cost_usd=result.get('cost_usd', 0.0),
                confidence=result.get('confidence', 0.0)
            )

            return {
                **result,
                'agent_name': agent_name,
                'success': True
            }

        except Exception as e:
            logger.error(f"Agent {agent_name} failed: {e}")

            # Track failure metrics
            self._update_metrics(
                agent_name=agent_name,
                success=False
            )

            return {
                'agent_name': agent_name,
                'success': False,
                'error': str(e)
            }

    def multi_agent_consensus(
        self,
        agent_names: List[str],
        context: Dict[str, Any],
        min_agreement: int = 2
    ) -> Dict[str, Any]:
        """Execute multi-agent voting for consensus decision.

        Example use case: 3 agents vote on whether to enter a trade.
        If 2/3 agree (min_agreement=2), execute the trade.

        Args:
            agent_names: List of agent names to consult
            context: Shared input context for all agents
            min_agreement: Minimum agents that must agree for consensus

        Returns:
            {
                'consensus_reached': bool,
                'decision': Any,           # The agreed-upon decision
                'votes': List[Dict],       # Individual agent votes
                'agreement_count': int,    # How many agents agreed
                'confidence_avg': float    # Average confidence of agreeing agents
            }
        """
        if len(agent_names) < min_agreement:
            raise ValueError(
                f"Need at least {min_agreement} agents, got {len(agent_names)}"
            )

        logger.info(
            f"Multi-agent consensus: {agent_names} (min_agreement={min_agreement})"
        )

        # Collect votes from all agents
        votes = []
        for agent_name in agent_names:
            result = self.route_task(agent_name, context)

            if result.get('success'):
                votes.append({
                    'agent_name': agent_name,
                    'decision': result.get('decision'),
                    'confidence': result.get('confidence', 0.0),
                    'reasoning': result.get('reasoning', '')
                })
            else:
                logger.warning(f"{agent_name} failed to vote: {result.get('error')}")

        # Count votes by decision
        decision_counts = defaultdict(lambda: {
            'count': 0,
            'confidence_sum': 0.0,
            'agents': []
        })

        for vote in votes:
            decision = str(vote['decision'])  # Normalize to string for counting
            decision_counts[decision]['count'] += 1
            decision_counts[decision]['confidence_sum'] += vote['confidence']
            decision_counts[decision]['agents'].append(vote['agent_name'])

        # Find majority decision
        if not decision_counts:
            return {
                'consensus_reached': False,
                'decision': None,
                'votes': votes,
                'agreement_count': 0,
                'confidence_avg': 0.0
            }

        # Get decision with most votes
        majority_decision = max(
            decision_counts.items(),
            key=lambda x: x[1]['count']
        )

        decision_str, stats = majority_decision
        agreement_count = stats['count']
        consensus_reached = agreement_count >= min_agreement

        # Calculate average confidence of agreeing agents
        confidence_avg = (
            stats['confidence_sum'] / agreement_count
            if agreement_count > 0 else 0.0
        )

        logger.info(
            f"Consensus: {consensus_reached} "
            f"({agreement_count}/{len(votes)} agreed on '{decision_str}')"
        )

        return {
            'consensus_reached': consensus_reached,
            'decision': decision_str,
            'votes': votes,
            'agreement_count': agreement_count,
            'confidence_avg': confidence_avg,
            'all_decision_counts': dict(decision_counts)
        }

    def _update_metrics(
        self,
        agent_name: str,
        success: bool,
        latency_ms: int = 0,
        cost_usd: float = 0.0,
        confidence: float = 0.0
    ) -> None:
        """Update daily metrics for an agent.

        Args:
            agent_name: Name of agent
            success: Whether task succeeded
            latency_ms: Task latency
            cost_usd: Task cost
            confidence: Agent confidence score
        """
        # Check if new day (reset metrics)
        today = date.today()
        if today != self._last_metrics_date:
            self._flush_daily_metrics()
            self._last_metrics_date = today

        # Update in-memory metrics
        metrics = self._daily_metrics[agent_name]
        metrics['tasks_completed'] += 1
        metrics['total_latency'] += latency_ms
        metrics['total_cost'] += cost_usd

        if success:
            metrics['successes'] += 1
            metrics['confidence_sum'] += confidence
        else:
            metrics['failures'] += 1

    def _flush_daily_metrics(self) -> None:
        """Flush daily metrics to database.

        Writes accumulated metrics to agent_metrics table and resets counters.
        """
        for agent_name, metrics in self._daily_metrics.items():
            if metrics['tasks_completed'] == 0:
                continue

            # Calculate aggregates
            avg_latency = (
                metrics['total_latency'] // metrics['tasks_completed']
                if metrics['tasks_completed'] > 0 else 0
            )

            success_rate = (
                (metrics['successes'] / metrics['tasks_completed']) * 100
                if metrics['tasks_completed'] > 0 else 0.0
            )

            avg_confidence = (
                metrics['confidence_sum'] / metrics['successes']
                if metrics['successes'] > 0 else 0.0
            )

            # Store in database
            self.memory.upsert_agent_metrics(
                agent_name=agent_name,
                date=self._last_metrics_date,
                tasks_completed=metrics['tasks_completed'],
                avg_latency_ms=avg_latency,
                success_rate=success_rate,
                avg_confidence=avg_confidence,
                cost_usd=metrics['total_cost']
            )

            logger.info(
                f"Flushed metrics for {agent_name} ({self._last_metrics_date}): "
                f"{metrics['tasks_completed']} tasks, "
                f"${metrics['total_cost']:.4f} cost, "
                f"{success_rate:.1f}% success rate"
            )

        # Reset metrics
        self._daily_metrics.clear()

    def flush_metrics_now(self) -> None:
        """Manually flush current metrics to database.

        Useful for shutdown or end-of-day processing.
        """
        self._flush_daily_metrics()

    def __enter__(self):
        """Context manager entry."""
        self.memory.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - flush metrics and cleanup."""
        self.flush_metrics_now()
        self.memory.__exit__(exc_type, exc_val, exc_tb)
