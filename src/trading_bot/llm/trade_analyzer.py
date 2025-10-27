"""
Trade Signal Analyzer using LLM

Uses OpenAI to analyze trade signals and provide:
- Confidence score (0-100)
- Risk assessment
- Reasoning for decision
- Suggested position size adjustment

Constitution v1.0.0 - §Risk_Management: Validate all trades before execution
"""

import json
import logging
from dataclasses import dataclass
from typing import Optional

from .openai_client import OpenAIClient, LLMConfig

logger = logging.getLogger(__name__)


@dataclass
class TradeAnalysisResult:
    """Result of LLM trade analysis."""

    confidence: int  # 0-100
    risk_level: str  # "low", "medium", "high"
    reasoning: str
    position_size_multiplier: float  # 0.5-1.5 (adjust position size)
    should_trade: bool
    tokens_used: int
    cost: float
    cached: bool


class TradeAnalyzer:
    """
    Analyzes trade signals using LLM.

    Provides intelligent validation of trade opportunities before execution.
    """

    def __init__(self, config: Optional[LLMConfig] = None, enabled: bool = True):
        """
        Initialize trade analyzer.

        Args:
            config: LLM configuration (loads from env if None)
            enabled: Enable LLM analysis (graceful degradation if False)
        """
        self.enabled = enabled

        if self.enabled:
            try:
                self.client = OpenAIClient(config)
                logger.info("Trade analyzer initialized (LLM enabled)")
            except Exception as e:
                logger.warning(f"LLM initialization failed, disabling: {e}")
                self.enabled = False
        else:
            logger.info("Trade analyzer initialized (LLM disabled)")

    def analyze_trade_signal(
        self,
        symbol: str,
        price: float,
        pattern: str,
        indicators: dict,
        context: Optional[dict] = None,
    ) -> TradeAnalysisResult:
        """
        Analyze a trade signal using LLM.

        Args:
            symbol: Stock symbol (e.g., "AAPL")
            price: Current price
            pattern: Pattern detected (e.g., "bull_flag", "breakout")
            indicators: Technical indicators dict (e.g., {"rsi": 55, "volume_ratio": 2.5})
            context: Additional context (market conditions, news, etc.)

        Returns:
            TradeAnalysisResult with confidence score and recommendations

        Example:
            result = analyzer.analyze_trade_signal(
                symbol="AAPL",
                price=150.50,
                pattern="bull_flag",
                indicators={"rsi": 55, "volume_ratio": 2.5, "atr": 2.10},
                context={"market_trend": "bullish", "sector": "technology"}
            )
        """
        # If LLM disabled, return default approval
        if not self.enabled:
            return TradeAnalysisResult(
                confidence=75,
                risk_level="medium",
                reasoning="LLM disabled - using default approval",
                position_size_multiplier=1.0,
                should_trade=True,
                tokens_used=0,
                cost=0.0,
                cached=False,
            )

        try:
            # Build analysis prompt
            prompt = self._build_prompt(symbol, price, pattern, indicators, context)

            # Get LLM response
            response = self.client.complete(
                prompt=prompt,
                max_tokens=300,
                temperature=0.3,  # Lower temperature for consistent analysis
                use_cache=True,
            )

            # Parse response
            result = self._parse_response(response)
            return result

        except Exception as e:
            logger.error(f"Trade analysis failed: {e}", exc_info=True)

            # Graceful degradation - allow trade with medium confidence
            return TradeAnalysisResult(
                confidence=70,
                risk_level="medium",
                reasoning=f"LLM analysis failed ({str(e)}), proceeding with caution",
                position_size_multiplier=0.8,  # Reduce position size due to uncertainty
                should_trade=True,
                tokens_used=0,
                cost=0.0,
                cached=False,
            )

    def _build_prompt(
        self,
        symbol: str,
        price: float,
        pattern: str,
        indicators: dict,
        context: Optional[dict],
    ) -> str:
        """Build analysis prompt for LLM."""
        prompt = f"""Analyze this trading signal and provide a structured assessment.

**Trade Signal:**
- Symbol: {symbol}
- Price: ${price:.2f}
- Pattern: {pattern}
- Indicators: {json.dumps(indicators, indent=2)}
"""

        if context:
            prompt += f"- Context: {json.dumps(context, indent=2)}\n"

        prompt += """
**Instructions:**
Provide a JSON response with the following structure:
{
  "confidence": <integer 0-100>,
  "risk_level": "<low|medium|high>",
  "reasoning": "<2-3 sentence explanation>",
  "position_size_multiplier": <float 0.5-1.5>
}

**Analysis Criteria:**
- **Confidence**: How strong is this signal? (0=avoid, 100=excellent setup)
- **Risk Level**: Overall risk (low/medium/high)
- **Reasoning**: Brief explanation of your assessment
- **Position Size Multiplier**: Adjust position size based on conviction (0.5=half size, 1.0=normal, 1.5=larger)

**Rules:**
1. Confidence < 60 = Do not trade
2. Confidence 60-75 = Trade with reduced size (0.7-0.9x)
3. Confidence 75-85 = Normal trade (1.0x)
4. Confidence > 85 = Strong conviction (1.1-1.3x)

Respond with ONLY the JSON, no additional text.
"""
        return prompt

    def _parse_response(self, response: dict) -> TradeAnalysisResult:
        """Parse LLM response into TradeAnalysisResult."""
        content = response["content"].strip()

        # Extract JSON from response
        if "```json" in content:
            # Handle markdown code blocks
            start = content.find("```json") + 7
            end = content.find("```", start)
            content = content[start:end].strip()
        elif "```" in content:
            start = content.find("```") + 3
            end = content.find("```", start)
            content = content[start:end].strip()

        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON response: {e}\nContent: {content}")
            # Fall back to default
            data = {
                "confidence": 70,
                "risk_level": "medium",
                "reasoning": "Failed to parse LLM response",
                "position_size_multiplier": 1.0,
            }

        # Validate and extract fields
        confidence = max(0, min(100, int(data.get("confidence", 70))))
        risk_level = data.get("risk_level", "medium").lower()
        if risk_level not in ["low", "medium", "high"]:
            risk_level = "medium"

        reasoning = data.get("reasoning", "No reasoning provided")
        position_multiplier = float(data.get("position_size_multiplier", 1.0))
        position_multiplier = max(0.5, min(1.5, position_multiplier))

        # Determine if should trade based on confidence
        should_trade = confidence >= 60

        return TradeAnalysisResult(
            confidence=confidence,
            risk_level=risk_level,
            reasoning=reasoning,
            position_size_multiplier=position_multiplier,
            should_trade=should_trade,
            tokens_used=response["tokens_used"],
            cost=response["cost"],
            cached=response["cached"],
        )

    def get_stats(self) -> dict:
        """Get analyzer statistics."""
        if not self.enabled:
            return {"enabled": False}

        return {
            "enabled": True,
            **self.client.get_stats(),
        }
