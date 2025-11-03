"""
Watchlist Service

Generates dynamic watchlists by combining sector tags + screener filters.

Constitution v1.0.0:
- §Code_Quality: Type hints required
- §Data_Integrity: Validate all inputs
- §Risk_Management: Graceful degradation on errors

Usage:
    config = WatchlistConfig(...)
    service = WatchlistService(screener_service, config)
    result = service.generate_watchlist()
    symbols = result.symbols  # Use for momentum scanning
"""

import logging
import time
from datetime import datetime, UTC
from decimal import Decimal

import robin_stocks.robinhood as r

from trading_bot.schemas.screener_schemas import ScreenerQuery
from trading_bot.schemas.watchlist_schemas import (
    GeneratedWatchlist,
    WatchlistConfig,
    WatchlistTier,
)
from trading_bot.services.screener_service import ScreenerService

logger = logging.getLogger(__name__)


class WatchlistService:
    """Service for generating dynamic watchlists from sectors and screener criteria.

    Workflow:
    1. Fetch stocks by sector via Robin Stocks market tags
    2. Apply tier-specific screener filters
    3. Sort by volume descending, take top N per tier
    4. Combine tiers into final watchlist

    Attributes:
        screener_service: ScreenerService instance for filtering
        config: WatchlistConfig with tier definitions and criteria
    """

    def __init__(self, screener_service: ScreenerService, config: WatchlistConfig):
        """Initialize watchlist service.

        Args:
            screener_service: ScreenerService for filtering stocks
            config: WatchlistConfig with tier configurations

        Raises:
            ValueError: If config is invalid
        """
        config.validate()
        self.screener_service = screener_service
        self.config = config

    def generate_watchlist(self) -> GeneratedWatchlist:
        """Generate watchlist from configured tiers and sectors.

        Returns:
            GeneratedWatchlist with symbols, metadata, and execution time

        Raises:
            RuntimeError: If generation fails and no fallback available
        """
        start_time = time.time()
        logger.info("Starting watchlist generation...")

        all_symbols: list[str] = []
        tier_breakdown: dict[str, int] = {}
        criteria_used: dict[str, dict] = {}
        warnings: list[str] = []

        try:
            # Process each enabled tier
            enabled_tiers = self.config.get_enabled_tiers()
            logger.info(f"Processing {len(enabled_tiers)} enabled tiers")

            for tier in enabled_tiers:
                logger.info(f"Processing tier: {tier.name}")

                # Fetch and filter symbols for this tier
                tier_symbols = self._process_tier(tier)

                # Limit to max_symbols per tier
                tier_symbols = tier_symbols[: tier.max_symbols]

                # Track results
                all_symbols.extend(tier_symbols)
                tier_breakdown[tier.name] = len(tier_symbols)
                criteria_used[tier.name] = self._criteria_to_dict(tier.criteria)

                # Warn if insufficient symbols
                if len(tier_symbols) < tier.max_symbols:
                    warning = (
                        f"Tier '{tier.name}' returned {len(tier_symbols)} symbols "
                        f"(requested {tier.max_symbols})"
                    )
                    warnings.append(warning)
                    logger.warning(warning)

                logger.info(
                    f"Tier '{tier.name}' added {len(tier_symbols)} symbols: {tier_symbols[:5]}..."
                )

            # Remove duplicates (preserve order)
            all_symbols = list(dict.fromkeys(all_symbols))

            # Calculate execution time
            execution_time_ms = (time.time() - start_time) * 1000

            logger.info(
                f"Watchlist generation complete | Total={len(all_symbols)} | "
                f"Time={execution_time_ms:.2f}ms"
            )

            return GeneratedWatchlist(
                symbols=all_symbols,
                generated_at=datetime.now(UTC),
                tier_breakdown=tier_breakdown,
                total_symbols=len(all_symbols),
                criteria_used=criteria_used,
                execution_time_ms=execution_time_ms,
                warnings=warnings,
            )

        except Exception as e:
            logger.error(f"Watchlist generation failed: {e}", exc_info=True)

            # Fall back to static list
            if self.config.fallback_symbols:
                logger.warning(
                    f"Using fallback watchlist ({len(self.config.fallback_symbols)} symbols)"
                )
                execution_time_ms = (time.time() - start_time) * 1000

                return GeneratedWatchlist(
                    symbols=self.config.fallback_symbols,
                    generated_at=datetime.now(UTC),
                    tier_breakdown={"fallback": len(self.config.fallback_symbols)},
                    total_symbols=len(self.config.fallback_symbols),
                    criteria_used={"fallback": "static_list"},
                    execution_time_ms=execution_time_ms,
                    warnings=[f"Generation failed, using fallback: {str(e)}"],
                )
            else:
                raise RuntimeError(f"Watchlist generation failed and no fallback: {e}") from e

    def _process_tier(self, tier: WatchlistTier) -> list[str]:
        """Process a single tier: fetch sectors, filter, and sort.

        Args:
            tier: WatchlistTier configuration

        Returns:
            List of symbols meeting criteria, sorted by volume descending
        """
        # Fetch symbols from all sectors in this tier
        sector_symbols: list[str] = []

        for sector in tier.sectors:
            symbols = self._fetch_sector_symbols(sector)
            logger.info(f"Sector '{sector}' returned {len(symbols)} symbols")
            sector_symbols.extend(symbols)

        # Remove duplicates
        sector_symbols = list(set(sector_symbols))
        logger.info(
            f"Tier '{tier.name}' has {len(sector_symbols)} unique symbols across {len(tier.sectors)} sectors"
        )

        # If no symbols found, return empty
        if not sector_symbols:
            logger.warning(f"No symbols found for tier '{tier.name}' sectors: {tier.sectors}")
            return []

        # Build screener query from tier criteria
        query = self._build_screener_query(tier.criteria)

        # Filter with screener
        try:
            result = self.screener_service.filter(query, symbols=sector_symbols)
            filtered_symbols = [stock.symbol for stock in result.stocks]
            logger.info(
                f"Screener filtered {len(sector_symbols)} -> {len(filtered_symbols)} symbols"
            )
            return filtered_symbols

        except Exception as e:
            logger.error(f"Screener failed for tier '{tier.name}': {e}", exc_info=True)
            # Graceful degradation: return unfiltered symbols
            logger.warning(f"Returning unfiltered symbols for tier '{tier.name}'")
            return sector_symbols[: tier.max_symbols]

    def _fetch_sector_symbols(self, sector_tag: str) -> list[str]:
        """Fetch stock symbols for a sector tag via Robin Stocks API.

        Args:
            sector_tag: Robin Stocks market tag (e.g., "technology", "biopharmaceutical")

        Returns:
            List of stock symbols in that sector
        """
        try:
            # Fetch from Robin Stocks
            stocks = r.get_all_stocks_from_market_tag(sector_tag, info="symbol")

            if not stocks:
                logger.warning(f"No stocks found for sector tag: {sector_tag}")
                return []

            # Handle both list[str] and list[dict] returns
            if isinstance(stocks[0], dict):
                symbols = [stock["symbol"] for stock in stocks if "symbol" in stock]
            else:
                symbols = stocks

            logger.info(f"Fetched {len(symbols)} symbols from sector '{sector_tag}'")
            return symbols

        except Exception as e:
            logger.error(f"Failed to fetch sector '{sector_tag}': {e}", exc_info=True)
            return []

    def _build_screener_query(self, criteria: "TierCriteria") -> ScreenerQuery:
        """Convert TierCriteria to ScreenerQuery.

        Args:
            criteria: TierCriteria with filter parameters

        Returns:
            ScreenerQuery for screener service
        """
        return ScreenerQuery(
            min_price=criteria.min_price,
            max_price=criteria.max_price,
            relative_volume=criteria.relative_volume,
            float_max=criteria.float_max,
            min_daily_change=criteria.min_daily_change,
            limit=500,  # Max results per tier
            offset=0,
        )

    def _criteria_to_dict(self, criteria: "TierCriteria") -> dict:
        """Convert TierCriteria to dict for logging/metadata.

        Args:
            criteria: TierCriteria object

        Returns:
            Dictionary representation
        """
        return {
            "min_price": str(criteria.min_price) if criteria.min_price else None,
            "max_price": str(criteria.max_price) if criteria.max_price else None,
            "relative_volume": criteria.relative_volume,
            "min_daily_change": criteria.min_daily_change,
            "float_max": criteria.float_max,
        }

    def preview_tier(self, tier_name: str, limit: int = 10) -> list[str]:
        """Preview symbols for a specific tier without generating full watchlist.

        Useful for testing tier criteria.

        Args:
            tier_name: Name of tier to preview (e.g., "mega_cap")
            limit: Max symbols to return

        Returns:
            List of up to `limit` symbols for that tier

        Raises:
            ValueError: If tier not found or not enabled
        """
        # Find tier
        tier = None
        for t in self.config.tiers:
            if t.name == tier_name:
                tier = t
                break

        if not tier:
            raise ValueError(f"Tier '{tier_name}' not found in config")

        if not tier.enabled:
            raise ValueError(f"Tier '{tier_name}' is not enabled")

        # Process tier
        symbols = self._process_tier(tier)
        return symbols[:limit]
