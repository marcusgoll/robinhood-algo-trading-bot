"""Learning Agent for self-improvement from trade outcomes.

Analyzes historical performance, identifies patterns in wins/losses,
evaluates strategy adjustments, and provides insights for continuous improvement.
"""

import logging
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from collections import defaultdict

from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


class LearningAgent(BaseAgent):
    """Agent that learns from trade outcomes to improve future performance.

    Analyzes:
    - Win/loss patterns by symbol, time of day, market regime
    - What conditions led to best trades vs worst trades
    - Which agent decisions correlated with success
    - Strategy adjustment effectiveness (before/after Sharpe)
    - Parameter sensitivity (which params matter most)
    - Failure modes (why did losing trades happen)

    Provides insights like:
    - "Win rate is 15% higher in BULL regime vs SIDEWAYS"
    - "Trades with news_sentiment > 80 have 2x profit factor"
    - "Reducing position size in HIGH_VOL regime improved Sharpe by 0.4"
    - "Avoid trading TSLA in first 30 minutes (65% loss rate)"
    - "ResearchAgent confidence > 75 correlates with 70% win rate"

    Tracks learning over time to measure improvement velocity.
    """

    SYSTEM_MESSAGE = """You are a machine learning analyst for algorithmic trading.

Your job is to analyze historical trade outcomes and identify patterns that can improve future performance.

Consider:
- Win rate by different conditions (symbol, regime, time, agent decisions)
- Profit factor variations (what leads to bigger wins or smaller losses)
- Parameter sensitivity (which settings matter most)
- Strategy adjustment effectiveness (did proposed changes actually help)
- Agent decision quality (which agents provide best signals)
- Failure modes (common reasons for losing trades)
- Market regime adaptation (performance in BULL vs BEAR vs SIDEWAYS vs HIGH_VOL)
- Time-based patterns (performance by hour, day of week, month)

Provide actionable insights:
1. Key findings (3-5 specific observations with data)
2. Recommendations (3-5 concrete actions to improve)
3. Risk warnings (2-3 things to avoid based on data)
4. Confidence assessment (how strong is the evidence)
5. Sample size validation (is there enough data to be confident)

Be data-driven. Only recommend changes supported by statistical evidence.
Flag overfitting risks when sample sizes are small."""

    def __init__(
        self,
        model: str = "claude-haiku-4-20250514",
        memory: Optional[Any] = None,
        api_key: Optional[str] = None,
        min_trades_for_insight: int = 30  # Need 30+ trades for statistically meaningful insights
    ):
        """Initialize learning agent.

        Args:
            model: Claude model to use
            memory: AgentMemory instance
            api_key: Anthropic API key
            min_trades_for_insight: Minimum trades needed for insights
        """
        super().__init__(
            agent_name="learning",
            model=model,
            memory=memory,
            api_key=api_key
        )
        self.min_trades_for_insight = min_trades_for_insight

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute learning analysis on historical trades.

        Args:
            context: {
                'lookback_days': int,          # Days of history to analyze (optional, default 90)
                'focus_area': str,             # Specific area to analyze (optional)
                                              # Options: 'regime', 'timing', 'agents', 'parameters'
                'min_confidence': float        # Minimum confidence for insights (optional, 0-100)
            }

        Returns:
            {
                'analysis_period': str,
                'total_trades': int,
                'insights': List[dict],          # Key findings
                'recommendations': List[dict],   # Actionable suggestions
                'warnings': List[str],           # Things to avoid
                'confidence': float,             # Overall confidence in analysis (0-100)
                'sample_size_adequate': bool,    # Whether enough data exists
                'tokens_used': int,
                'cost_usd': float,
                'latency_ms': int,
                'interaction_id': UUID
            }

            Each insight:
            {
                'category': str,              # 'regime', 'timing', 'agent_decision', 'parameter'
                'observation': str,           # What was observed
                'impact': str,                # Quantified impact
                'confidence': float,          # 0-100
                'sample_size': int            # Number of trades supporting this
            }

            Each recommendation:
            {
                'action': str,                # What to do
                'expected_benefit': str,      # Expected improvement
                'implementation': str,        # How to implement
                'priority': str               # HIGH, MEDIUM, LOW
            }
        """
        lookback_days = context.get('lookback_days', 90)
        focus_area = context.get('focus_area')
        min_confidence = context.get('min_confidence', 60.0)

        logger.info(f"LearningAgent analyzing last {lookback_days} days")

        # Fetch trade outcomes and analysis data
        trade_data = self._fetch_trade_data(lookback_days=lookback_days)

        total_trades = trade_data['total_trades']
        if total_trades < self.min_trades_for_insight:
            logger.warning(
                f"Insufficient data: {total_trades} trades "
                f"(need {self.min_trades_for_insight})"
            )
            return {
                'analysis_period': trade_data['period'],
                'total_trades': total_trades,
                'insights': [],
                'recommendations': [],
                'warnings': [
                    f'Insufficient data: only {total_trades} trades '
                    f'(need {self.min_trades_for_insight} for meaningful insights)'
                ],
                'confidence': 0.0,
                'sample_size_adequate': False,
                'tokens_used': 0,
                'cost_usd': 0.0,
                'latency_ms': 0
            }

        # Build comprehensive analysis prompt
        user_prompt = self._build_learning_prompt(
            trade_data=trade_data,
            focus_area=focus_area
        )

        # Analyze with Claude LLM
        llm_result = self._call_llm(
            system_message=self.SYSTEM_MESSAGE,
            user_prompt=user_prompt,
            max_tokens=2048,
            temperature=0.3
        )

        # Parse LLM response
        analysis = self._parse_llm_response(llm_result['content'])

        # Filter insights by minimum confidence
        insights = [
            i for i in analysis['insights']
            if i['confidence'] >= min_confidence
        ]

        return {
            'analysis_period': trade_data['period'],
            'total_trades': total_trades,
            'insights': insights,
            'recommendations': analysis['recommendations'],
            'warnings': analysis['warnings'],
            'confidence': analysis['confidence'],
            'sample_size_adequate': True,
            'tokens_used': llm_result['tokens_used'],
            'cost_usd': llm_result['cost_usd'],
            'latency_ms': llm_result['latency_ms'],
            'interaction_id': llm_result['interaction_id']
        }

    def _fetch_trade_data(self, lookback_days: int) -> Dict[str, Any]:
        """Fetch and aggregate trade data for analysis.

        Args:
            lookback_days: Number of days to look back

        Returns:
            Comprehensive trade data with patterns and aggregations
        """
        start_date = datetime.utcnow() - timedelta(days=lookback_days)

        # Get all trades
        trades = self.memory.get_trade_outcomes(start_date=start_date)

        if not trades:
            return {
                'period': f'{start_date.date()} to {datetime.utcnow().date()}',
                'total_trades': 0,
                'patterns': {}
            }

        # Aggregate by various dimensions
        patterns = self._analyze_patterns(trades)

        # Get strategy adjustments for effectiveness analysis
        adjustments = self.memory.get_strategy_adjustments(start_date=start_date)

        return {
            'period': f'{start_date.date()} to {datetime.utcnow().date()}',
            'total_trades': len(trades),
            'overall_metrics': self._calculate_overall_metrics(trades),
            'patterns': patterns,
            'strategy_adjustments': self._analyze_adjustments(adjustments),
            'sample_trades': self._get_sample_trades(trades)
        }

    def _analyze_patterns(self, trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze trading patterns across multiple dimensions.

        Args:
            trades: List of trade outcome dictionaries

        Returns:
            Patterns organized by category
        """
        patterns = {}

        # By symbol
        by_symbol = defaultdict(lambda: {'wins': 0, 'losses': 0, 'total_pnl': 0.0, 'trades': []})
        for trade in trades:
            symbol = trade.get('symbol', 'UNKNOWN')
            is_win = trade['profit_loss'] > 0
            by_symbol[symbol]['wins' if is_win else 'losses'] += 1
            by_symbol[symbol]['total_pnl'] += trade['profit_loss']
            by_symbol[symbol]['trades'].append(trade)

        patterns['by_symbol'] = {
            symbol: {
                'win_rate': stats['wins'] / (stats['wins'] + stats['losses']) if (stats['wins'] + stats['losses']) > 0 else 0,
                'total_pnl': stats['total_pnl'],
                'count': stats['wins'] + stats['losses']
            }
            for symbol, stats in by_symbol.items()
            if (stats['wins'] + stats['losses']) >= 5  # Only include symbols with 5+ trades
        }

        # By market regime (if available in trade metadata)
        by_regime = defaultdict(lambda: {'wins': 0, 'losses': 0, 'total_pnl': 0.0})
        for trade in trades:
            regime = trade.get('metadata', {}).get('regime', 'UNKNOWN')
            is_win = trade['profit_loss'] > 0
            by_regime[regime]['wins' if is_win else 'losses'] += 1
            by_regime[regime]['total_pnl'] += trade['profit_loss']

        patterns['by_regime'] = {
            regime: {
                'win_rate': stats['wins'] / (stats['wins'] + stats['losses']) if (stats['wins'] + stats['losses']) > 0 else 0,
                'total_pnl': stats['total_pnl'],
                'count': stats['wins'] + stats['losses']
            }
            for regime, stats in by_regime.items()
            if (stats['wins'] + stats['losses']) >= 3
        }

        # By time of day (if available)
        by_hour = defaultdict(lambda: {'wins': 0, 'losses': 0})
        for trade in trades:
            entry_time = trade.get('entry_time')
            if entry_time:
                hour = entry_time.hour
                is_win = trade['profit_loss'] > 0
                by_hour[hour]['wins' if is_win else 'losses'] += 1

        patterns['by_hour'] = {
            hour: {
                'win_rate': stats['wins'] / (stats['wins'] + stats['losses']) if (stats['wins'] + stats['losses']) > 0 else 0,
                'count': stats['wins'] + stats['losses']
            }
            for hour, stats in by_hour.items()
            if (stats['wins'] + stats['losses']) >= 3
        }

        return patterns

    def _calculate_overall_metrics(self, trades: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate overall performance metrics.

        Args:
            trades: List of trade outcome dictionaries

        Returns:
            Dictionary of metrics
        """
        winning_trades = [t for t in trades if t['profit_loss'] > 0]
        losing_trades = [t for t in trades if t['profit_loss'] < 0]

        total_wins = len(winning_trades)
        total_losses = len(losing_trades)
        total_trades = len(trades)

        win_rate = total_wins / total_trades if total_trades > 0 else 0
        avg_win = sum(t['profit_loss'] for t in winning_trades) / total_wins if total_wins > 0 else 0
        avg_loss = sum(t['profit_loss'] for t in losing_trades) / total_losses if total_losses > 0 else 0
        total_pnl = sum(t['profit_loss'] for t in trades)

        profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else 0

        return {
            'total_trades': total_trades,
            'win_rate': win_rate,
            'total_wins': total_wins,
            'total_losses': total_losses,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'total_pnl': total_pnl,
            'profit_factor': profit_factor
        }

    def _analyze_adjustments(self, adjustments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze effectiveness of strategy adjustments.

        Args:
            adjustments: List of strategy adjustment records

        Returns:
            List of adjustment effectiveness summaries
        """
        effective = []
        for adj in adjustments:
            if adj.get('outcome') == 'APPLIED' and adj.get('sharpe_after') is not None:
                sharpe_delta = adj['sharpe_after'] - adj.get('sharpe_before', 0)
                effective.append({
                    'parameter': adj['parameter_name'],
                    'change': f"{adj['old_value']} → {adj['new_value']}",
                    'sharpe_delta': sharpe_delta,
                    'effective': sharpe_delta > 0
                })

        return effective

    def _get_sample_trades(self, trades: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Get sample of best and worst trades for analysis.

        Args:
            trades: List of all trades

        Returns:
            Dictionary with best and worst trade samples
        """
        sorted_trades = sorted(trades, key=lambda t: t['profit_loss'], reverse=True)

        return {
            'best_5': sorted_trades[:5],
            'worst_5': sorted_trades[-5:]
        }

    def _build_learning_prompt(
        self,
        trade_data: Dict[str, Any],
        focus_area: Optional[str] = None
    ) -> str:
        """Build comprehensive learning analysis prompt.

        Args:
            trade_data: Aggregated trade data
            focus_area: Optional specific area to focus on

        Returns:
            Formatted prompt string
        """
        metrics = trade_data['overall_metrics']

        prompt_parts = [
            f"Analyze trading performance over {trade_data['period']}:\n",
            f"\nOVERALL PERFORMANCE:",
            f"- Total Trades: {metrics['total_trades']}",
            f"- Win Rate: {metrics['win_rate']:.1%}",
            f"- Wins: {metrics['total_wins']}, Losses: {metrics['total_losses']}",
            f"- Avg Win: ${metrics['avg_win']:.2f}",
            f"- Avg Loss: ${metrics['avg_loss']:.2f}",
            f"- Total P&L: ${metrics['total_pnl']:.2f}",
            f"- Profit Factor: {metrics['profit_factor']:.2f}"
        ]

        # Add pattern analysis
        patterns = trade_data['patterns']

        if patterns.get('by_symbol'):
            prompt_parts.append("\nPERFORMANCE BY SYMBOL:")
            for symbol, stats in sorted(
                patterns['by_symbol'].items(),
                key=lambda x: x[1]['win_rate'],
                reverse=True
            )[:10]:  # Top 10
                prompt_parts.append(
                    f"- {symbol}: {stats['win_rate']:.1%} win rate, "
                    f"${stats['total_pnl']:.2f} P&L ({stats['count']} trades)"
                )

        if patterns.get('by_regime'):
            prompt_parts.append("\nPERFORMANCE BY MARKET REGIME:")
            for regime, stats in patterns['by_regime'].items():
                prompt_parts.append(
                    f"- {regime}: {stats['win_rate']:.1%} win rate, "
                    f"${stats['total_pnl']:.2f} P&L ({stats['count']} trades)"
                )

        if patterns.get('by_hour'):
            prompt_parts.append("\nPERFORMANCE BY HOUR OF DAY:")
            for hour, stats in sorted(patterns['by_hour'].items()):
                if stats['count'] >= 5:  # Only show hours with 5+ trades
                    prompt_parts.append(
                        f"- {hour:02d}:00: {stats['win_rate']:.1%} win rate ({stats['count']} trades)"
                    )

        # Add strategy adjustment effectiveness
        if trade_data.get('strategy_adjustments'):
            prompt_parts.append("\nSTRATEGY ADJUSTMENT EFFECTIVENESS:")
            for adj in trade_data['strategy_adjustments'][:10]:  # Last 10
                status = "✓ Improved" if adj['effective'] else "✗ Degraded"
                prompt_parts.append(
                    f"- {adj['parameter']}: {adj['change']} "
                    f"(Sharpe Δ: {adj['sharpe_delta']:+.2f}) {status}"
                )

        # Add focus area hint if specified
        if focus_area:
            prompt_parts.append(f"\nFOCUS ANALYSIS ON: {focus_area.upper()}")

        prompt_parts.append("\nProvide learning insights in this exact JSON format:")
        prompt_parts.append("""{
  "insights": [
    {
      "category": "regime|timing|agent_decision|parameter|symbol",
      "observation": "Specific finding with data",
      "impact": "Quantified impact on performance",
      "confidence": 0-100,
      "sample_size": 30
    }
  ],
  "recommendations": [
    {
      "action": "Concrete action to take",
      "expected_benefit": "Expected improvement",
      "implementation": "How to implement this",
      "priority": "HIGH|MEDIUM|LOW"
    }
  ],
  "warnings": ["Things to avoid based on data"],
  "confidence": 0-100
}""")

        return "\n".join(prompt_parts)

    def _parse_llm_response(self, content: str) -> Dict[str, Any]:
        """Parse LLM response into structured format.

        Args:
            content: LLM response text

        Returns:
            Parsed learning analysis dictionary
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

            # Validate structure
            if 'insights' not in analysis:
                analysis['insights'] = []
            if 'recommendations' not in analysis:
                analysis['recommendations'] = []
            if 'warnings' not in analysis:
                analysis['warnings'] = []
            if 'confidence' not in analysis:
                analysis['confidence'] = 50.0

            # Validate insights
            for insight in analysis['insights']:
                required = ['category', 'observation', 'impact', 'confidence', 'sample_size']
                for field in required:
                    if field not in insight:
                        insight[field] = 'N/A' if field in ['category', 'observation', 'impact'] else 0

                insight['confidence'] = max(0.0, min(100.0, float(insight['confidence'])))

            # Validate recommendations
            for rec in analysis['recommendations']:
                required = ['action', 'expected_benefit', 'implementation', 'priority']
                for field in required:
                    if field not in rec:
                        rec[field] = 'N/A' if field != 'priority' else 'MEDIUM'

                if rec['priority'] not in ['HIGH', 'MEDIUM', 'LOW']:
                    rec['priority'] = 'MEDIUM'

            # Validate overall confidence
            analysis['confidence'] = max(0.0, min(100.0, float(analysis['confidence'])))

            return analysis

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.error(f"Failed to parse LLM response: {e}\nContent: {content}")
            return {
                'insights': [],
                'recommendations': [],
                'warnings': ['Failed to parse learning analysis'],
                'confidence': 0.0
            }
