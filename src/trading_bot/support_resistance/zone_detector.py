"""
Support/Resistance Zone Detector Service

Identifies support and resistance zones from historical OHLCV data by detecting
swing points, clustering them, and calculating strength scores.

Constitution v1.0.0:
- §Safety_First: Manual review required, no auto-trading
- §Risk_Management: Input validation, graceful degradation
- §Data_Integrity: Zone validation before signal generation

Feature: support-resistance-mapping
Tasks: T010-T013 - Zone detection implementation
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal

import numpy as np
import pandas as pd

from ..market_data.market_data_service import MarketDataService
from .config import ZoneDetectionConfig
from .models import Timeframe, TouchType, Zone, ZoneTouch, ZoneType
from .zone_logger import ZoneLogger

# Module logger
logger = logging.getLogger(__name__)


class ZoneDetector:
    """Support/resistance zone detection service.

    Detects support/resistance zones with the following algorithm:
    1. Identify swing highs and swing lows from historical OHLCV
    2. Cluster swing points within tolerance_pct (default 1.5%)
    3. Filter clusters with >= touch_threshold touches (3 for daily, 2 for 4h)
    4. Calculate strength scores (touch_count + volume_bonus)
    5. Return sorted zones by strength descending

    Features:
    - Daily and 4-hour timeframe support
    - Configurable touch threshold and tolerance
    - Volume-weighted strength scoring
    - Graceful degradation (missing data → empty results + warning)

    Example:
        >>> config = ZoneDetectionConfig.from_env()
        >>> market_data = MarketDataService(...)
        >>> detector = ZoneDetector(config, market_data)
        >>> zones = detector.detect_zones("AAPL", days=60, timeframe=Timeframe.DAILY)
        >>> for zone in zones:
        ...     print(f"{zone.zone_type.value} at ${zone.price_level}: strength {zone.strength_score}")
    """

    def __init__(
        self,
        config: ZoneDetectionConfig,
        market_data_service: MarketDataService,
        zone_logger: ZoneLogger | None = None,
    ):
        """Initialize zone detector with configuration and dependencies.

        Args:
            config: Zone detection configuration
            market_data_service: Service for fetching historical market data
            zone_logger: Optional logger instance (creates default if None)
        """
        self.config = config
        self.market_data = market_data_service
        self.logger = zone_logger or ZoneLogger()

    def detect_zones(
        self,
        symbol: str,
        days: int,
        timeframe: Timeframe = Timeframe.DAILY
    ) -> list[Zone]:
        """Detect support and resistance zones from historical price data.

        Fetches OHLCV data via MarketDataService, identifies swing points,
        clusters them into zones, and calculates strength scores.

        Args:
            symbol: Stock ticker symbol (e.g., "AAPL")
            days: Number of historical days to analyze (minimum 30, ideal 60+)
            timeframe: DAILY or FOUR_HOUR timeframe

        Returns:
            List of Zone objects sorted by strength_score descending
            Empty list if days < 30 or data unavailable

        Raises:
            ValueError: If symbol is empty or days < 0

        Example:
            >>> zones = detector.detect_zones("AAPL", days=60, timeframe=Timeframe.DAILY)
            >>> len(zones)
            5
            >>> zones[0].strength_score
            Decimal('7.0')
        """
        # Input validation
        if not symbol or not symbol.strip():
            raise ValueError("symbol must be non-empty")
        if days < 0:
            raise ValueError("days must be non-negative")

        # Graceful degradation: warn if insufficient days
        if days < self.config.min_days:
            logger.warning(
                f"Insufficient days for {symbol}: {days} < {self.config.min_days} (minimum). "
                f"Zone detection may be unreliable. Consider using 60+ days."
            )
            return []

        # Fetch OHLCV data
        try:
            # Calculate start date
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            # Fetch data via MarketDataService
            # Note: Actual implementation would use async/await or sync fetch
            # For now, assuming sync API
            ohlcv = self._fetch_ohlcv(symbol, start_date, end_date, timeframe)

            if ohlcv is None or ohlcv.empty:
                logger.warning(f"No data available for {symbol}, returning empty zones")
                return []

        except Exception as e:
            logger.error(f"Failed to fetch data for {symbol}: {e}")
            return []

        # Step 1-2: Identify and cluster swing points
        swing_highs = self._identify_swing_highs(ohlcv)
        swing_lows = self._identify_swing_lows(ohlcv)

        high_clusters = self._cluster_swing_points(swing_highs, self.config.tolerance_pct)
        low_clusters = self._cluster_swing_points(swing_lows, self.config.tolerance_pct)

        # Step 3-4: Build zones from clusters
        touch_threshold = self.config.touch_threshold

        resistance_zones = self._build_zones_from_clusters(
            high_clusters,
            ZoneType.RESISTANCE,
            ohlcv,
            touch_threshold,
            timeframe
        )

        support_zones = self._build_zones_from_clusters(
            low_clusters,
            ZoneType.SUPPORT,
            ohlcv,
            touch_threshold,
            timeframe
        )

        # Combine and sort by strength
        all_zones = resistance_zones + support_zones
        all_zones.sort(key=lambda z: z.strength_score, reverse=True)

        # Log detection event
        self.logger.log_zone_detection(
            symbol,
            all_zones,
            {
                "days_analyzed": days,
                "touch_threshold": touch_threshold,
                "zones_found": len(all_zones),
                "timeframe": timeframe.value
            }
        )

        return all_zones

    def _fetch_ohlcv(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        timeframe: Timeframe
    ) -> pd.DataFrame:
        """Fetch OHLCV data from MarketDataService.

        Args:
            symbol: Stock symbol
            start_date: Start of historical range
            end_date: End of historical range
            timeframe: DAILY or FOUR_HOUR

        Returns:
            DataFrame with columns: date, open, high, low, close, volume
            Or empty DataFrame if data unavailable
        """
        try:
            # Map timeframe to interval parameter
            interval = "day" if timeframe == Timeframe.DAILY else "5minute"

            # Calculate days in range
            days_delta = (end_date - start_date).days

            # Map days to span parameter (robin_stocks API constraint)
            if days_delta <= 7:
                span = "week"
            elif days_delta <= 31:
                span = "month"
            elif days_delta <= 90:
                span = "3month"
            elif days_delta <= 365:
                span = "year"
            else:
                span = "5year"

            logger.debug(f"Fetching OHLCV for {symbol} from {start_date} to {end_date} (interval={interval}, span={span})")

            # Fetch from MarketDataService
            df = self.market_data.get_historical_data(symbol, interval=interval, span=span)

            if df.empty:
                logger.warning(f"No OHLCV data returned for {symbol}")
                return df

            # Parse date column to datetime
            df['date'] = pd.to_datetime(df['date'])

            # Filter to requested date range
            df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]

            # Convert price/volume columns to appropriate types
            for col in ['open', 'high', 'low', 'close']:
                df[col] = df[col].astype(float)
            df['volume'] = df['volume'].astype(float)

            logger.info(f"Fetched {len(df)} bars for {symbol} ({timeframe.value})")
            return df

        except Exception as e:
            logger.error(f"Failed to fetch OHLCV for {symbol}: {e}")
            return pd.DataFrame()

    def _identify_swing_highs(
        self,
        ohlcv: pd.DataFrame
    ) -> list[tuple[datetime, Decimal]]:
        """Identify swing high points from OHLCV data.

        A swing high occurs when a bar's high is greater than both the
        previous and next bar's high.

        Args:
            ohlcv: DataFrame with 'date', 'high' columns

        Returns:
            List of (date, price) tuples for swing highs

        Example:
            >>> ohlcv = pd.DataFrame({
            ...     'date': [...],
            ...     'high': [100, 105, 102, ...]  # 105 is swing high
            ... })
            >>> swings = detector._identify_swing_highs(ohlcv)
            >>> swings[0]
            (datetime(...), Decimal('105.00'))
        """
        if ohlcv.empty or len(ohlcv) < 3:
            return []

        swing_highs = []

        # Iterate from index 1 to len-2 (skip first and last bars)
        for i in range(1, len(ohlcv) - 1):
            current_high = ohlcv.iloc[i]['high']
            prev_high = ohlcv.iloc[i - 1]['high']
            next_high = ohlcv.iloc[i + 1]['high']

            # Swing high: current > prev AND current > next
            if current_high > prev_high and current_high > next_high:
                date = ohlcv.iloc[i]['date']
                swing_highs.append((date, Decimal(str(current_high))))

        return swing_highs

    def _identify_swing_lows(
        self,
        ohlcv: pd.DataFrame
    ) -> list[tuple[datetime, Decimal]]:
        """Identify swing low points from OHLCV data.

        A swing low occurs when a bar's low is less than both the
        previous and next bar's low.

        Args:
            ohlcv: DataFrame with 'date', 'low' columns

        Returns:
            List of (date, price) tuples for swing lows

        Example:
            >>> ohlcv = pd.DataFrame({
            ...     'date': [...],
            ...     'low': [100, 95, 102, ...]  # 95 is swing low
            ... })
            >>> swings = detector._identify_swing_lows(ohlcv)
            >>> swings[0]
            (datetime(...), Decimal('95.00'))
        """
        if ohlcv.empty or len(ohlcv) < 3:
            return []

        swing_lows = []

        # Iterate from index 1 to len-2 (skip first and last bars)
        for i in range(1, len(ohlcv) - 1):
            current_low = ohlcv.iloc[i]['low']
            prev_low = ohlcv.iloc[i - 1]['low']
            next_low = ohlcv.iloc[i + 1]['low']

            # Swing low: current < prev AND current < next
            if current_low < prev_low and current_low < next_low:
                date = ohlcv.iloc[i]['date']
                swing_lows.append((date, Decimal(str(current_low))))

        return swing_lows

    def _cluster_swing_points(
        self,
        swing_points: list[tuple[datetime, Decimal]],
        tolerance_pct: Decimal
    ) -> list[list[tuple[datetime, Decimal]]]:
        """Cluster swing points within tolerance percentage.

        Groups swing points where price difference is <= tolerance_pct.
        Uses simple greedy clustering: each point joins the first cluster
        within tolerance, or creates a new cluster.

        Args:
            swing_points: List of (date, price) tuples
            tolerance_pct: Price tolerance as percentage (e.g., 1.5 for 1.5%)

        Returns:
            List of clusters, where each cluster is a list of (date, price) tuples

        Example:
            >>> swings = [
            ...     (date1, Decimal('100.00')),
            ...     (date2, Decimal('101.00')),  # Within 1.5% of 100
            ...     (date3, Decimal('110.00'))   # >1.5% away, new cluster
            ... ]
            >>> clusters = detector._cluster_swing_points(swings, Decimal('1.5'))
            >>> len(clusters)
            2
            >>> len(clusters[0])
            2
        """
        if not swing_points:
            return []

        clusters: list[list[tuple[datetime, Decimal]]] = []

        for date, price in swing_points:
            # Find first cluster within tolerance
            assigned = False

            for cluster in clusters:
                # Check if price is within tolerance of cluster median
                cluster_prices = [p for _, p in cluster]
                cluster_median = Decimal(str(np.median([float(p) for p in cluster_prices])))

                # Calculate percentage difference
                pct_diff = abs((price - cluster_median) / cluster_median) * Decimal('100')

                if pct_diff <= tolerance_pct:
                    cluster.append((date, price))
                    assigned = True
                    break

            # Create new cluster if not assigned
            if not assigned:
                clusters.append([(date, price)])

        return clusters

    def _calculate_strength_score(
        self,
        touches: list[ZoneTouch],
        avg_volume: Decimal
    ) -> Decimal:
        """Calculate zone strength score with volume bonus.

        Formula: base_score (touch count) + volume_bonus
        Volume bonus: +1 for each touch with volume > 1.5x average

        Args:
            touches: List of ZoneTouch objects for the zone
            avg_volume: Average volume across all touches

        Returns:
            Strength score as Decimal

        Example:
            >>> touches = [
            ...     ZoneTouch(..., volume=Decimal("1000000")),  # Normal
            ...     ZoneTouch(..., volume=Decimal("2000000")),  # High (>1.5x)
            ...     ZoneTouch(..., volume=Decimal("3000000"))   # High (>1.5x)
            ... ]
            >>> score = detector._calculate_strength_score(touches, Decimal("1000000"))
            >>> score
            Decimal('5')  # 3 touches + 2 high-volume bonus
        """
        base_score = len(touches)

        # Calculate volume bonus
        volume_threshold = avg_volume * self.config.volume_threshold  # Default 1.5x
        volume_bonus = sum(
            1 for touch in touches
            if touch.volume > volume_threshold
        )

        return Decimal(str(base_score + volume_bonus))

    def _build_zones_from_clusters(
        self,
        clusters: list[list[tuple[datetime, Decimal]]],
        zone_type: ZoneType,
        ohlcv: pd.DataFrame,
        touch_threshold: int,
        timeframe: Timeframe
    ) -> list[Zone]:
        """Build Zone objects from clustered swing points.

        Filters clusters by touch count, calculates metadata (price level,
        dates, volume metrics), and creates Zone objects.

        Args:
            clusters: List of swing point clusters
            zone_type: SUPPORT or RESISTANCE
            ohlcv: DataFrame with volume data for metadata calculation
            touch_threshold: Minimum touches to qualify as a zone
            timeframe: DAILY or FOUR_HOUR

        Returns:
            List of Zone objects (only clusters with >= touch_threshold touches)

        Example:
            >>> clusters = [
            ...     [(date1, Decimal('100.00')), (date2, Decimal('101.00')), (date3, Decimal('100.50'))],
            ...     [(date4, Decimal('110.00'))]  # Only 1 touch, filtered out
            ... ]
            >>> zones = detector._build_zones_from_clusters(
            ...     clusters, ZoneType.SUPPORT, ohlcv, touch_threshold=3, Timeframe.DAILY
            ... )
            >>> len(zones)
            1
            >>> zones[0].touch_count
            3
        """
        zones = []

        for cluster in clusters:
            touch_count = len(cluster)

            # Filter by touch threshold
            if touch_count < touch_threshold:
                continue

            # Calculate price level (median of cluster)
            cluster_prices = [p for _, p in cluster]
            price_level = Decimal(str(np.median([float(p) for p in cluster_prices])))

            # Calculate first/last touch dates
            cluster_dates = [d for d, _ in cluster]
            first_touch_date = min(cluster_dates)
            last_touch_date = max(cluster_dates)

            # Calculate volume metrics from OHLCV data
            # Match touch dates to OHLCV bars and extract volumes
            touch_volumes = []
            if not ohlcv.empty and 'date' in ohlcv.columns and 'volume' in ohlcv.columns:
                for touch_date, _ in cluster:
                    # Find matching bar in OHLCV (pandas datetime comparison)
                    matching_rows = ohlcv[ohlcv['date'] == touch_date]
                    if not matching_rows.empty:
                        volume = Decimal(str(matching_rows.iloc[0]['volume']))
                        touch_volumes.append(volume)
                    else:
                        # Fallback: use average volume from entire dataset if exact date not found
                        logger.debug(f"No volume data for touch date {touch_date}, using dataset average")
                        volume = Decimal(str(ohlcv['volume'].mean()))
                        touch_volumes.append(volume)

            # Calculate volume statistics
            if touch_volumes:
                average_volume = Decimal(str(np.mean([float(v) for v in touch_volumes])))
                highest_volume_touch = max(touch_volumes)
            else:
                # Fallback if no volumes found
                logger.warning("No volume data available for cluster, using defaults")
                average_volume = Decimal("1000000")
                highest_volume_touch = Decimal("1500000")

            # Calculate strength score using volume bonus
            # Create ZoneTouch objects for strength calculation
            touches = [
                ZoneTouch(
                    zone_id="",  # Will be set by Zone
                    touch_date=date,
                    price=price,
                    volume=touch_volumes[i] if i < len(touch_volumes) else average_volume,
                    touch_type=TouchType.BOUNCE
                )
                for i, (date, price) in enumerate(cluster)
            ]

            strength_score = self._calculate_strength_score(touches, average_volume)

            # Create Zone object
            zone = Zone(
                price_level=price_level,
                zone_type=zone_type,
                strength_score=strength_score,
                touch_count=touch_count,
                first_touch_date=first_touch_date,
                last_touch_date=last_touch_date,
                average_volume=average_volume,
                highest_volume_touch=highest_volume_touch,
                timeframe=timeframe
            )

            zones.append(zone)

        return zones
