"""Regime Detector Agent for market regime classification.

Analyzes price action and volatility to classify current market regime:
BULL, BEAR, SIDEWAYS, HIGH_VOL, LOW_VOL

Uses technical indicators + Claude LLM for robust regime detection.
"""

import logging
import json
from typing import Dict, Any, Optional

from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


class RegimeDetectorAgent(BaseAgent):
    """Agent that classifies market regime for adaptive strategy selection.

    Analyzes:
    - Price vs moving averages (SMA20, SMA50, SMA200)
    - Trend strength (ADX, slope of moving averages)
    - Volatility (ATR, standard deviation, VIX if SPY)
    - Volume patterns (volume ratio vs average)
    - Recent price action (higher highs/lows, breakouts)

    Classifies regime as:
    - BULL: Strong uptrend, price above MAs, low-moderate volatility
    - BEAR: Strong downtrend, price below MAs, increasing volatility
    - SIDEWAYS: Range-bound, choppy, no clear trend
    - HIGH_VOL: High volatility regardless of direction (> 2x normal)
    - LOW_VOL: Low volatility, stable, range-bound

    Regime detection helps adapt strategy parameters:
    - BULL: Increase position sizes, longer holds
    - BEAR: Reduce sizes, tighter stops
    - SIDEWAYS: Mean reversion, range trading
    - HIGH_VOL: Reduce sizes, avoid whipsaws
    - LOW_VOL: Use breakout strategies
    """

    SYSTEM_MESSAGE = """You are a market regime classification expert.

Your job is to classify the current market regime based on price action and technical indicators.

Consider:
- Trend direction (price vs moving averages, higher highs/lows)
- Trend strength (how far above/below MAs, ADX levels)
- Volatility level (ATR, std dev compared to historical norms)
- Volume patterns (increasing on trend days, decreasing on reversals)
- Recent price behavior (smooth trends vs choppy action)
- Breakouts vs false breaks

Classify regime as:
1. BULL - Strong uptrend, price above MAs, controlled volatility
2. BEAR - Strong downtrend, price below MAs, elevated volatility
3. SIDEWAYS - No clear trend, choppy, range-bound
4. HIGH_VOL - Volatility spike regardless of direction
5. LOW_VOL - Low volatility, stable, compressed range

Provide:
1. Regime classification (BULL, BEAR, SIDEWAYS, HIGH_VOL, LOW_VOL)
2. Confidence score (0-100)
3. Key indicators (2-3 supporting factors)
4. Regime strength (STRONG, MODERATE, WEAK)
5. Brief reasoning (1-2 sentences)

Be conservative. Mixed signals → SIDEWAYS or moderate confidence."""

    def __init__(
        self,
        model: str = "claude-haiku-4-5",
        memory: Optional[Any] = None,
        api_key: Optional[str] = None
    ):
        """Initialize regime detector agent.

        Args:
            model: Claude model to use (default: claude-haiku-4-5, latest as of Oct 2025)
            memory: AgentMemory instance
            api_key: Anthropic API key
        """
        super().__init__(
            agent_name="regime_detector",
            model=model,
            memory=memory,
            api_key=api_key
        )

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute regime classification.

        Args:
            context: {
                'symbol': str,                 # Stock symbol (required)
                'current_price': float,        # Current price (required)
                'sma_20': float,               # 20-day SMA (optional)
                'sma_50': float,               # 50-day SMA (optional)
                'sma_200': float,              # 200-day SMA (optional)
                'atr': float,                  # Average True Range (optional)
                'adx': float,                  # Average Directional Index (optional)
                'volume_ratio': float,         # Current volume / avg volume (optional)
                'recent_high': float,          # Recent high (optional)
                'recent_low': float,           # Recent low (optional)
                'volatility_20d': float        # 20-day historical volatility (optional)
            }

        Returns:
            {
                'symbol': str,
                'regime': str,                 # BULL/BEAR/SIDEWAYS/HIGH_VOL/LOW_VOL
                'confidence': float,           # 0-100
                'regime_strength': str,        # STRONG/MODERATE/WEAK
                'key_indicators': List[str],   # Supporting factors
                'reasoning': str,              # Brief explanation
                'tokens_used': int,
                'cost_usd': float,
                'latency_ms': int,
                'interaction_id': UUID
            }
        """
        symbol = context.get('symbol')
        current_price = context.get('current_price')

        if not all([symbol, current_price]):
            raise ValueError("symbol and current_price required")

        logger.info(f"RegimeDetectorAgent classifying {symbol} @ ${current_price}")

        # Build user prompt with technical indicators
        user_prompt = self._build_regime_prompt(
            symbol=symbol,
            current_price=current_price,
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

        return {
            'symbol': symbol,
            'regime': analysis['regime'],
            'confidence': analysis['confidence'],
            'regime_strength': analysis['regime_strength'],
            'key_indicators': analysis['key_indicators'],
            'reasoning': analysis['reasoning'],
            'tokens_used': llm_result['tokens_used'],
            'cost_usd': llm_result['cost_usd'],
            'latency_ms': llm_result['latency_ms'],
            'interaction_id': llm_result['interaction_id']
        }

    def _build_regime_prompt(
        self,
        symbol: str,
        current_price: float,
        context: Dict[str, Any]
    ) -> str:
        """Build user prompt for regime classification.

        Args:
            symbol: Stock symbol
            current_price: Current price
            context: Full context with technical indicators

        Returns:
            Formatted prompt string
        """
        prompt_parts = [
            f"Classify market regime for {symbol} @ ${current_price:.2f}:\n",
            f"\nPRICE ACTION:"
        ]

        # Add moving average analysis
        sma_20 = context.get('sma_20')
        sma_50 = context.get('sma_50')
        sma_200 = context.get('sma_200')

        if sma_20:
            pct_above_20 = ((current_price - sma_20) / sma_20) * 100
            prompt_parts.append(f"- Price vs SMA20: {pct_above_20:+.1f}%")

        if sma_50:
            pct_above_50 = ((current_price - sma_50) / sma_50) * 100
            prompt_parts.append(f"- Price vs SMA50: {pct_above_50:+.1f}%")

        if sma_200:
            pct_above_200 = ((current_price - sma_200) / sma_200) * 100
            prompt_parts.append(f"- Price vs SMA200: {pct_above_200:+.1f}%")

        # Add volatility metrics
        atr = context.get('atr')
        volatility_20d = context.get('volatility_20d')

        if atr or volatility_20d:
            prompt_parts.append(f"\nVOLATILITY:")
            if atr:
                atr_pct = (atr / current_price) * 100
                prompt_parts.append(f"- ATR: ${atr:.2f} ({atr_pct:.1f}% of price)")
            if volatility_20d:
                prompt_parts.append(f"- 20-day Volatility: {volatility_20d:.1f}%")

        # Add trend strength
        adx = context.get('adx')
        if adx:
            prompt_parts.append(f"\nTREND STRENGTH:")
            prompt_parts.append(f"- ADX: {adx:.1f}")
            if adx < 20:
                prompt_parts.append("  (Weak trend)")
            elif adx < 40:
                prompt_parts.append("  (Moderate trend)")
            else:
                prompt_parts.append("  (Strong trend)")

        # Add volume
        volume_ratio = context.get('volume_ratio')
        if volume_ratio:
            prompt_parts.append(f"\nVOLUME:")
            prompt_parts.append(f"- Volume Ratio: {volume_ratio:.1f}x average")

        # Add recent range
        recent_high = context.get('recent_high')
        recent_low = context.get('recent_low')
        if recent_high and recent_low:
            range_pct = ((recent_high - recent_low) / recent_low) * 100
            price_in_range = ((current_price - recent_low) / (recent_high - recent_low)) * 100

            prompt_parts.append(f"\nRECENT RANGE:")
            prompt_parts.append(f"- High: ${recent_high:.2f}")
            prompt_parts.append(f"- Low: ${recent_low:.2f}")
            prompt_parts.append(f"- Range: {range_pct:.1f}%")
            prompt_parts.append(f"- Price Position: {price_in_range:.0f}% of range")

        prompt_parts.append("\nProvide regime classification in this exact JSON format:")
        prompt_parts.append("""{
  "regime": "BULL|BEAR|SIDEWAYS|HIGH_VOL|LOW_VOL",
  "confidence": 0-100,
  "regime_strength": "STRONG|MODERATE|WEAK",
  "key_indicators": ["indicator 1", "indicator 2", "indicator 3"],
  "reasoning": "1-2 sentence explanation"
}""")

        return "\n".join(prompt_parts)

    def _parse_llm_response(self, content: str) -> Dict[str, Any]:
        """Parse LLM response into structured format.

        Args:
            content: LLM response text

        Returns:
            Parsed regime classification dictionary
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
                'regime', 'confidence', 'regime_strength',
                'key_indicators', 'reasoning'
            ]
            for field in required_fields:
                if field not in analysis:
                    raise ValueError(f"Missing required field: {field}")

            # Normalize regime
            regime = analysis['regime'].upper()
            if regime not in ['BULL', 'BEAR', 'SIDEWAYS', 'HIGH_VOL', 'LOW_VOL']:
                regime = 'SIDEWAYS'  # Safe default
            analysis['regime'] = regime

            # Normalize regime strength
            strength = analysis['regime_strength'].upper()
            if strength not in ['STRONG', 'MODERATE', 'WEAK']:
                strength = 'MODERATE'
            analysis['regime_strength'] = strength

            # Ensure confidence is float 0-100
            analysis['confidence'] = max(0.0, min(100.0, float(analysis['confidence'])))

            # Ensure key_indicators is a list
            if not isinstance(analysis['key_indicators'], list):
                analysis['key_indicators'] = []

            return analysis

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.error(f"Failed to parse LLM response: {e}\nContent: {content}")
            # Return safe default
            return {
                'regime': 'SIDEWAYS',
                'confidence': 0.0,
                'regime_strength': 'WEAK',
                'key_indicators': ['Failed to parse regime classification'],
                'reasoning': 'Error parsing regime analysis'
            }
