"""Risk Manager Agent for position sizing and risk assessment.

Analyzes portfolio metrics and provides position sizing recommendations
using Kelly Criterion, portfolio exposure limits, and risk metrics.
"""

import logging
import json
import math
from typing import Dict, Any, Optional, List

from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


class RiskManagerAgent(BaseAgent):
    """Agent that performs risk assessment and position sizing.

    Analyzes:
    - Current portfolio exposure
    - Historical win rate and average win/loss
    - Kelly Criterion for optimal position sizing
    - Portfolio concentration risk
    - Correlation between positions
    - Maximum drawdown limits

    Provides recommendations for:
    - Position size (shares or % of portfolio)
    - Stop loss level
    - Take profit targets
    - Overall risk approval (APPROVE/REJECT/REDUCE)
    """

    SYSTEM_MESSAGE = """You are a risk management expert for algorithmic trading.

Your job is to assess trade risk and recommend appropriate position sizing.

Consider:
- Portfolio exposure (avoid over-concentration in single position)
- Historical performance (win rate, avg win/loss ratio)
- Volatility and beta (higher risk = smaller position)
- Kelly Criterion for optimal sizing
- Maximum drawdown limits
- Correlation with existing positions
- Market regime (reduce size in high volatility)

Provide:
1. Decision (APPROVE, REDUCE, or REJECT)
2. Recommended position size (% of portfolio)
3. Stop loss level (% below entry)
4. Take profit targets (% above entry)
5. Risk/reward ratio
6. Key risk factors (2-3 concerns)
7. Confidence score (0-100)

Be conservative. Better to size too small than too large.
Reject trades that exceed risk limits or have poor risk/reward."""

    def __init__(
        self,
        model: str = "claude-haiku-4-5",
        memory: Optional[Any] = None,
        api_key: Optional[str] = None,
        max_position_size: float = 0.20,  # Max 20% of portfolio in single position
        max_portfolio_risk: float = 0.02,  # Max 2% portfolio risk per trade
        kelly_fraction: float = 0.25  # Use 25% of full Kelly
    ):
        """Initialize risk manager agent.

        Args:
            model: Claude model to use (default: claude-haiku-4-5, latest as of Oct 2025)

        Args:
            model: Claude model to use
            memory: AgentMemory instance
            api_key: Anthropic API key
            max_position_size: Maximum position size as fraction of portfolio (0.20 = 20%)
            max_portfolio_risk: Maximum portfolio risk per trade (0.02 = 2%)
            kelly_fraction: Fraction of Kelly Criterion to use (0.25 = quarter Kelly)
        """
        super().__init__(
            agent_name="risk_manager",
            model=model,
            memory=memory,
            api_key=api_key
        )
        self.max_position_size = max_position_size
        self.max_portfolio_risk = max_portfolio_risk
        self.kelly_fraction = kelly_fraction

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute risk assessment for a trade.

        Args:
            context: {
                'symbol': str,                    # Stock symbol (required)
                'entry_price': float,             # Proposed entry price (required)
                'portfolio_value': float,         # Total portfolio value (required)
                'cash_available': float,          # Cash available for trading (required)
                'current_positions': List[dict],  # Existing positions (optional)
                'win_rate': float,                # Historical win rate 0-1 (optional)
                'avg_win': float,                 # Average win % (optional)
                'avg_loss': float,                # Average loss % (optional)
                'volatility': float,              # Stock volatility/ATR (optional)
                'beta': float,                    # Stock beta (optional)
                'market_regime': str,             # BULL/BEAR/SIDEWAYS/HIGH_VOL (optional)
                'fundamental_score': float        # Fundamental confidence 0-100 (optional)
            }

        Returns:
            {
                'symbol': str,
                'decision': str,               # APPROVE/REDUCE/REJECT
                'confidence': float,           # 0-100
                'position_size_pct': float,    # Recommended % of portfolio
                'position_size_shares': int,   # Recommended number of shares
                'stop_loss_pct': float,        # Recommended stop loss % below entry
                'take_profit_pct': float,      # Recommended take profit % above entry
                'risk_reward_ratio': float,    # Expected R:R ratio
                'risk_factors': List[str],     # Key concerns
                'reasoning': str,              # Brief explanation
                'kelly_size': float,           # Kelly Criterion size
                'tokens_used': int,
                'cost_usd': float,
                'latency_ms': int,
                'interaction_id': UUID
            }
        """
        symbol = context.get('symbol')
        entry_price = context.get('entry_price')
        portfolio_value = context.get('portfolio_value')
        cash_available = context.get('cash_available')

        if not all([symbol, entry_price, portfolio_value, cash_available]):
            raise ValueError("symbol, entry_price, portfolio_value, cash_available required")

        logger.info(f"RiskManagerAgent assessing {symbol} @ ${entry_price}")

        # Calculate Kelly Criterion position size
        kelly_size = self._calculate_kelly_size(
            win_rate=context.get('win_rate', 0.5),
            avg_win=context.get('avg_win', 0.05),
            avg_loss=context.get('avg_loss', 0.03)
        )

        # Calculate portfolio metrics
        portfolio_metrics = self._calculate_portfolio_metrics(
            current_positions=context.get('current_positions', []),
            portfolio_value=portfolio_value
        )

        # Build user prompt with risk metrics
        user_prompt = self._build_risk_prompt(
            symbol=symbol,
            entry_price=entry_price,
            portfolio_value=portfolio_value,
            cash_available=cash_available,
            kelly_size=kelly_size,
            portfolio_metrics=portfolio_metrics,
            context=context
        )

        # Analyze with Claude LLM
        llm_result = self._call_llm(
            system_message=self.SYSTEM_MESSAGE,
            user_prompt=user_prompt,
            max_tokens=1024,
            temperature=0.3
        )

        # Parse LLM response
        analysis = self._parse_llm_response(llm_result['content'])

        # Calculate share count
        position_size_pct = analysis['position_size_pct']
        position_value = portfolio_value * (position_size_pct / 100.0)
        shares = int(position_value / entry_price)

        # Apply hard limits
        max_shares = int((portfolio_value * self.max_position_size) / entry_price)
        if shares > max_shares:
            shares = max_shares
            position_size_pct = (shares * entry_price / portfolio_value) * 100

        return {
            'symbol': symbol,
            'decision': analysis['decision'],
            'confidence': analysis['confidence'],
            'position_size_pct': position_size_pct,
            'position_size_shares': shares,
            'stop_loss_pct': analysis['stop_loss_pct'],
            'take_profit_pct': analysis['take_profit_pct'],
            'risk_reward_ratio': analysis['risk_reward_ratio'],
            'risk_factors': analysis['risk_factors'],
            'reasoning': analysis['reasoning'],
            'kelly_size': kelly_size,
            'tokens_used': llm_result['tokens_used'],
            'cost_usd': llm_result['cost_usd'],
            'latency_ms': llm_result['latency_ms'],
            'interaction_id': llm_result['interaction_id']
        }

    def _calculate_kelly_size(
        self,
        win_rate: float,
        avg_win: float,
        avg_loss: float
    ) -> float:
        """Calculate Kelly Criterion position size.

        Kelly % = (Win Rate * Avg Win - Loss Rate * Avg Loss) / Avg Win

        Args:
            win_rate: Historical win rate (0-1)
            avg_win: Average win as decimal (0.05 = 5%)
            avg_loss: Average loss as decimal (0.03 = 3%)

        Returns:
            Recommended position size as fraction (0.25 = 25% of portfolio)
        """
        if win_rate <= 0 or win_rate >= 1:
            return 0.05  # Default 5% if no history

        loss_rate = 1 - win_rate

        # Avoid division by zero
        if avg_win <= 0:
            return 0.05

        # Kelly formula
        kelly = (win_rate * avg_win - loss_rate * avg_loss) / avg_win

        # Apply Kelly fraction (use quarter Kelly for safety)
        kelly = kelly * self.kelly_fraction

        # Clamp to reasonable range
        kelly = max(0.01, min(kelly, self.max_position_size))

        return kelly

    def _calculate_portfolio_metrics(
        self,
        current_positions: List[Dict[str, Any]],
        portfolio_value: float
    ) -> Dict[str, Any]:
        """Calculate portfolio exposure metrics.

        Args:
            current_positions: List of current positions
            portfolio_value: Total portfolio value

        Returns:
            Dictionary with portfolio metrics
        """
        if not current_positions:
            return {
                'total_positions': 0,
                'total_exposure': 0.0,
                'largest_position_pct': 0.0,
                'cash_pct': 100.0
            }

        total_position_value = sum(
            pos.get('market_value', 0) for pos in current_positions
        )

        largest_position = max(
            current_positions,
            key=lambda p: p.get('market_value', 0)
        )

        largest_position_value = largest_position.get('market_value', 0)

        return {
            'total_positions': len(current_positions),
            'total_exposure': (total_position_value / portfolio_value) * 100,
            'largest_position_pct': (largest_position_value / portfolio_value) * 100,
            'largest_position_symbol': largest_position.get('symbol', 'N/A'),
            'cash_pct': ((portfolio_value - total_position_value) / portfolio_value) * 100
        }

    def _build_risk_prompt(
        self,
        symbol: str,
        entry_price: float,
        portfolio_value: float,
        cash_available: float,
        kelly_size: float,
        portfolio_metrics: Dict[str, Any],
        context: Dict[str, Any]
    ) -> str:
        """Build user prompt for risk assessment.

        Args:
            symbol: Stock symbol
            entry_price: Proposed entry price
            portfolio_value: Total portfolio value
            cash_available: Cash available
            kelly_size: Kelly Criterion size
            portfolio_metrics: Portfolio metrics
            context: Full context

        Returns:
            Formatted prompt string
        """
        prompt_parts = [
            f"Assess risk for trading {symbol} @ ${entry_price:.2f}:\n",
            f"\nPORTFOLIO:",
            f"- Total Value: ${portfolio_value:,.2f}",
            f"- Cash Available: ${cash_available:,.2f}",
            f"- Current Positions: {portfolio_metrics['total_positions']}",
            f"- Total Exposure: {portfolio_metrics['total_exposure']:.1f}%",
            f"- Largest Position: {portfolio_metrics.get('largest_position_symbol', 'N/A')} "
            f"({portfolio_metrics['largest_position_pct']:.1f}%)",
            f"- Cash: {portfolio_metrics['cash_pct']:.1f}%",
            f"\nRISK METRICS:",
            f"- Kelly Criterion Size: {kelly_size:.1%}",
            f"- Max Position Size: {self.max_position_size:.1%}",
            f"- Max Portfolio Risk: {self.max_portfolio_risk:.1%}"
        ]

        # Add historical performance if available
        win_rate = context.get('win_rate')
        if win_rate is not None:
            prompt_parts.append(f"\nHISTORICAL PERFORMANCE:")
            prompt_parts.append(f"- Win Rate: {win_rate:.1%}")
            prompt_parts.append(f"- Avg Win: {context.get('avg_win', 0):.1%}")
            prompt_parts.append(f"- Avg Loss: {context.get('avg_loss', 0):.1%}")

        # Add stock-specific metrics if available
        volatility = context.get('volatility')
        beta = context.get('beta')
        if volatility or beta:
            prompt_parts.append(f"\nSTOCK METRICS:")
            if volatility:
                prompt_parts.append(f"- Volatility/ATR: {volatility:.2f}")
            if beta:
                prompt_parts.append(f"- Beta: {beta:.2f}")

        # Add market regime if available
        market_regime = context.get('market_regime')
        if market_regime:
            prompt_parts.append(f"\nMARKET REGIME: {market_regime}")

        # Add fundamental score if available
        fundamental_score = context.get('fundamental_score')
        if fundamental_score:
            prompt_parts.append(f"Fundamental Confidence: {fundamental_score:.0f}/100")

        prompt_parts.append(f"\nProvide your risk assessment in this exact JSON format:")
        prompt_parts.append("""{
  "decision": "APPROVE|REDUCE|REJECT",
  "confidence": 0-100,
  "position_size_pct": 0.0-20.0,
  "stop_loss_pct": 2.0-10.0,
  "take_profit_pct": 5.0-30.0,
  "risk_reward_ratio": 1.5-5.0,
  "risk_factors": ["factor 1", "factor 2"],
  "reasoning": "1-2 sentence explanation"
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

            # Validate required fields
            required_fields = [
                'decision', 'confidence', 'position_size_pct',
                'stop_loss_pct', 'take_profit_pct', 'risk_reward_ratio',
                'risk_factors', 'reasoning'
            ]
            for field in required_fields:
                if field not in analysis:
                    raise ValueError(f"Missing required field: {field}")

            # Normalize decision
            decision = analysis['decision'].upper()
            if decision not in ['APPROVE', 'REDUCE', 'REJECT']:
                decision = 'REDUCE'  # Safe default
            analysis['decision'] = decision

            # Ensure numeric values are in valid range
            analysis['confidence'] = max(0.0, min(100.0, float(analysis['confidence'])))
            analysis['position_size_pct'] = max(0.0, min(20.0, float(analysis['position_size_pct'])))
            analysis['stop_loss_pct'] = max(0.5, min(20.0, float(analysis['stop_loss_pct'])))
            analysis['take_profit_pct'] = max(1.0, min(100.0, float(analysis['take_profit_pct'])))
            analysis['risk_reward_ratio'] = max(0.5, min(10.0, float(analysis['risk_reward_ratio'])))

            return analysis

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.error(f"Failed to parse LLM response: {e}\nContent: {content}")
            # Return conservative default
            return {
                'decision': 'REJECT',
                'confidence': 0.0,
                'position_size_pct': 0.0,
                'stop_loss_pct': 5.0,
                'take_profit_pct': 10.0,
                'risk_reward_ratio': 2.0,
                'risk_factors': ['Failed to parse risk assessment'],
                'reasoning': 'Error parsing risk analysis'
            }
