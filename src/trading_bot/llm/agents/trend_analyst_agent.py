"""Trend Analyst Agent for technical trend analysis.

Analyzes price trends using moving averages, trend strength, breakouts,
and price patterns to identify bullish/bearish trends for crypto trading.
"""

import logging
import json
from typing import Dict, Any, Optional

from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


class TrendAnalystAgent(BaseAgent):
    """Agent that analyzes price trends and breakout patterns.

    Analyzes:
    - Moving average alignments (SMA 20/50/200)
    - Trend strength and momentum
    - Support/resistance levels
    - Breakout patterns (higher highs, higher lows)
    - Price position relative to moving averages
    - Golden cross / Death cross patterns

    Provides trading recommendations based on trend direction and strength.
    """

    SYSTEM_MESSAGE = """You are a technical trend analysis expert for crypto trading.

Your job is to analyze price trends and provide trading recommendations based on technical patterns.

Consider:
- Moving average alignment (bullish when price > SMA20 > SMA50 > SMA200)
- Trend strength (ADX, price momentum)
- Breakout patterns (higher highs, higher lows for uptrend)
- Support/resistance levels
- Price position relative to key moving averages
- Golden cross (SMA50 crosses above SMA200) = bullish
- Death cross (SMA50 crosses below SMA200) = bearish
- Volume trends (rising volume confirms trend)

Provide:
1. Overall recommendation (BUY, HOLD, SELL, or SKIP)
2. Confidence score (0-100)
3. Trend direction (STRONG_UPTREND, UPTREND, SIDEWAYS, DOWNTREND, STRONG_DOWNTREND)
4. Trend strength (0-100)
5. Key signals (2-4 bullet points)
6. Key concerns (1-2 concerns if any)
7. Brief reasoning (1-2 sentences)

Be conservative. Only recommend BUY for strong confirmed uptrends with multiple confirmations.
Recommend SKIP if trend is unclear, sideways, or weakening."""

    def __init__(
        self,
        model: str = "claude-haiku-4-5",
        memory: Optional[Any] = None,
        api_key: Optional[str] = None,
        min_trend_strength: float = 60.0  # Minimum trend strength for BUY
    ):
        """Initialize trend analyst agent.

        Args:
            model: Claude model to use (default: claude-haiku-4-5)
            memory: AgentMemory instance
            api_key: Anthropic API key
            min_trend_strength: Minimum trend strength threshold (0-100)
        """
        super().__init__(
            agent_name="trend_analyst",
            model=model,
            memory=memory,
            api_key=api_key
        )
        self.min_trend_strength = min_trend_strength

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute trend analysis on a symbol.

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
                'trend_direction': str,        # STRONG_UPTREND/UPTREND/SIDEWAYS/DOWNTREND/STRONG_DOWNTREND
                'trend_strength': float,       # 0-100
                'signals': List[str],          # Key bullish signals
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

        logger.info(f"TrendAnalystAgent analyzing {symbol}")

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

        # Filter weak trends
        if analysis['trend_strength'] < self.min_trend_strength:
            logger.info(
                f"Weak trend for {symbol}: {analysis['trend_strength']:.0f}/100 "
                f"(min: {self.min_trend_strength:.0f})"
            )
            # Downgrade to SKIP if trend is too weak
            if analysis['decision'] == 'BUY':
                analysis['decision'] = 'SKIP'
                analysis['concerns'].append(f"Trend strength below threshold ({analysis['trend_strength']:.0f}/100)")

        return {
            'symbol': symbol,
            'decision': analysis['decision'],
            'confidence': analysis['confidence'],
            'trend_direction': analysis['trend_direction'],
            'trend_strength': analysis['trend_strength'],
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
        """Build user prompt for trend analysis.

        Args:
            symbol: Crypto symbol
            current_price: Current price
            technical_data: Technical indicators
            market_regime: Overall market regime

        Returns:
            Formatted prompt string
        """
        prompt_parts = [f"Analyze trend for {symbol} @ ${current_price:.2f}:\n"]

        # Add moving averages
        prompt_parts.append(f"\nMOVING AVERAGES:")
        prompt_parts.append(f"- Current Price: ${current_price:.2f}")
        prompt_parts.append(f"- SMA 20: ${technical_data.get('sma_20', 'N/A')}")
        prompt_parts.append(f"- SMA 50: ${technical_data.get('sma_50', 'N/A')}")
        prompt_parts.append(f"- SMA 200: ${technical_data.get('sma_200', 'N/A')}")

        # Add trend indicators
        prompt_parts.append(f"\nTREND INDICATORS:")
        prompt_parts.append(f"- ADX (trend strength): {technical_data.get('adx', 'N/A')}")
        prompt_parts.append(f"- Volume Ratio: {technical_data.get('volume_ratio', 'N/A')}")

        # Add price levels
        if 'recent_high' in technical_data and 'recent_low' in technical_data:
            prompt_parts.append(f"\nPRICE LEVELS:")
            prompt_parts.append(f"- Recent High: ${technical_data['recent_high']:.2f}")
            prompt_parts.append(f"- Recent Low: ${technical_data['recent_low']:.2f}")
            range_pct = ((technical_data['recent_high'] - technical_data['recent_low']) / technical_data['recent_low']) * 100
            price_in_range = ((current_price - technical_data['recent_low']) / (technical_data['recent_high'] - technical_data['recent_low'])) * 100
            prompt_parts.append(f"- Range: {range_pct:.1f}%")
            prompt_parts.append(f"- Position in Range: {price_in_range:.1f}%")

        # Add market regime if available
        if market_regime:
            prompt_parts.append(f"\nMARKET REGIME: {market_regime}")

        prompt_parts.append(f"\nProvide your trend analysis in this exact JSON format:")
        prompt_parts.append("""{
  "decision": "BUY|HOLD|SELL|SKIP",
  "confidence": 0-100,
  "trend_direction": "STRONG_UPTREND|UPTREND|SIDEWAYS|DOWNTREND|STRONG_DOWNTREND",
  "trend_strength": 0-100,
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
                'decision', 'confidence', 'trend_direction', 'trend_strength',
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

            # Normalize trend direction
            trend_dir = analysis['trend_direction'].upper()
            valid_trends = ['STRONG_UPTREND', 'UPTREND', 'SIDEWAYS', 'DOWNTREND', 'STRONG_DOWNTREND']
            if trend_dir not in valid_trends:
                trend_dir = 'SIDEWAYS'
            analysis['trend_direction'] = trend_dir

            # Ensure numeric values are in valid range
            analysis['confidence'] = max(0.0, min(100.0, float(analysis['confidence'])))
            analysis['trend_strength'] = max(0.0, min(100.0, float(analysis['trend_strength'])))

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
                'trend_direction': 'SIDEWAYS',
                'trend_strength': 0.0,
                'signals': [],
                'concerns': ['Failed to parse trend analysis'],
                'reasoning': 'Error parsing analysis'
            }
