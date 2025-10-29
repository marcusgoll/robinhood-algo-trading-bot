"""
Catalyst Detector Service

Scans breaking news for fundamental events (earnings, FDA approvals, mergers, etc.)
and categorizes them into catalyst types for momentum trading signals.

Constitution v1.0.0:
- §Safety_First: Manual review required, no auto-trading
- §Risk_Management: Input validation, rate limiting, graceful degradation
- §Security: API keys from environment only

Feature: momentum-detection
Tasks: T015 [GREEN], T016 [GREEN] - CatalystDetector service with error handling
"""

import logging
from datetime import UTC, datetime, timedelta

import httpx

from ..error_handling.retry import with_retry
from .config import MomentumConfig
from .logging.momentum_logger import MomentumLogger
from .schemas.momentum_signal import CatalystEvent, CatalystType, MomentumSignal, SignalType
from .validation import validate_symbols
from .sentiment.sentiment_fetcher import SentimentFetcher
from .sentiment.sentiment_analyzer import SentimentAnalyzer
from .sentiment.sentiment_aggregator import SentimentAggregator
from .sentiment.models import SentimentScore

# Module logger
logger = logging.getLogger(__name__)


class CatalystDetector:
    """News-driven catalyst detection service.

    Scans breaking news (last 24 hours) from configured data provider and
    categorizes events into catalyst types (earnings, FDA, merger, product, analyst).

    Features:
    - Keyword-based categorization (extensible to ML models)
    - 24-hour lookback window (spec FR-001)
    - Graceful degradation (missing API key → empty results + warning)
    - Exponential backoff retry (spec NFR-003)
    - Thread-safe logging (spec NFR-005)

    Example:
        >>> config = MomentumConfig.from_env()
        >>> detector = CatalystDetector(config)
        >>> signals = await detector.scan(["AAPL", "GOOGL", "TSLA"])
        >>> for signal in signals:
        ...     print(f"{signal.symbol}: {signal.details['catalyst_type']}")
        AAPL: earnings
    """

    # Catalyst keyword mapping (from spec FR-002)
    # Priority order: EARNINGS → FDA → MERGER → PRODUCT → ANALYST
    CATALYST_KEYWORDS = {
        CatalystType.EARNINGS: ["earnings", "eps", "revenue", "quarterly results", "guidance"],
        CatalystType.FDA: ["fda", "approval", "clinical trial", "drug", "phase"],
        CatalystType.MERGER: ["merger", "acquisition", "buyout", "takeover", "acquire"],
        CatalystType.PRODUCT: ["launch", "unveil", "release", "introduce", "product"],
        CatalystType.ANALYST: ["upgrade", "downgrade", "initiated", "price target", "rating"],
    }

    def __init__(self, config: MomentumConfig, momentum_logger: MomentumLogger | None = None):
        """Initialize catalyst detector with configuration and logging.

        Args:
            config: Momentum detection configuration (includes NEWS_API_KEY)
            momentum_logger: Optional logger instance (creates default if None)
        """
        self.config = config
        self.logger = momentum_logger or MomentumLogger()

        # Initialize sentiment pipeline if enabled
        if self.config.sentiment_enabled:
            try:
                self.sentiment_fetcher = SentimentFetcher(config)
                self.sentiment_analyzer = SentimentAnalyzer()
                self.sentiment_aggregator = SentimentAggregator()
                logger.info("Sentiment analysis pipeline initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize sentiment pipeline: {e}. Sentiment analysis disabled.")
                self.config.sentiment_enabled = False
        else:
            logger.info("Sentiment analysis disabled via SENTIMENT_ENABLED=false")

    async def scan(self, symbols: list[str]) -> list[MomentumSignal]:
        """Scan for catalyst events in last 24 hours.

        Implements graceful degradation per spec Dependencies and Blockers:
        - If NEWS_API_KEY missing → log warning, return empty list, NO exception
        - If API fails → retry with exponential backoff (max 3 attempts)
        - If all retries fail → log error, return empty list

        Args:
            symbols: List of stock ticker symbols to scan (e.g., ["AAPL", "GOOGL"])

        Returns:
            List of MomentumSignal objects with catalyst events (empty if no catalysts or API unavailable)

        Raises:
            ValueError: If symbols list is empty or contains invalid symbols

        Example:
            >>> config = MomentumConfig(news_api_key="test-key")
            >>> detector = CatalystDetector(config)
            >>> signals = await detector.scan(["AAPL"])
            >>> len(signals) > 0
            True
        """
        # T056: Input validation (fail fast)
        try:
            validate_symbols(symbols)
        except ValueError as e:
            logger.error(f"CatalystDetector input validation failed: {e}")
            self.logger.log_error(
                e,
                {
                    "detector": "CatalystDetector",
                    "operation": "scan",
                    "symbols": symbols,
                    "validation_error": str(e),
                }
            )
            raise  # Re-raise ValueError to fail fast

        # T016: Check if Alpaca API credentials are configured (graceful degradation)
        if not self.config.alpaca_api_key or not self.config.alpaca_secret_key:
            logger.warning(
                "Alpaca API credentials not configured, catalyst detection skipped. "
                "Set ALPACA_API_KEY and ALPACA_SECRET_KEY environment variables to enable catalyst detection."
            )
            return []  # Graceful degradation: return empty list, don't crash

        try:
            # Fetch news from Alpaca API (with retry logic built into @with_retry decorator)
            news_data = await self._fetch_news_from_alpaca(symbols)

            # Filter news to last 24 hours and build signals
            signals = self._process_news_data(news_data, symbols)

            # Enrich signals with sentiment scores (if sentiment enabled)
            if self.config.sentiment_enabled:
                signals = await self._enrich_with_sentiment(signals)

            # Log each detected signal
            for signal in signals:
                signal_dict = {
                    "signal_type": signal.signal_type.value,
                    "symbol": signal.symbol,
                    "strength": signal.strength,
                    "detected_at": signal.detected_at.isoformat(),
                    "details": signal.details,
                }
                self.logger.log_signal(signal_dict, {"source": "catalyst"})

            return signals

        except TimeoutError as e:
            # T055: API timeout - log warning, return empty (graceful degradation)
            logger.warning(
                f"API timeout while fetching catalyst news for {len(symbols)} symbols: {e}. "
                f"Check NEWS_API_KEY validity and network connection. Retry logic will handle transient issues."
            )
            self.logger.log_error(
                e,
                {
                    "detector": "CatalystDetector",
                    "operation": "scan",
                    "symbols": symbols,
                    "error_type": "timeout",
                    "retry_exhausted": True,
                }
            )
            return []  # Graceful degradation: continue processing other detectors

        except (ConnectionError, OSError) as e:
            # T055: Network error - log error, return empty (graceful degradation)
            logger.error(
                f"Network error while fetching catalyst news for {len(symbols)} symbols: {e}. "
                f"Check network connectivity and NEWS_API endpoint availability."
            )
            self.logger.log_error(
                e,
                {
                    "detector": "CatalystDetector",
                    "operation": "scan",
                    "symbols": symbols,
                    "error_type": "network",
                }
            )
            return []  # Graceful degradation

        except (KeyError, ValueError, TypeError) as e:
            # T055: Malformed API response - log error, return empty (graceful degradation)
            logger.error(
                f"Malformed API response while processing catalyst news: {e}. "
                f"Expected structure: {{'news': [{{'headline': str, 'created_at': str, ...}}]}}. "
                f"Check NEWS_API provider compatibility."
            )
            self.logger.log_error(
                e,
                {
                    "detector": "CatalystDetector",
                    "operation": "scan",
                    "symbols": symbols,
                    "error_type": "malformed_response",
                }
            )
            return []  # Graceful degradation

        except NotImplementedError:
            # T055: API integration pending - log info, return empty
            logger.info(
                f"CatalystDetector API integration pending (NotImplementedError). "
                f"Returning empty signals for {len(symbols)} symbols."
            )
            return []  # Expected during MVP development

        except Exception as e:
            # T055: Unexpected error - log error with full context, return empty (graceful degradation)
            logger.error(
                f"Unexpected error in CatalystDetector.scan() for {len(symbols)} symbols: {e}. "
                f"This should not happen - investigate immediately."
            )
            self.logger.log_error(
                e,
                {
                    "detector": "CatalystDetector",
                    "operation": "scan",
                    "symbols": symbols,
                    "error_type": "unexpected",
                }
            )
            return []  # Graceful degradation: don't crash entire momentum scan

    @with_retry()  # Uses DEFAULT_POLICY: 3 retries, exponential backoff
    async def _fetch_news_with_retry(self, symbols: list[str]) -> list[CatalystEvent]:
        """Fetch news from data provider with retry logic.

        Internal method wrapped with @with_retry decorator for exponential backoff.
        Delegates to _fetch_news() for actual API call.

        Args:
            symbols: List of stock ticker symbols

        Returns:
            List of CatalystEvent objects from last 24 hours

        Raises:
            Exception: Re-raises any exception after 3 retry attempts
        """
        return await self._fetch_news(symbols)

    async def _fetch_news(self, symbols: list[str]) -> list[CatalystEvent]:
        """Fetch news from Alpaca API (or configured provider).

        TODO: Replace stub with actual Alpaca API integration when market-data-module available.
        For now, returns empty list (MVP stub).

        Args:
            symbols: List of stock ticker symbols

        Returns:
            List of CatalystEvent objects from last 24 hours
        """
        # STUB: Actual implementation will use Alpaca News API
        # See spec Dependencies and Blockers: news-api-integration not implemented
        logger.info(f"CatalystDetector stub: Would fetch news for {len(symbols)} symbols")
        return []

    async def _fetch_news_from_alpaca(self, symbols: list[str]) -> dict:
        """Fetch news from Alpaca API with retry logic.

        This method makes actual HTTP requests to Alpaca News API.
        API endpoint: https://data.alpaca.markets/v1beta1/news

        Args:
            symbols: List of stock ticker symbols

        Returns:
            dict: Alpaca API response with news items in format:
                {
                    "news": [
                        {
                            "headline": str,
                            "created_at": str (ISO 8601),
                            "symbols": List[str],
                            "source": str
                        },
                        ...
                    ]
                }

        Raises:
            ConnectionError: If API request fails
            TimeoutError: If request times out
            ValueError: If API credentials are missing
        """
        # Check if Alpaca API credentials are configured
        if not self.config.alpaca_api_key or not self.config.alpaca_secret_key:
            logger.warning(
                "Alpaca API credentials not configured. Set ALPACA_API_KEY and "
                "ALPACA_SECRET_KEY environment variables to enable news catalyst detection."
            )
            return {"news": []}  # Return empty news list (graceful degradation)

        # Calculate 24-hour lookback window
        now = datetime.now(UTC)
        start_time = now - timedelta(hours=24)

        # Build API request
        url = "https://data.alpaca.markets/v1beta1/news"
        headers = {
            "APCA-API-KEY-ID": self.config.alpaca_api_key,
            "APCA-API-SECRET-KEY": self.config.alpaca_secret_key,
        }
        params = {
            "symbols": ",".join(symbols),  # Comma-separated symbol list
            "start": start_time.isoformat(),
            "limit": 50,  # Fetch up to 50 news items
            "sort": "desc",  # Most recent first
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=headers, params=params)
                response.raise_for_status()  # Raise HTTPError for 4xx/5xx responses

                data = response.json()
                logger.info(
                    f"Fetched {len(data.get('news', []))} news items from Alpaca for "
                    f"{len(symbols)} symbols"
                )
                return data

        except httpx.TimeoutException as e:
            logger.error(f"Alpaca News API request timed out after 10 seconds: {e}")
            raise TimeoutError(f"Alpaca News API timeout: {e}") from e

        except httpx.HTTPStatusError as e:
            logger.error(
                f"Alpaca News API returned HTTP {e.response.status_code}: "
                f"{e.response.text}"
            )
            raise ConnectionError(
                f"Alpaca News API HTTP error {e.response.status_code}"
            ) from e

        except httpx.RequestError as e:
            logger.error(f"Alpaca News API request failed: {e}")
            raise ConnectionError(f"Alpaca News API request error: {e}") from e

        except Exception as e:
            logger.error(f"Unexpected error fetching news from Alpaca: {e}")
            raise

    def _process_news_data(self, news_data: dict, symbols: list[str]) -> list[MomentumSignal]:
        """Process raw news data and build MomentumSignal objects.

        Filters news to last 24 hours, categorizes catalyst types, and builds signals.

        Args:
            news_data: Raw response from Alpaca API
            symbols: List of symbols being scanned

        Returns:
            List[MomentumSignal]: Processed momentum signals
        """
        signals = []
        now = datetime.now(UTC)
        cutoff_time = now - timedelta(hours=24)

        # Extract news items from response
        news_items = news_data.get("news", [])

        for news_item in news_items:
            try:
                # Parse published timestamp
                published_at = datetime.fromisoformat(news_item["created_at"].replace("Z", "+00:00"))

                # Filter: only include news from last 24 hours
                if published_at < cutoff_time:
                    continue

                # Extract headline and symbols
                headline = news_item.get("headline", "")
                news_symbols = news_item.get("symbols", [])

                # Skip if headline is empty or no symbols
                if not headline or not news_symbols:
                    continue

                # Categorize catalyst type
                catalyst_type = self.categorize(headline)

                # Build MomentumSignal for each symbol in the news
                for symbol in news_symbols:
                    # Only include symbols we're scanning for
                    if symbol not in symbols:
                        continue

                    # Calculate strength
                    strength = self._calculate_catalyst_strength(catalyst_type, published_at)

                    # Filter by min_catalyst_strength threshold
                    if strength < self.config.min_catalyst_strength:
                        continue

                    signal = MomentumSignal(
                        symbol=symbol,
                        signal_type=SignalType.CATALYST,
                        strength=strength,
                        detected_at=now,
                        details={
                            "headline": headline,
                            "catalyst_type": catalyst_type.value,
                            "published_at": published_at.isoformat(),
                            "source": news_item.get("source", "Unknown"),
                        },
                    )
                    signals.append(signal)

            except (KeyError, ValueError) as e:
                # Skip malformed news items (log but continue processing)
                logger.debug(f"Skipping malformed news item: {e}")
                continue

        return signals

    def _calculate_catalyst_strength(self, catalyst_type: CatalystType, published_at: datetime) -> float:
        """Calculate catalyst signal strength (0-100) based on type and recency.

        Strength formula:
        - Base strength by catalyst type:
          - EARNINGS: 80 (high impact)
          - FDA: 85 (very high impact)
          - MERGER: 90 (highest impact)
          - PRODUCT: 70 (medium-high impact)
          - ANALYST: 60 (medium impact)
        - Recency bonus: -1 point per hour old (max 24 hours)

        Args:
            catalyst_type: Type of catalyst
            published_at: When news was published (UTC)

        Returns:
            float: Strength score (0-100)
        """
        # Base strength by catalyst type
        base_strengths = {
            CatalystType.EARNINGS: 80.0,
            CatalystType.FDA: 85.0,
            CatalystType.MERGER: 90.0,
            CatalystType.PRODUCT: 70.0,
            CatalystType.ANALYST: 60.0,
        }

        base_strength = base_strengths.get(catalyst_type, 50.0)

        # Calculate recency penalty (fresher news = higher strength)
        now = datetime.now(UTC)
        hours_old = (now - published_at).total_seconds() / 3600
        recency_penalty = min(hours_old, 24.0)  # Cap at 24 hours

        # Final strength: base - recency penalty
        strength = max(0.0, base_strength - recency_penalty)

        return round(strength, 1)

    def categorize(self, headline: str) -> CatalystType:
        """Categorize news headline into catalyst type using keyword matching.

        Uses keyword-based classification (extensible to ML models in future).
        Returns CatalystType.ANALYST as default if no keywords match.

        Args:
            headline: News headline text (case-insensitive matching)

        Returns:
            CatalystType enum value (EARNINGS, FDA, MERGER, PRODUCT, ANALYST)

        Example:
            >>> detector = CatalystDetector(MomentumConfig())
            >>> detector.categorize("Company announces Q4 earnings beat")
            <CatalystType.EARNINGS: 'earnings'>
            >>> detector.categorize("FDA approves new drug")
            <CatalystType.FDA: 'fda'>
        """
        headline_lower = headline.lower()

        # Check each catalyst type's keywords
        for catalyst_type, keywords in self.CATALYST_KEYWORDS.items():
            if any(keyword.lower() in headline_lower for keyword in keywords):
                return catalyst_type

        # Default: PRODUCT (most generic category)
        return CatalystType.PRODUCT

    def _convert_events_to_signals(self, events: list[CatalystEvent]) -> list[MomentumSignal]:
        """Convert CatalystEvent objects to MomentumSignal objects.

        Calculates signal strength based on catalyst type and recency.
        More recent news gets higher strength score.

        Args:
            events: List of CatalystEvent objects

        Returns:
            List of MomentumSignal objects with strength scores
        """
        signals = []
        now = datetime.now(UTC)

        for event in events:
            # Calculate recency factor (fresher news = higher score)
            hours_ago = (now - event.published_at).total_seconds() / 3600
            recency_factor = max(0, 100 - (hours_ago / 24) * 100)  # 100 at 0h, 0 at 24h

            # Calculate base strength by catalyst type (arbitrary weights, tune later)
            type_weights = {
                CatalystType.EARNINGS: 0.9,
                CatalystType.FDA: 0.95,
                CatalystType.MERGER: 0.85,
                CatalystType.PRODUCT: 0.7,
                CatalystType.ANALYST: 0.75,
            }
            base_strength = type_weights.get(event.catalyst_type, 0.5)

            # Final strength: blend recency and type importance
            strength = recency_factor * base_strength

            # Build signal details
            details = {
                "catalyst_type": event.catalyst_type.value,
                "headline": event.headline,
                "published_at": event.published_at.isoformat(),
                "source": event.source,
            }

            # Create MomentumSignal (symbol extracted from event context)
            # Note: Need to add symbol tracking in _fetch_news() when implemented
            signal = MomentumSignal(
                symbol="STUB",  # TODO: Extract from news API response
                signal_type=SignalType.CATALYST,
                strength=strength,
                detected_at=now,
                details=details,
            )

            signals.append(signal)

        return signals

    async def _enrich_with_sentiment(self, signals: list[MomentumSignal]) -> list[MomentumSignal]:
        """Enrich catalyst signals with sentiment scores.

        For each signal, fetches social media posts, analyzes sentiment, and adds
        sentiment_score to signal details. Implements graceful degradation.

        Args:
            signals: List of MomentumSignal objects from catalyst detection

        Returns:
            List[MomentumSignal]: Same signals enriched with sentiment_score in details

        Notes:
            - Sentiment score added to signal.details["sentiment_score"]
            - If sentiment analysis fails, sentiment_score=None (graceful degradation)
            - Feature flag: Skip if self.config.sentiment_enabled=False
        """
        if not signals:
            return signals

        enriched_signals = []

        for signal in signals:
            symbol = signal.symbol

            try:
                # Fetch social media posts (Twitter + Reddit)
                posts = self.sentiment_fetcher.fetch_all(symbol, minutes=30)

                if not posts:
                    # No posts found, set sentiment_score=None
                    logger.debug(f"No social media posts found for {symbol}")
                    signal.details["sentiment_score"] = None
                    enriched_signals.append(signal)
                    continue

                # Analyze sentiment for each post
                post_texts = [post.text for post in posts]
                sentiment_results = self.sentiment_analyzer.analyze_batch(post_texts)

                # Convert sentiment results to scores
                # FinBERT returns {negative, neutral, positive} probabilities
                # Convert to score: positive - negative (range -1.0 to +1.0)
                scores = []
                for result in sentiment_results:
                    if result is None:
                        continue
                    score = result.get("positive", 0.0) - result.get("negative", 0.0)
                    scores.append(score)

                if not scores:
                    # No valid sentiment scores
                    signal.details["sentiment_score"] = None
                    enriched_signals.append(signal)
                    continue

                # Create SentimentScore objects for aggregation
                now = datetime.now(UTC)
                sentiment_score_obj = SentimentScore(
                    symbol=symbol,
                    score=sum(scores) / len(scores),  # Simple average for now
                    confidence=0.85,  # Placeholder confidence
                    post_count=len(posts),
                    timestamp=now
                )

                # Aggregate with recency weighting
                aggregated_score = self.sentiment_aggregator.aggregate([sentiment_score_obj])

                # Add sentiment score to signal details
                signal.details["sentiment_score"] = aggregated_score

                logger.debug(
                    f"Enriched {symbol} signal with sentiment: {aggregated_score:.3f} "
                    f"(from {len(posts)} posts)"
                )

                enriched_signals.append(signal)

            except Exception as e:
                # Graceful degradation: Log error, set sentiment_score=None
                logger.warning(
                    f"Failed to fetch sentiment for {symbol}: {e}. "
                    f"Continuing with sentiment_score=None"
                )
                signal.details["sentiment_score"] = None
                enriched_signals.append(signal)

        return enriched_signals
