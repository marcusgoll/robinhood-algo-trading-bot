"""Research Agent for fundamental analysis using Financial Modeling Prep API.

Fetches company fundamentals, analyzes them with Claude LLM, and provides
trading recommendations with confidence scores.
"""

import logging
import json
from typing import Dict, Any, Optional

from .base_agent import BaseAgent
from ...market_data.fmp_client import FMPClient, FMPRateLimitExceeded

logger = logging.getLogger(__name__)


class ResearchAgent(BaseAgent):
    """Agent that performs fundamental analysis on stocks.

    Uses FMP API to fetch:
    - Company profile (sector, industry, market cap, P/E, beta, etc.)
    - Key metrics (ROE, ROA, debt/equity, etc.)
    - Financial ratios (profitability, liquidity)
    - Analyst recommendations
    - Insider trades
    - Earnings surprises

    Then analyzes with Claude LLM to generate structured recommendations.
    """

    SYSTEM_MESSAGE = """You are a fundamental analysis expert for stock trading.

Your job is to analyze company fundamentals and provide a trading recommendation.

Consider:
- Valuation metrics (P/E, P/B, EV/EBITDA)
- Profitability (ROE, ROA, profit margins)
- Financial health (debt/equity, current ratio)
- Growth trends (revenue growth, EPS growth)
- Market sentiment (analyst ratings, insider activity)
- Earnings surprises (beat or miss estimates)

Provide:
1. Overall recommendation (BUY, HOLD, SELL, or SKIP)
2. Confidence score (0-100)
3. Key strengths (2-3 bullet points)
4. Key concerns (2-3 bullet points)
5. Brief reasoning (1-2 sentences)

Be conservative. Only recommend BUY if fundamentals are strong across multiple metrics.
Recommend SKIP if data is insufficient or contradictory."""

    def __init__(
        self,
        model: str = "claude-haiku-4-5",
        memory: Optional[Any] = None,
        api_key: Optional[str] = None,
        fmp_client: Optional[FMPClient] = None
    ):
        """Initialize research agent.

        Args:
            model: Claude model to use (default: claude-haiku-4-5, latest as of Oct 2025)
            model: Claude model to use
            memory: AgentMemory instance
            api_key: Anthropic API key
            fmp_client: FMPClient instance (creates new if None)
        """
        super().__init__(
            agent_name="research",
            model=model,
            memory=memory,
            api_key=api_key
        )
        self.fmp_client = fmp_client or FMPClient()

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute fundamental research on a symbol.

        Args:
            context: {
                'symbol': str,           # Stock symbol (required)
                'current_price': float,  # Current stock price (optional)
                'technical_data': dict   # Technical indicators (optional)
            }

        Returns:
            {
                'symbol': str,
                'decision': str,              # BUY/HOLD/SELL/SKIP
                'confidence': float,          # 0-100
                'strengths': List[str],       # Key strengths
                'concerns': List[str],        # Key concerns
                'reasoning': str,             # Brief explanation
                'fundamental_data': dict,     # Raw FMP data
                'tokens_used': int,
                'cost_usd': float,
                'latency_ms': int,
                'interaction_id': UUID
            }
        """
        symbol = context.get('symbol')
        if not symbol:
            raise ValueError("Symbol required in context")

        logger.info(f"ResearchAgent analyzing {symbol}")

        try:
            # Fetch fundamental data from FMP
            fundamental_data = self._fetch_fundamental_data(symbol)

            if not fundamental_data:
                logger.warning(f"No fundamental data available for {symbol}")
                return {
                    'symbol': symbol,
                    'decision': 'SKIP',
                    'confidence': 0.0,
                    'strengths': [],
                    'concerns': ['Insufficient fundamental data'],
                    'reasoning': 'Unable to fetch fundamental data from FMP API',
                    'fundamental_data': {},
                    'tokens_used': 0,
                    'cost_usd': 0.0,
                    'latency_ms': 0
                }

            # Build user prompt with fundamental data
            user_prompt = self._build_analysis_prompt(
                symbol=symbol,
                fundamental_data=fundamental_data,
                current_price=context.get('current_price'),
                technical_data=context.get('technical_data')
            )

            # Analyze with Claude LLM
            llm_result = self._call_llm(
                system_message=self.SYSTEM_MESSAGE,
                user_prompt=user_prompt,
                max_tokens=1024,
                temperature=0.3  # Lower temperature for more consistent analysis
            )

            # Parse LLM response
            analysis = self._parse_llm_response(llm_result['content'])

            return {
                'symbol': symbol,
                'decision': analysis['decision'],
                'confidence': analysis['confidence'],
                'strengths': analysis['strengths'],
                'concerns': analysis['concerns'],
                'reasoning': analysis['reasoning'],
                'fundamental_data': fundamental_data,
                'tokens_used': llm_result['tokens_used'],
                'cost_usd': llm_result['cost_usd'],
                'latency_ms': llm_result['latency_ms'],
                'interaction_id': llm_result['interaction_id']
            }

        except FMPRateLimitExceeded as e:
            logger.error(f"FMP rate limit exceeded: {e}")
            return {
                'symbol': symbol,
                'decision': 'SKIP',
                'confidence': 0.0,
                'strengths': [],
                'concerns': ['FMP API rate limit exceeded'],
                'reasoning': str(e),
                'fundamental_data': {},
                'tokens_used': 0,
                'cost_usd': 0.0,
                'latency_ms': 0
            }

        except Exception as e:
            logger.error(f"ResearchAgent error for {symbol}: {e}")
            raise

    def _fetch_fundamental_data(self, symbol: str) -> Dict[str, Any]:
        """Fetch comprehensive fundamental data from FMP.

        Args:
            symbol: Stock symbol

        Returns:
            Dictionary with profile, metrics, ratios, ratings, insider trades
        """
        data = {}

        try:
            # Company profile (sector, industry, market cap, P/E, beta, etc.)
            profile = self.fmp_client.get_company_profile(symbol)
            if profile:
                data['profile'] = profile

            # Key metrics (ROE, ROA, debt/equity, etc.)
            metrics = self.fmp_client.get_key_metrics(symbol, limit=1)
            if metrics:
                data['key_metrics'] = metrics[0]

            # Financial ratios
            ratios = self.fmp_client.get_financial_ratios(symbol, limit=1)
            if ratios:
                data['financial_ratios'] = ratios[0]

            # Analyst recommendations
            analyst_recs = self.fmp_client.get_analyst_recommendations(symbol)
            if analyst_recs:
                data['analyst_recommendations'] = analyst_recs[0]

            # Recent insider trades
            insider_trades = self.fmp_client.get_insider_trades(symbol, limit=10)
            if insider_trades:
                # Summarize insider activity
                purchases = sum(1 for t in insider_trades if t.get('transactionType') == 'P-Purchase')
                sales = sum(1 for t in insider_trades if t.get('transactionType') == 'S-Sale')
                data['insider_activity'] = {
                    'recent_purchases': purchases,
                    'recent_sales': sales,
                    'total_transactions': len(insider_trades)
                }

            # Earnings surprises
            earnings = self.fmp_client.get_earnings_surprises(symbol, limit=4)
            if earnings:
                # Calculate beat/miss rate
                beats = sum(1 for e in earnings
                           if e.get('actualEarningResult', 0) > e.get('estimatedEarning', 0))
                data['earnings_surprises'] = {
                    'last_4_quarters': earnings,
                    'beat_rate': beats / len(earnings) if earnings else 0
                }

            logger.info(f"Fetched fundamental data for {symbol}: {len(data)} categories")
            return data

        except FMPRateLimitExceeded:
            raise
        except Exception as e:
            logger.error(f"Error fetching fundamental data for {symbol}: {e}")
            return {}

    def _build_analysis_prompt(
        self,
        symbol: str,
        fundamental_data: Dict[str, Any],
        current_price: Optional[float] = None,
        technical_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build user prompt for LLM analysis.

        Args:
            symbol: Stock symbol
            fundamental_data: FMP data
            current_price: Current stock price
            technical_data: Technical indicators

        Returns:
            Formatted prompt string
        """
        prompt_parts = [f"Analyze {symbol} for trading:\n"]

        # Add company profile
        if 'profile' in fundamental_data:
            profile = fundamental_data['profile']
            prompt_parts.append(f"\nCOMPANY PROFILE:")
            prompt_parts.append(f"- Name: {profile.get('companyName', 'N/A')}")
            prompt_parts.append(f"- Sector: {profile.get('sector', 'N/A')}")
            prompt_parts.append(f"- Industry: {profile.get('industry', 'N/A')}")
            prompt_parts.append(f"- Market Cap: ${profile.get('mktCap', 0):,.0f}")
            prompt_parts.append(f"- P/E Ratio: {profile.get('pe', 'N/A')}")
            prompt_parts.append(f"- Beta: {profile.get('beta', 'N/A')}")
            prompt_parts.append(f"- Dividend Yield: {profile.get('dividendYield', 0):.2%}")

        # Add key metrics
        if 'key_metrics' in fundamental_data:
            metrics = fundamental_data['key_metrics']
            prompt_parts.append(f"\nKEY METRICS:")
            prompt_parts.append(f"- ROE: {metrics.get('roe', 'N/A')}")
            prompt_parts.append(f"- ROA: {metrics.get('roa', 'N/A')}")
            prompt_parts.append(f"- Debt/Equity: {metrics.get('debtToEquity', 'N/A')}")
            prompt_parts.append(f"- P/B Ratio: {metrics.get('priceToBookRatio', 'N/A')}")
            prompt_parts.append(f"- EV/EBITDA: {metrics.get('evToEBITDA', 'N/A')}")

        # Add financial ratios
        if 'financial_ratios' in fundamental_data:
            ratios = fundamental_data['financial_ratios']
            prompt_parts.append(f"\nFINANCIAL RATIOS:")
            prompt_parts.append(f"- Net Profit Margin: {ratios.get('netProfitMargin', 'N/A')}")
            prompt_parts.append(f"- Operating Margin: {ratios.get('operatingProfitMargin', 'N/A')}")
            prompt_parts.append(f"- Current Ratio: {ratios.get('currentRatio', 'N/A')}")
            prompt_parts.append(f"- Quick Ratio: {ratios.get('quickRatio', 'N/A')}")

        # Add analyst recommendations
        if 'analyst_recommendations' in fundamental_data:
            recs = fundamental_data['analyst_recommendations']
            prompt_parts.append(f"\nANALYST RECOMMENDATIONS:")
            prompt_parts.append(f"- Strong Buy: {recs.get('analystRatingsStrongBuy', 0)}")
            prompt_parts.append(f"- Buy: {recs.get('analystRatingsBuy', 0)}")
            prompt_parts.append(f"- Hold: {recs.get('analystRatingsHold', 0)}")
            prompt_parts.append(f"- Sell: {recs.get('analystRatingsSell', 0)}")

        # Add insider activity
        if 'insider_activity' in fundamental_data:
            insider = fundamental_data['insider_activity']
            prompt_parts.append(f"\nINSIDER ACTIVITY (Recent 10 transactions):")
            prompt_parts.append(f"- Purchases: {insider['recent_purchases']}")
            prompt_parts.append(f"- Sales: {insider['recent_sales']}")

        # Add earnings surprises
        if 'earnings_surprises' in fundamental_data:
            earnings = fundamental_data['earnings_surprises']
            prompt_parts.append(f"\nEARNINGS SURPRISES:")
            prompt_parts.append(f"- Beat Rate (last 4Q): {earnings['beat_rate']:.0%}")

        # Add current price if available
        if current_price:
            prompt_parts.append(f"\nCURRENT PRICE: ${current_price:.2f}")

        # Add technical data if available
        if technical_data:
            prompt_parts.append(f"\nTECHNICAL INDICATORS:")
            prompt_parts.append(f"- RSI: {technical_data.get('rsi', 'N/A')}")
            prompt_parts.append(f"- Volume Ratio: {technical_data.get('volume_ratio', 'N/A')}")

        prompt_parts.append(f"\nProvide your analysis in this exact JSON format:")
        prompt_parts.append("""{
  "decision": "BUY|HOLD|SELL|SKIP",
  "confidence": 0-100,
  "strengths": ["strength 1", "strength 2", "strength 3"],
  "concerns": ["concern 1", "concern 2", "concern 3"],
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
            # Look for JSON block between ```json and ``` or just raw JSON
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
            required_fields = ['decision', 'confidence', 'strengths', 'concerns', 'reasoning']
            for field in required_fields:
                if field not in analysis:
                    raise ValueError(f"Missing required field: {field}")

            # Normalize decision
            decision = analysis['decision'].upper()
            if decision not in ['BUY', 'HOLD', 'SELL', 'SKIP']:
                decision = 'SKIP'
            analysis['decision'] = decision

            # Ensure confidence is float 0-100
            analysis['confidence'] = max(0.0, min(100.0, float(analysis['confidence'])))

            return analysis

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.error(f"Failed to parse LLM response: {e}\nContent: {content}")
            # Return safe default
            return {
                'decision': 'SKIP',
                'confidence': 0.0,
                'strengths': [],
                'concerns': ['Failed to parse LLM response'],
                'reasoning': 'Error parsing analysis'
            }
