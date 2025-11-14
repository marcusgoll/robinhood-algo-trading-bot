"""News Analyst Agent for sentiment analysis from financial news.

Fetches recent news from FMP API, performs sentiment analysis with Claude LLM,
and provides trading impact assessments based on news sentiment.
"""

import logging
import json
from typing import Dict, Any, Optional, List
from datetime import datetime

from .base_agent import BaseAgent
from ...market_data.fmp_client import FMPClient, FMPRateLimitExceeded

logger = logging.getLogger(__name__)


class NewsAnalystAgent(BaseAgent):
    """Agent that performs sentiment analysis on financial news.

    Uses FMP API to fetch recent news and Claude LLM to analyze:
    - Overall sentiment (bullish, neutral, bearish)
    - Sentiment score (-100 to +100)
    - Key themes (earnings, regulatory, product launches, acquisitions)
    - Credibility assessment (verify against multiple sources)
    - Trading impact (BUY_SIGNAL, SELL_SIGNAL, NEUTRAL, NOISE)
    - Urgency level (IMMEDIATE, NEAR_TERM, LONG_TERM)

    Tracks sentiment trends over time to identify shifts in market narrative.
    """

    SYSTEM_MESSAGE = """You are a financial news sentiment analyst.

Your job is to analyze recent news articles about a stock and assess their trading impact.

Consider:
- Headline sentiment (positive, neutral, negative)
- Article content (facts vs speculation)
- Source credibility (reputable outlets vs blogs)
- Information novelty (breaking news vs rehashed content)
- Market relevance (material impact vs noise)
- Temporal urgency (immediate action vs long-term development)
- Sentiment consistency (single article vs broader narrative)

Analyze news and provide:
1. Overall sentiment (BULLISH, NEUTRAL, BEARISH)
2. Sentiment score (-100 to +100, where -100 is extremely bearish, +100 is extremely bullish)
3. Key themes (list 2-4 major topics: "earnings_beat", "regulatory_approval", "product_launch", etc.)
4. Credibility score (0-100, based on source quality and fact density)
5. Trading impact (BUY_SIGNAL, SELL_SIGNAL, NEUTRAL, NOISE)
6. Urgency level (IMMEDIATE, NEAR_TERM, LONG_TERM)
7. Brief summary (2-3 sentences)
8. Confidence score (0-100)

Be skeptical of hype. Distinguish between material news and market noise.
Only recommend BUY_SIGNAL/SELL_SIGNAL for high-credibility, high-impact news."""

    def __init__(
        self,
        model: str = "claude-haiku-4-5",
        memory: Optional[Any] = None,
        api_key: Optional[str] = None,
        fmp_client: Optional[FMPClient] = None,
        min_credibility: float = 60.0  # Minimum credibility score to act on news
    ):
        """Initialize news analyst agent.

        Args:
            model: Claude model to use (default: claude-haiku-4-5, latest as of Oct 2025)

        Args:
            model: Claude model to use
            memory: AgentMemory instance
            api_key: Anthropic API key
            fmp_client: FMPClient instance (creates new if None)
            min_credibility: Minimum credibility threshold (0-100)
        """
        super().__init__(
            agent_name="news_analyst",
            model=model,
            memory=memory,
            api_key=api_key
        )
        self.fmp_client = fmp_client or FMPClient()
        self.min_credibility = min_credibility

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute sentiment analysis on recent news.

        Args:
            context: {
                'symbol': str,              # Stock symbol (required)
                'lookback_hours': int,      # Hours of news to analyze (optional, default 24)
                'max_articles': int,        # Max articles to analyze (optional, default 10)
                'current_price': float      # Current stock price (optional)
            }

        Returns:
            {
                'symbol': str,
                'decision': str,               # BUY/SKIP/HOLD (for consensus voting)
                'sentiment': str,              # BULLISH/NEUTRAL/BEARISH
                'sentiment_score': float,      # -100 to +100
                'key_themes': List[str],       # Major topics
                'credibility': float,          # 0-100
                'trading_impact': str,         # BUY_SIGNAL/SELL_SIGNAL/NEUTRAL/NOISE
                'urgency': str,                # IMMEDIATE/NEAR_TERM/LONG_TERM
                'summary': str,                # Brief summary
                'confidence': float,           # 0-100
                'reasoning': str,              # Reasoning for decision
                'articles_analyzed': int,
                'tokens_used': int,
                'cost_usd': float,
                'latency_ms': int,
                'interaction_id': UUID
            }
        """
        symbol = context.get('symbol')
        if not symbol:
            raise ValueError("Symbol required in context")

        # Check if this is a crypto symbol (contains '/')
        is_crypto = '/' in symbol

        if is_crypto:
            logger.info(f"NewsAnalystAgent skipping {symbol} (crypto - FMP free tier doesn't support crypto news)")
            return {
                'symbol': symbol,
                'decision': 'SKIP',
                'sentiment': 'NEUTRAL',
                'sentiment_score': 0.0,
                'key_themes': [],
                'credibility': 50.0,
                'trading_impact': 'NEUTRAL',
                'urgency': 'LONG_TERM',
                'summary': 'Crypto news analysis not available (FMP free tier limitation)',
                'confidence': 50.0,
                'reasoning': 'Cannot evaluate crypto sentiment - FMP API does not provide crypto news on free tier. Defer to technical analysis.',
                'articles_analyzed': 0,
                'tokens_used': 0,
                'cost_usd': 0.0,
                'latency_ms': 0
            }

        max_articles = context.get('max_articles', 10)

        logger.info(f"NewsAnalystAgent analyzing {symbol} (max {max_articles} articles)")

        try:
            # Fetch recent news from FMP
            news_articles = self.fmp_client.get_company_news(
                symbol=symbol,
                limit=max_articles
            )

            if not news_articles:
                logger.warning(f"No news articles found for {symbol}")
                return {
                    'symbol': symbol,
                    'decision': 'SKIP',
                    'sentiment': 'NEUTRAL',
                    'sentiment_score': 0.0,
                    'key_themes': [],
                    'credibility': 0.0,
                    'trading_impact': 'NOISE',
                    'urgency': 'LONG_TERM',
                    'summary': 'No recent news available',
                    'confidence': 0.0,
                    'reasoning': 'No news articles found to analyze sentiment',
                    'articles_analyzed': 0,
                    'tokens_used': 0,
                    'cost_usd': 0.0,
                    'latency_ms': 0
                }

            # Build user prompt with news articles
            user_prompt = self._build_sentiment_prompt(
                symbol=symbol,
                news_articles=news_articles,
                current_price=context.get('current_price')
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

            # Filter low-credibility news
            if analysis['credibility'] < self.min_credibility:
                logger.info(
                    f"Low credibility news for {symbol}: {analysis['credibility']:.0f}/100 "
                    f"(min: {self.min_credibility:.0f})"
                )
                # Downgrade trading impact to NOISE
                if analysis['trading_impact'] in ['BUY_SIGNAL', 'SELL_SIGNAL']:
                    analysis['trading_impact'] = 'NOISE'

            # Map trading_impact to decision for consensus voting
            decision_map = {
                'BUY_SIGNAL': 'BUY',
                'SELL_SIGNAL': 'SKIP',  # Treat sell signals as skip for now
                'NEUTRAL': 'SKIP',
                'NOISE': 'SKIP'
            }
            decision = decision_map.get(analysis['trading_impact'], 'SKIP')

            return {
                'symbol': symbol,
                'decision': decision,
                'sentiment': analysis['sentiment'],
                'sentiment_score': analysis['sentiment_score'],
                'key_themes': analysis['key_themes'],
                'credibility': analysis['credibility'],
                'trading_impact': analysis['trading_impact'],
                'urgency': analysis['urgency'],
                'summary': analysis['summary'],
                'confidence': analysis['confidence'],
                'reasoning': analysis['summary'],  # Use summary as reasoning
                'articles_analyzed': len(news_articles),
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
                'sentiment': 'NEUTRAL',
                'sentiment_score': 0.0,
                'key_themes': [],
                'credibility': 0.0,
                'trading_impact': 'NOISE',
                'urgency': 'LONG_TERM',
                'summary': 'FMP API rate limit exceeded',
                'confidence': 0.0,
                'reasoning': 'Cannot evaluate news sentiment - FMP API rate limit exceeded',
                'articles_analyzed': 0,
                'tokens_used': 0,
                'cost_usd': 0.0,
                'latency_ms': 0
            }

        except Exception as e:
            logger.error(f"NewsAnalystAgent error for {symbol}: {e}")
            raise

    def _build_sentiment_prompt(
        self,
        symbol: str,
        news_articles: List[Dict[str, Any]],
        current_price: Optional[float] = None
    ) -> str:
        """Build user prompt for sentiment analysis.

        Args:
            symbol: Stock symbol
            news_articles: List of news articles from FMP
            current_price: Current stock price

        Returns:
            Formatted prompt string
        """
        prompt_parts = [
            f"Analyze recent news sentiment for {symbol}:\n",
            f"\nNEWS ARTICLES ({len(news_articles)} total):"
        ]

        for i, article in enumerate(news_articles[:10], 1):  # Limit to 10 for context
            published_date = article.get('publishedDate', 'N/A')
            title = article.get('title', 'N/A')
            text = article.get('text', '')[:200]  # First 200 chars
            url = article.get('url', 'N/A')

            prompt_parts.append(f"\nArticle {i}:")
            prompt_parts.append(f"- Date: {published_date}")
            prompt_parts.append(f"- Title: {title}")
            prompt_parts.append(f"- Excerpt: {text}...")
            prompt_parts.append(f"- Source: {url}")

        if current_price:
            prompt_parts.append(f"\nCURRENT PRICE: ${current_price:.2f}")

        prompt_parts.append("\nProvide your sentiment analysis in this exact JSON format:")
        prompt_parts.append("""{
  "sentiment": "BULLISH|NEUTRAL|BEARISH",
  "sentiment_score": -100 to +100,
  "key_themes": ["theme1", "theme2", "theme3"],
  "credibility": 0-100,
  "trading_impact": "BUY_SIGNAL|SELL_SIGNAL|NEUTRAL|NOISE",
  "urgency": "IMMEDIATE|NEAR_TERM|LONG_TERM",
  "summary": "2-3 sentence summary",
  "confidence": 0-100
}""")

        return "\n".join(prompt_parts)

    def _parse_llm_response(self, content: str) -> Dict[str, Any]:
        """Parse LLM response into structured format.

        Args:
            content: LLM response text

        Returns:
            Parsed sentiment analysis dictionary
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
                'sentiment', 'sentiment_score', 'key_themes', 'credibility',
                'trading_impact', 'urgency', 'summary', 'confidence'
            ]
            for field in required_fields:
                if field not in analysis:
                    raise ValueError(f"Missing required field: {field}")

            # Normalize sentiment
            sentiment = analysis['sentiment'].upper()
            if sentiment not in ['BULLISH', 'NEUTRAL', 'BEARISH']:
                sentiment = 'NEUTRAL'
            analysis['sentiment'] = sentiment

            # Normalize trading impact
            impact = analysis['trading_impact'].upper()
            if impact not in ['BUY_SIGNAL', 'SELL_SIGNAL', 'NEUTRAL', 'NOISE']:
                impact = 'NEUTRAL'
            analysis['trading_impact'] = impact

            # Normalize urgency
            urgency = analysis['urgency'].upper()
            if urgency not in ['IMMEDIATE', 'NEAR_TERM', 'LONG_TERM']:
                urgency = 'LONG_TERM'
            analysis['urgency'] = urgency

            # Ensure numeric values are in valid range
            analysis['sentiment_score'] = max(-100.0, min(100.0, float(analysis['sentiment_score'])))
            analysis['credibility'] = max(0.0, min(100.0, float(analysis['credibility'])))
            analysis['confidence'] = max(0.0, min(100.0, float(analysis['confidence'])))

            # Ensure key_themes is a list
            if not isinstance(analysis['key_themes'], list):
                analysis['key_themes'] = []

            return analysis

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.error(f"Failed to parse LLM response: {e}\nContent: {content}")
            # Return neutral default
            return {
                'sentiment': 'NEUTRAL',
                'sentiment_score': 0.0,
                'key_themes': [],
                'credibility': 0.0,
                'trading_impact': 'NOISE',
                'urgency': 'LONG_TERM',
                'summary': 'Failed to parse sentiment analysis',
                'confidence': 0.0
            }
