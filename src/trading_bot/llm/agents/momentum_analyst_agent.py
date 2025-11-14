"""Momentum Analyst Agent for momentum and oscillator analysis.

Analyzes momentum indicators like RSI, MACD, volume patterns to identify
overbought/oversold conditions and momentum shifts for crypto trading.
"""

import logging
import json
from typing import Dict, Any, Optional

from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


class MomentumAnalystAgent(BaseAgent):
    """Agent that analyzes momentum indicators and oscillators.

    Analyzes:
    - RSI (Relative Strength Index) - overbought/oversold
    - MACD - trend reversals and momentum shifts
    - Volume patterns - accumulation/distribution
    - Momentum strength and divergences
    - Overbought/oversold conditions

    Provides trading recommendations based on momentum strength and direction.
    """

    SYSTEM_MESSAGE = """You are a momentum analysis expert for crypto trading.

Your job is to analyze momentum indicators and provide trading recommendations based on oscillators and volume.

Consider:
- RSI levels (< 30 = oversold opportunity, > 70 = overbought risk, 40-60 = neutral)
- RSI divergences (price makes new low but RSI doesn't = bullish divergence)
- MACD signals (MACD crossing above signal line = bullish)
- Volume patterns (rising volume on updays = accumulation)
- Momentum strength (strong momentum confirms trend)
- Overbought/oversold extremes (don't buy at RSI > 80, don't sell at RSI < 20)

Provide:
1. Overall recommendation (BUY, HOLD, SELL, or SKIP)
2. Confidence score (0-100)
3. Momentum state (STRONG_BULLISH, BULLISH, NEUTRAL, BEARISH, STRONG_BEARISH)
4. RSI interpretation (OVERSOLD, NEUTRAL, OVERBOUGHT)
5. Key signals (2-4 momentum signals)
6. Key concerns (1-2 concerns if any)
7. Brief reasoning (1-2 sentences)

Be conservative:
- Only BUY when momentum is bullish AND not overbought (RSI < 70)
- SKIP if overbought (RSI > 75) even if trend is up
- Look for oversold bounces (RSI < 35) with bullish divergence
- Avoid buying weakening momentum even in uptrend"""

    def __init__(
        self,
        model: str = "claude-haiku-4-5",
        memory: Optional[Any] = None,
        api_key: Optional[str] = None,
        rsi_overbought: float = 70.0,  # RSI above this = overbought
        rsi_oversold: float = 30.0     # RSI below this = oversold
    ):
        """Initialize momentum analyst agent.

        Args:
            model: Claude model to use (default: claude-haiku-4-5)
            memory: AgentMemory instance
            api_key: Anthropic API key
            rsi_overbought: RSI threshold for overbought (default: 70)
            rsi_oversold: RSI threshold for oversold (default: 30)
        """
        super().__init__(
            agent_name="momentum_analyst",
            model=model,
            memory=memory,
            api_key=api_key
        )
        self.rsi_overbought = rsi_overbought
        self.rsi_oversold = rsi_oversold

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute momentum analysis on a symbol.

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
                'momentum_state': str,         # STRONG_BULLISH/BULLISH/NEUTRAL/BEARISH/STRONG_BEARISH
                'rsi_interpretation': str,     # OVERSOLD/NEUTRAL/OVERBOUGHT
                'signals': List[str],          # Key momentum signals
                'concerns': List[str],         # Key concerns
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

        logger.info(f"MomentumAnalystAgent analyzing {symbol}")

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

        # Apply overbought filter
        rsi = technical_data.get('rsi')
        if rsi and rsi > self.rsi_overbought:
            logger.info(
                f"Overbought condition for {symbol}: RSI={rsi:.1f} "
                f"(threshold: {self.rsi_overbought:.0f})"
            )
            # Downgrade BUY to SKIP if overbought
            if analysis['decision'] == 'BUY':
                analysis['decision'] = 'SKIP'
                analysis['concerns'].append(f"RSI overbought at {rsi:.1f}")

        return {
            'symbol': symbol,
            'decision': analysis['decision'],
            'confidence': analysis['confidence'],
            'momentum_state': analysis['momentum_state'],
            'rsi_interpretation': analysis['rsi_interpretation'],
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
        """Build user prompt for momentum analysis.

        Args:
            symbol: Crypto symbol
            current_price: Current price
            technical_data: Technical indicators
            market_regime: Overall market regime

        Returns:
            Formatted prompt string
        """
        prompt_parts = [f"Analyze momentum for {symbol} @ ${current_price:.2f}:\n"]

        # Add RSI
        rsi = technical_data.get('rsi')
        prompt_parts.append(f"\nMOMENTUM INDICATORS:")
        prompt_parts.append(f"- RSI (14): {rsi if rsi else 'N/A'}")
        if rsi:
            if rsi < 30:
                prompt_parts.append(f"  → OVERSOLD (strong buy signal if trend reverses)")
            elif rsi > 70:
                prompt_parts.append(f"  → OVERBOUGHT (caution - possible pullback)")
            else:
                prompt_parts.append(f"  → NEUTRAL range")

        # Add volume
        volume_ratio = technical_data.get('volume_ratio')
        if volume_ratio:
            prompt_parts.append(f"- Volume Ratio: {volume_ratio:.2f}x average")
            if volume_ratio > 1.5:
                prompt_parts.append(f"  → HIGH volume (strong conviction)")
            elif volume_ratio < 0.7:
                prompt_parts.append(f"  → LOW volume (weak conviction)")

        # Add ATR for volatility context
        atr = technical_data.get('atr')
        if atr:
            prompt_parts.append(f"- ATR (volatility): ${atr:.2f}")

        # Add price momentum
        if 'recent_high' in technical_data and 'recent_low' in technical_data:
            prompt_parts.append(f"\nPRICE MOMENTUM:")
            recent_high = technical_data['recent_high']
            recent_low = technical_data['recent_low']
            prompt_parts.append(f"- Recent High: ${recent_high:.2f}")
            prompt_parts.append(f"- Recent Low: ${recent_low:.2f}")

            # Position in range
            price_pct = ((current_price - recent_low) / (recent_high - recent_low)) * 100
            prompt_parts.append(f"- Price Position: {price_pct:.1f}% of range")
            if price_pct > 80:
                prompt_parts.append(f"  → Near resistance (possible reversal)")
            elif price_pct < 20:
                prompt_parts.append(f"  → Near support (possible bounce)")

        # Add market regime if available
        if market_regime:
            prompt_parts.append(f"\nMARKET REGIME: {market_regime}")

        prompt_parts.append(f"\nProvide your momentum analysis in this exact JSON format:")
        prompt_parts.append("""{
  "decision": "BUY|HOLD|SELL|SKIP",
  "confidence": 0-100,
  "momentum_state": "STRONG_BULLISH|BULLISH|NEUTRAL|BEARISH|STRONG_BEARISH",
  "rsi_interpretation": "OVERSOLD|NEUTRAL|OVERBOUGHT",
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
                'decision', 'confidence', 'momentum_state', 'rsi_interpretation',
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

            # Normalize momentum state
            momentum = analysis['momentum_state'].upper()
            valid_states = ['STRONG_BULLISH', 'BULLISH', 'NEUTRAL', 'BEARISH', 'STRONG_BEARISH']
            if momentum not in valid_states:
                momentum = 'NEUTRAL'
            analysis['momentum_state'] = momentum

            # Normalize RSI interpretation
            rsi_state = analysis['rsi_interpretation'].upper()
            if rsi_state not in ['OVERSOLD', 'NEUTRAL', 'OVERBOUGHT']:
                rsi_state = 'NEUTRAL'
            analysis['rsi_interpretation'] = rsi_state

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
                'momentum_state': 'NEUTRAL',
                'rsi_interpretation': 'NEUTRAL',
                'signals': [],
                'concerns': ['Failed to parse momentum analysis'],
                'reasoning': 'Error parsing analysis'
            }
