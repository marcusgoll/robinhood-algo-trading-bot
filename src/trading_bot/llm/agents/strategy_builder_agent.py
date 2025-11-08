"""Strategy Builder Agent for parameter optimization and self-improvement.

Analyzes historical trade outcomes and proposes strategy parameter adjustments
to improve performance over time. Uses reinforcement learning principles.
"""

import logging
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from uuid import UUID

from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


class StrategyBuilderAgent(BaseAgent):
    """Agent that proposes strategy parameter adjustments based on performance.

    Analyzes:
    - Historical trade outcomes (win rate, avg profit/loss, sharpe ratio)
    - Parameter correlation with successful trades
    - Recent strategy adjustment performance
    - Market regime changes requiring adaptation

    Proposes adjustments for:
    - Entry/exit thresholds (RSI, MACD, moving averages)
    - Position sizing parameters (Kelly fraction, max position size)
    - Risk management (stop loss %, take profit %, risk/reward ratio)
    - Timeframe selection (5min, 15min, 1hr, 4hr, daily)
    - Indicator weights in ensemble models

    Tracks:
    - Sharpe ratio before/after each adjustment
    - Win rate improvement
    - Average profit/loss changes
    - Parameter stability (avoid over-fitting)
    """

    SYSTEM_MESSAGE = """You are a quantitative strategy optimization expert for algorithmic trading.

Your job is to analyze historical performance and propose parameter adjustments to improve results.

Consider:
- Win rate trends (increasing or decreasing over time)
- Profit/loss distribution (are losses getting larger?)
- Sharpe ratio changes (risk-adjusted returns)
- Parameter correlation with wins (which settings led to profitable trades?)
- Market regime shifts (parameters that worked in bull markets may fail in bear markets)
- Overfitting risk (avoid over-tuning to recent data)
- Stability vs adaptation tradeoff (gradual changes vs aggressive pivots)

Analyze performance data and propose:
1. Parameter name (e.g., "rsi_oversold_threshold", "stop_loss_pct", "kelly_fraction")
2. Current value
3. Proposed new value
4. Expected impact (INCREASE_WIN_RATE, REDUCE_LOSSES, IMPROVE_SHARPE, ADAPT_TO_REGIME)
5. Confidence score (0-100)
6. Reasoning (2-3 sentences explaining why this change should help)
7. Risk level (LOW, MEDIUM, HIGH) - how likely is this to hurt performance

Be conservative. Only propose changes with strong evidence.
Prefer gradual adjustments over dramatic shifts.
Track A/B test results to validate proposals."""

    def __init__(
        self,
        model: str = "claude-haiku-4-20250514",
        memory: Optional[Any] = None,
        api_key: Optional[str] = None,
        min_trades_for_analysis: int = 20,  # Need at least 20 trades for statistical significance
        lookback_days: int = 30  # Analyze last 30 days by default
    ):
        """Initialize strategy builder agent.

        Args:
            model: Claude model to use
            memory: AgentMemory instance
            api_key: Anthropic API key
            min_trades_for_analysis: Minimum trades needed before proposing changes
            lookback_days: Number of days to analyze
        """
        super().__init__(
            agent_name="strategy_builder",
            model=model,
            memory=memory,
            api_key=api_key
        )
        self.min_trades_for_analysis = min_trades_for_analysis
        self.lookback_days = lookback_days

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute strategy analysis and propose parameter adjustments.

        Args:
            context: {
                'strategy_name': str,           # Strategy to analyze (optional)
                'focus_parameters': List[str],  # Specific params to tune (optional)
                'lookback_days': int,           # Override default lookback (optional)
                'min_confidence': float,        # Minimum confidence for proposals (optional, 0-100)
                'max_proposals': int            # Max number of proposals (optional, default 3)
            }

        Returns:
            {
                'strategy_name': str,
                'analysis_period': str,              # Date range analyzed
                'trades_analyzed': int,
                'current_metrics': dict,             # Current win rate, sharpe, avg profit/loss
                'proposals': List[dict],             # Proposed adjustments
                'warnings': List[str],               # Any concerns (e.g., insufficient data)
                'tokens_used': int,
                'cost_usd': float,
                'latency_ms': int,
                'interaction_id': UUID
            }

            Each proposal in 'proposals':
            {
                'parameter_name': str,
                'current_value': float,
                'proposed_value': float,
                'expected_impact': str,          # INCREASE_WIN_RATE, REDUCE_LOSSES, etc.
                'confidence': float,             # 0-100
                'reasoning': str,
                'risk_level': str,               # LOW, MEDIUM, HIGH
                'adjustment_id': UUID            # Stored in strategy_adjustments table
            }
        """
        strategy_name = context.get('strategy_name', 'default')
        lookback_days = context.get('lookback_days', self.lookback_days)
        min_confidence = context.get('min_confidence', 60.0)
        max_proposals = context.get('max_proposals', 3)

        logger.info(f"StrategyBuilderAgent analyzing {strategy_name} (last {lookback_days} days)")

        # Fetch historical performance data
        performance_data = self._fetch_performance_data(
            strategy_name=strategy_name,
            lookback_days=lookback_days
        )

        # Check if we have enough data
        trades_analyzed = performance_data['total_trades']
        if trades_analyzed < self.min_trades_for_analysis:
            logger.warning(
                f"Insufficient data: {trades_analyzed} trades "
                f"(need {self.min_trades_for_analysis})"
            )
            return {
                'strategy_name': strategy_name,
                'analysis_period': performance_data['period'],
                'trades_analyzed': trades_analyzed,
                'current_metrics': performance_data['metrics'],
                'proposals': [],
                'warnings': [
                    f'Insufficient data: only {trades_analyzed} trades '
                    f'(need {self.min_trades_for_analysis})'
                ],
                'tokens_used': 0,
                'cost_usd': 0.0,
                'latency_ms': 0
            }

        # Fetch recent strategy adjustments to track what we've already tried
        recent_adjustments = self._fetch_recent_adjustments(
            strategy_name=strategy_name,
            lookback_days=lookback_days
        )

        # Build user prompt with performance data
        user_prompt = self._build_analysis_prompt(
            strategy_name=strategy_name,
            performance_data=performance_data,
            recent_adjustments=recent_adjustments,
            focus_parameters=context.get('focus_parameters'),
            max_proposals=max_proposals
        )

        # Analyze with Claude LLM
        llm_result = self._call_llm(
            system_message=self.SYSTEM_MESSAGE,
            user_prompt=user_prompt,
            max_tokens=2048,
            temperature=0.4  # Slightly higher for creative parameter exploration
        )

        # Parse LLM response
        analysis = self._parse_llm_response(llm_result['content'])

        # Filter proposals by minimum confidence
        proposals = [
            p for p in analysis['proposals']
            if p['confidence'] >= min_confidence
        ]

        # Store proposals in database as PENDING adjustments
        for proposal in proposals:
            adjustment_id = self.memory.propose_strategy_adjustment(
                strategy_name=strategy_name,
                parameter_name=proposal['parameter_name'],
                old_value=proposal['current_value'],
                new_value=proposal['proposed_value'],
                reasoning=proposal['reasoning'],
                expected_impact=proposal['expected_impact']
            )
            proposal['adjustment_id'] = adjustment_id

        return {
            'strategy_name': strategy_name,
            'analysis_period': performance_data['period'],
            'trades_analyzed': trades_analyzed,
            'current_metrics': performance_data['metrics'],
            'proposals': proposals,
            'warnings': analysis.get('warnings', []),
            'tokens_used': llm_result['tokens_used'],
            'cost_usd': llm_result['cost_usd'],
            'latency_ms': llm_result['latency_ms'],
            'interaction_id': llm_result['interaction_id']
        }

    def _fetch_performance_data(
        self,
        strategy_name: str,
        lookback_days: int
    ) -> Dict[str, Any]:
        """Fetch historical trade performance from database.

        Args:
            strategy_name: Strategy to analyze
            lookback_days: Number of days to look back

        Returns:
            Dictionary with performance metrics and trade details
        """
        start_date = datetime.utcnow() - timedelta(days=lookback_days)

        # Query trade_outcomes table
        trades = self.memory.get_trade_outcomes(
            strategy_name=strategy_name,
            start_date=start_date
        )

        if not trades:
            return {
                'period': f'{start_date.date()} to {datetime.utcnow().date()}',
                'total_trades': 0,
                'metrics': {},
                'trades': []
            }

        # Calculate metrics
        total_trades = len(trades)
        winning_trades = [t for t in trades if t['profit_loss'] > 0]
        losing_trades = [t for t in trades if t['profit_loss'] < 0]

        win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0.0
        avg_profit = sum(t['profit_loss'] for t in winning_trades) / len(winning_trades) if winning_trades else 0.0
        avg_loss = sum(t['profit_loss'] for t in losing_trades) / len(losing_trades) if losing_trades else 0.0
        total_pnl = sum(t['profit_loss'] for t in trades)

        # Calculate Sharpe ratio approximation (daily returns)
        returns = [t['profit_loss'] / t['entry_price'] for t in trades]
        avg_return = sum(returns) / len(returns) if returns else 0.0
        return_std = (sum((r - avg_return) ** 2 for r in returns) / len(returns)) ** 0.5 if returns else 0.0
        sharpe_ratio = (avg_return / return_std) * (252 ** 0.5) if return_std > 0 else 0.0

        metrics = {
            'win_rate': win_rate,
            'avg_profit': avg_profit,
            'avg_loss': avg_loss,
            'total_pnl': total_pnl,
            'sharpe_ratio': sharpe_ratio,
            'profit_factor': abs(avg_profit / avg_loss) if avg_loss != 0 else 0.0,
            'max_consecutive_losses': self._calculate_max_consecutive_losses(trades)
        }

        return {
            'period': f'{start_date.date()} to {datetime.utcnow().date()}',
            'total_trades': total_trades,
            'metrics': metrics,
            'trades': trades
        }

    def _calculate_max_consecutive_losses(self, trades: List[Dict[str, Any]]) -> int:
        """Calculate maximum consecutive losing trades.

        Args:
            trades: List of trade outcome dictionaries

        Returns:
            Maximum consecutive losses
        """
        max_consecutive = 0
        current_consecutive = 0

        for trade in sorted(trades, key=lambda t: t['entry_time']):
            if trade['profit_loss'] < 0:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 0

        return max_consecutive

    def _fetch_recent_adjustments(
        self,
        strategy_name: str,
        lookback_days: int
    ) -> List[Dict[str, Any]]:
        """Fetch recent strategy adjustments from database.

        Args:
            strategy_name: Strategy name
            lookback_days: Number of days to look back

        Returns:
            List of recent adjustments with outcomes
        """
        start_date = datetime.utcnow() - timedelta(days=lookback_days)

        adjustments = self.memory.get_strategy_adjustments(
            strategy_name=strategy_name,
            start_date=start_date
        )

        return adjustments

    def _build_analysis_prompt(
        self,
        strategy_name: str,
        performance_data: Dict[str, Any],
        recent_adjustments: List[Dict[str, Any]],
        focus_parameters: Optional[List[str]] = None,
        max_proposals: int = 3
    ) -> str:
        """Build user prompt for strategy analysis.

        Args:
            strategy_name: Strategy name
            performance_data: Historical performance metrics
            recent_adjustments: Recent parameter changes
            focus_parameters: Specific parameters to focus on
            max_proposals: Maximum number of proposals

        Returns:
            Formatted prompt string
        """
        metrics = performance_data['metrics']

        prompt_parts = [
            f"Analyze strategy '{strategy_name}' and propose parameter adjustments:\n",
            f"\nPERFORMANCE METRICS ({performance_data['period']}):",
            f"- Total Trades: {performance_data['total_trades']}",
            f"- Win Rate: {metrics.get('win_rate', 0):.1%}",
            f"- Average Profit: ${metrics.get('avg_profit', 0):.2f}",
            f"- Average Loss: ${metrics.get('avg_loss', 0):.2f}",
            f"- Total P&L: ${metrics.get('total_pnl', 0):.2f}",
            f"- Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.2f}",
            f"- Profit Factor: {metrics.get('profit_factor', 0):.2f}",
            f"- Max Consecutive Losses: {metrics.get('max_consecutive_losses', 0)}"
        ]

        # Add recent adjustments if any
        if recent_adjustments:
            prompt_parts.append(f"\nRECENT ADJUSTMENTS:")
            for adj in recent_adjustments[:5]:  # Show last 5
                outcome = adj.get('outcome', 'PENDING')
                sharpe_change = adj.get('sharpe_after', 0) - adj.get('sharpe_before', 0)
                prompt_parts.append(
                    f"- {adj['parameter_name']}: {adj['old_value']} → {adj['new_value']} "
                    f"(Outcome: {outcome}, Sharpe Δ: {sharpe_change:+.2f})"
                )

        # Add focus parameters if specified
        if focus_parameters:
            prompt_parts.append(f"\nFOCUS ON THESE PARAMETERS: {', '.join(focus_parameters)}")

        prompt_parts.append(f"\nPropose up to {max_proposals} parameter adjustments in this exact JSON format:")
        prompt_parts.append("""{
  "proposals": [
    {
      "parameter_name": "rsi_oversold_threshold",
      "current_value": 30.0,
      "proposed_value": 25.0,
      "expected_impact": "INCREASE_WIN_RATE|REDUCE_LOSSES|IMPROVE_SHARPE|ADAPT_TO_REGIME",
      "confidence": 0-100,
      "reasoning": "2-3 sentences explaining why",
      "risk_level": "LOW|MEDIUM|HIGH"
    }
  ],
  "warnings": ["Any concerns about data quality or overfitting"]
}""")

        return "\n".join(prompt_parts)

    def _parse_llm_response(self, content: str) -> Dict[str, Any]:
        """Parse LLM response into structured format.

        Args:
            content: LLM response text

        Returns:
            Parsed analysis dictionary
        """
        try:
            # Try to extract JSON from response
            if "```json" in content:
                start = content.find("```json") + 7
                end = content.find("```", start)
                json_str = content[start:end].strip()
            elif "```" in content:
                start = content.find("```") + 3
                end = content.find("```", start)
                json_str = content[start:end].strip()
            elif "{" in content and "}" in content:
                start = content.find("{")
                end = content.rfind("}") + 1
                json_str = content[start:end]
            else:
                json_str = content

            analysis = json.loads(json_str)

            # Validate proposals
            if 'proposals' not in analysis:
                analysis['proposals'] = []

            for proposal in analysis['proposals']:
                # Validate required fields
                required_fields = [
                    'parameter_name', 'current_value', 'proposed_value',
                    'expected_impact', 'confidence', 'reasoning', 'risk_level'
                ]
                for field in required_fields:
                    if field not in proposal:
                        raise ValueError(f"Missing required field in proposal: {field}")

                # Normalize impact
                impact = proposal['expected_impact'].upper()
                valid_impacts = ['INCREASE_WIN_RATE', 'REDUCE_LOSSES', 'IMPROVE_SHARPE', 'ADAPT_TO_REGIME']
                if impact not in valid_impacts:
                    impact = 'IMPROVE_SHARPE'  # Safe default
                proposal['expected_impact'] = impact

                # Normalize risk level
                risk = proposal['risk_level'].upper()
                if risk not in ['LOW', 'MEDIUM', 'HIGH']:
                    risk = 'MEDIUM'
                proposal['risk_level'] = risk

                # Ensure confidence is float 0-100
                proposal['confidence'] = max(0.0, min(100.0, float(proposal['confidence'])))

            # Ensure warnings is a list
            if 'warnings' not in analysis:
                analysis['warnings'] = []

            return analysis

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.error(f"Failed to parse LLM response: {e}\nContent: {content}")
            # Return empty proposals
            return {
                'proposals': [],
                'warnings': ['Failed to parse strategy analysis']
            }
