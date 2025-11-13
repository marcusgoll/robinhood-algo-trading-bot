"""Volatility Analyst Agent for volatility and risk assessment.

Analyzes volatility indicators like ATR, Bollinger Bands, volatility patterns
to assess risk and identify high-probability entry points for crypto trading.
"""

import logging
import json
from typing import Dict, Any, Optional

from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


class VolatilityAnalystAgent(BaseAgent):
    """Agent that analyzes volatility and risk metrics.

    Analyzes:
    - ATR (Average True Range) - volatility magnitude
    - Bollinger Bands - price extremes and squeezes
    - Volatility trends - expanding/contracting
    - Price compression patterns (low volatility → breakout)
    - Risk/reward assessment based on volatility

    Provides trading recommendations based on volatility and risk.
    """

    SYSTEM_MESSAGE = """You are a volatility analysis expert for crypto trading.

Your job is to analyze volatility patterns and assess risk/reward for trading opportunities.

Consider:
- ATR magnitude (high ATR = high risk/reward, low ATR = range-bound)
- ATR trend (rising ATR = increasing volatility, falling ATR = consolidation)
- Bollinger Band position (price at lower band = potential bounce)
- Bollinger Band width (narrow bands = low volatility → possible breakout)
- Volatility squeeze patterns (low volatility followed by expansion)
- Risk/reward ratio (enter when volatility is low, not high)
- Market regime context (high volatility = dangerous, low volatility = opportunity)

Provide:
1. Overall recommendation (BUY, HOLD, SELL, or SKIP)
2. Confidence score (0-100)
3. Volatility state (VERY_HIGH, HIGH, NORMAL, LOW, VERY_LOW)
4. Risk assessment (HIGH_RISK, MODERATE_RISK, LOW_RISK)
5. Key signals (2-4 volatility signals)
6. Key concerns (1-2 risk concerns)
7. Brief reasoning (1-2 sentences)

Be conservative:
- SKIP during very high volatility (ATR spike) - too risky
- BUY during low volatility near support (favorable risk/reward)
- Look for volatility compression → breakout setups
- Avoid buying at Bollinger Band extremes (mean reversion likely)"""

    def __init__(
        self,
        model: str = "claude-haiku-4-5",
        memory: Optional[Any] = None,
        api_key: Optional[str] = None,
        max_atr_pct: float = 10.0  # Max ATR as % of price for BUY
    ):
        """Initialize volatility analyst agent.

        Args:
            model: Claude model to use (default: claude-haiku-4-5)
            memory: AgentMemory instance
            api_key: Anthropic API key
            max_atr_pct: Maximum ATR % for BUY signal (default: 10%)
        """
        super().__init__(
            agent_name="volatility_analyst",
            model=model,
            memory=memory,
            api_key=api_key
        )
        self.max_atr_pct = max_atr_pct

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute volatility analysis on a symbol.

        Args:
            context: {
                'symbol': str,              # Crypto symbol (required)
                'current_price': float,     # Current price (required)
                'technical_data': dict,     # Technical indicators (required)
                'market_regime': str        # Market regime (optional)
            }

        Returns:
            {
                'symbol': str,
                'decision': str,               # BUY/HOLD/SELL/SKIP
                'confidence': float,           # 0-100
                'volatility_state': str,       # VERY_HIGH/HIGH/NORMAL/LOW/VERY_LOW
                'risk_assessment': str,        # HIGH_RISK/MODERATE_RISK/LOW_RISK
                'signals': List[str],          # Key volatility signals
                'concerns': List[str],         # Key risk concerns
                'reasoning': str,              # Brief explanation
                'tokens_used': int,
                'cost_usd': float,
                'latency_ms': int,
                'interaction_id': UUID
            }
        """
        symbol = context.get('symbol')
        current_price = context.get('current_price')
        technical_data = context.get('technical_data')

        if not all([symbol, current_price, technical_data]):
            raise ValueError("symbol, current_price, technical_data required in context")

        logger.info(f"VolatilityAnalystAgent analyzing {symbol}")

        # Build user prompt with technical data
        user_prompt = self._build_analysis_prompt(
            symbol=symbol,
            current_price=current_price,
            technical_data=technical_data,
            market_regime=context.get('market_regime')
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

        # Apply volatility filter
        atr = technical_data.get('atr')
        if atr and current_price:
            atr_pct = (atr / current_price) * 100
            if atr_pct > self.max_atr_pct:
                logger.info(
                    f"High volatility for {symbol}: ATR={atr_pct:.1f}% "
                    f"(max: {self.max_atr_pct:.0f}%)"
                )
                # Downgrade BUY to SKIP if volatility too high
                if analysis['decision'] == 'BUY':
                    analysis['decision'] = 'SKIP'
                    analysis['concerns'].append(f"Volatility too high (ATR={atr_pct:.1f}%)")

        return {
            'symbol': symbol,
            'decision': analysis['decision'],
            'confidence': analysis['confidence'],
            'volatility_state': analysis['volatility_state'],
            'risk_assessment': analysis['risk_assessment'],
            'signals': analysis['signals'],
            'concerns': analysis['concerns'],
            'reasoning': analysis['reasoning'],
            'tokens_used': llm_result['tokens_used'],
            'cost_usd': llm_result['cost_usd'],
            'latency_ms': llm_result['latency_ms'],
            'interaction_id': llm_result['interaction_id']
        }

    def _build_analysis_prompt(
        self,
        symbol: str,
        current_price: float,
        technical_data: Dict[str, Any],
        market_regime: Optional[str] = None
    ) -> str:
        """Build user prompt for volatility analysis.

        Args:
            symbol: Crypto symbol
            current_price: Current price
            technical_data: Technical indicators
            market_regime: Overall market regime

        Returns:
            Formatted prompt string
        """
        prompt_parts = [f"Analyze volatility and risk for {symbol} @ ${current_price:.2f}:\n"]

        # Add ATR
        atr = technical_data.get('atr')
        if atr:
            atr_pct = (atr / current_price) * 100
            prompt_parts.append(f"\nVOLATILITY INDICATORS:")
            prompt_parts.append(f"- ATR: ${atr:.2f} ({atr_pct:.1f}% of price)")
            if atr_pct > 8:
                prompt_parts.append(f"  → VERY HIGH volatility (risky)")
            elif atr_pct > 5:
                prompt_parts.append(f"  → HIGH volatility")
            elif atr_pct < 2:
                prompt_parts.append(f"  → LOW volatility (potential breakout setup)")
            else:
                prompt_parts.append(f"  → NORMAL volatility")

        # Add Bollinger Bands if available
        bb_upper = technical_data.get('bb_upper')
        bb_lower = technical_data.get('bb_lower')
        if bb_upper and bb_lower:
            prompt_parts.append(f"\nBOLLINGER BANDS:")
            prompt_parts.append(f"- Upper Band: ${bb_upper:.2f}")
            prompt_parts.append(f"- Lower Band: ${bb_lower:.2f}")
            prompt_parts.append(f"- Current Price: ${current_price:.2f}")

            # Price position
            if current_price > bb_upper:
                prompt_parts.append(f"  → Price ABOVE upper band (overbought, mean reversion likely)")
            elif current_price < bb_lower:
                prompt_parts.append(f"  → Price BELOW lower band (oversold, potential bounce)")
            else:
                band_range = bb_upper - bb_lower
                band_width_pct = (band_range / current_price) * 100
                prompt_parts.append(f"  → Band width: {band_width_pct:.1f}%")
                if band_width_pct < 5:
                    prompt_parts.append(f"    → SQUEEZE (low volatility, breakout likely)")

        # Add price range context
        if 'recent_high' in technical_data and 'recent_low' in technical_data:
            recent_high = technical_data['recent_high']
            recent_low = technical_data['recent_low']
            range_pct = ((recent_high - recent_low) / recent_low) * 100

            prompt_parts.append(f"\nPRICE RANGE:")
            prompt_parts.append(f"- Recent High: ${recent_high:.2f}")
            prompt_parts.append(f"- Recent Low: ${recent_low:.2f}")
            prompt_parts.append(f"- Range Width: {range_pct:.1f}%")

            if range_pct < 5:
                prompt_parts.append(f"  → TIGHT RANGE (consolidation)")
            elif range_pct > 20:
                prompt_parts.append(f"  → WIDE RANGE (high volatility)")

        # Add market regime if available
        if market_regime:
            prompt_parts.append(f"\nMARKET REGIME: {market_regime}")
            if market_regime == "HIGH_VOL":
                prompt_parts.append(f"  → Extra caution warranted")

        prompt_parts.append(f"\nProvide your volatility analysis in this exact JSON format:")
        prompt_parts.append("""{
  "decision": "BUY|HOLD|SELL|SKIP",
  "confidence": 0-100,
  "volatility_state": "VERY_HIGH|HIGH|NORMAL|LOW|VERY_LOW",
  "risk_assessment": "HIGH_RISK|MODERATE_RISK|LOW_RISK",
  "signals": ["signal 1", "signal 2", "signal 3"],
  "concerns": ["concern 1", "concern 2"],
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
                'decision', 'confidence', 'volatility_state', 'risk_assessment',
                'signals', 'concerns', 'reasoning'
            ]
            for field in required_fields:
                if field not in analysis:
                    raise ValueError(f"Missing required field: {field}")

            # Normalize decision
            decision = analysis['decision'].upper()
            if decision not in ['BUY', 'HOLD', 'SELL', 'SKIP']:
                decision = 'SKIP'
            analysis['decision'] = decision

            # Normalize volatility state
            vol_state = analysis['volatility_state'].upper()
            valid_states = ['VERY_HIGH', 'HIGH', 'NORMAL', 'LOW', 'VERY_LOW']
            if vol_state not in valid_states:
                vol_state = 'NORMAL'
            analysis['volatility_state'] = vol_state

            # Normalize risk assessment
            risk = analysis['risk_assessment'].upper()
            if risk not in ['HIGH_RISK', 'MODERATE_RISK', 'LOW_RISK']:
                risk = 'MODERATE_RISK'
            analysis['risk_assessment'] = risk

            # Ensure numeric values are in valid range
            analysis['confidence'] = max(0.0, min(100.0, float(analysis['confidence'])))

            # Ensure lists
            if not isinstance(analysis['signals'], list):
                analysis['signals'] = []
            if not isinstance(analysis['concerns'], list):
                analysis['concerns'] = []

            return analysis

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.error(f"Failed to parse LLM response: {e}\nContent: {content}")
            # Return safe default
            return {
                'decision': 'SKIP',
                'confidence': 0.0,
                'volatility_state': 'NORMAL',
                'risk_assessment': 'MODERATE_RISK',
                'signals': [],
                'concerns': ['Failed to parse volatility analysis'],
                'reasoning': 'Error parsing analysis'
            }
