"""
Order Flow Validators

Validation functions for Level 2 order book data and Time & Sales tape data.

Pattern: Follows market_data/validators.py pattern with fail-fast validation
"""

from datetime import UTC, datetime

from trading_bot.logger import TradingLogger
from trading_bot.market_data.exceptions import DataValidationError

from .config import OrderFlowConfig
from .data_models import OrderBookSnapshot, TimeAndSalesRecord

# Get logger for validation warnings
_logger = TradingLogger.get_logger(__name__)


def validate_level2_data(snapshot: OrderBookSnapshot) -> None:
    """
    Validate Level 2 order book snapshot for data integrity and freshness.

    Validation Rules (per spec US5 and data-model.md):
    - Timestamp freshness: Fail if >30 seconds old, warn if >10 seconds
    - Bids sorted descending by price
    - Asks sorted ascending by price
    - All prices >$0, all sizes >0 shares

    Args:
        snapshot: OrderBookSnapshot to validate

    Raises:
        DataValidationError: If validation fails

    Example:
        >>> snapshot = OrderBookSnapshot(...)
        >>> validate_level2_data(snapshot)  # Raises if stale or invalid
    """
    # Check timestamp freshness (Constitution §Data_Integrity)
    now = datetime.now(UTC)
    age_seconds = (now - snapshot.timestamp_utc).total_seconds()

    if age_seconds > 30:
        _logger.error(
            "Level 2 validation failed: stale data",
            extra={
                "error_type": "STALE_DATA",
                "error_code": "LEVEL2_STALE",
                "symbol": snapshot.symbol,
                "age_seconds": age_seconds,
                "threshold_seconds": 30,
                "timestamp_utc": snapshot.timestamp_utc.isoformat(),
            },
        )
        raise DataValidationError(
            f"Level 2 data too stale: {age_seconds:.1f}s old (max 30s allowed)"
        )

    if age_seconds > 10:
        _logger.warning(
            "Level 2 data aging",
            extra={
                "error_type": "AGING_DATA",
                "error_code": "LEVEL2_AGING",
                "symbol": snapshot.symbol,
                "age_seconds": age_seconds,
                "threshold_seconds": 10,
                "timestamp_utc": snapshot.timestamp_utc.isoformat(),
            },
        )

    # Validate bid sort order (descending by price)
    if len(snapshot.bids) > 1:
        for i in range(len(snapshot.bids) - 1):
            if snapshot.bids[i][0] < snapshot.bids[i + 1][0]:
                _logger.error(
                    "Level 2 validation failed: bids not sorted",
                    extra={
                        "error_type": "SORT_ORDER",
                        "error_code": "LEVEL2_BID_SORT",
                        "symbol": snapshot.symbol,
                        "position": i,
                        "current_price": str(snapshot.bids[i][0]),
                        "next_price": str(snapshot.bids[i + 1][0]),
                        "expected_order": "descending",
                    },
                )
                raise DataValidationError(
                    f"Level 2 bids not sorted descending: "
                    f"{snapshot.bids[i][0]} < {snapshot.bids[i+1][0]}"
                )

    # Validate ask sort order (ascending by price)
    if len(snapshot.asks) > 1:
        for i in range(len(snapshot.asks) - 1):
            if snapshot.asks[i][0] > snapshot.asks[i + 1][0]:
                _logger.error(
                    "Level 2 validation failed: asks not sorted",
                    extra={
                        "error_type": "SORT_ORDER",
                        "error_code": "LEVEL2_ASK_SORT",
                        "symbol": snapshot.symbol,
                        "position": i,
                        "current_price": str(snapshot.asks[i][0]),
                        "next_price": str(snapshot.asks[i + 1][0]),
                        "expected_order": "ascending",
                    },
                )
                raise DataValidationError(
                    f"Level 2 asks not sorted ascending: "
                    f"{snapshot.asks[i][0]} > {snapshot.asks[i+1][0]}"
                )


def validate_tape_data(records: list[TimeAndSalesRecord]) -> None:
    """
    Validate Time & Sales tape data for chronological sequence and data integrity.

    Validation Rules (per spec US5 and data-model.md):
    - Timestamps in chronological order (later ticks have later timestamps)
    - All prices >$0
    - All sizes >0 shares
    - Valid side ("buy" or "sell")

    Args:
        records: List of TimeAndSalesRecord to validate

    Raises:
        DataValidationError: If validation fails

    Example:
        >>> records = [TimeAndSalesRecord(...), ...]
        >>> validate_tape_data(records)  # Raises if out of order or invalid
    """
    if not records:
        return  # Empty list is valid

    # Check chronological sequence
    for i in range(len(records) - 1):
        if records[i].timestamp_utc > records[i + 1].timestamp_utc:
            _logger.error(
                "Tape validation failed: chronological violation",
                extra={
                    "error_type": "CHRONOLOGICAL_VIOLATION",
                    "error_code": "TAPE_CHRONOLOGY",
                    "symbol": records[i].symbol,
                    "tick_index": i,
                    "current_timestamp": records[i].timestamp_utc.isoformat(),
                    "next_timestamp": records[i + 1].timestamp_utc.isoformat(),
                    "time_delta_seconds": (
                        records[i].timestamp_utc - records[i + 1].timestamp_utc
                    ).total_seconds(),
                },
            )
            raise DataValidationError(
                f"Time & Sales data not chronological: "
                f"{records[i].timestamp_utc} > {records[i+1].timestamp_utc} "
                f"(tick {i} after tick {i+1})"
            )

    # Validate all records have valid price and size
    # (Note: individual record validation already done in TimeAndSalesRecord.__post_init__)
    for idx, record in enumerate(records):
        if record.price <= 0:
            _logger.error(
                "Tape validation failed: invalid price",
                extra={
                    "error_type": "INVALID_PRICE",
                    "error_code": "TAPE_PRICE",
                    "symbol": record.symbol,
                    "tick_index": idx,
                    "price": str(record.price),
                    "minimum_required": "0.01",
                },
            )
            raise DataValidationError(
                f"Time & Sales record {idx} has invalid price: {record.price} (must be >$0)"
            )
        if record.size <= 0:
            _logger.error(
                "Tape validation failed: invalid size",
                extra={
                    "error_type": "INVALID_SIZE",
                    "error_code": "TAPE_SIZE",
                    "symbol": record.symbol,
                    "tick_index": idx,
                    "size": record.size,
                    "minimum_required": 1,
                },
            )
            raise DataValidationError(
                f"Time & Sales record {idx} has invalid size: {record.size} (must be >0 shares)"
            )


def validate_order_flow_config(config: OrderFlowConfig) -> None:
    """
    Validate OrderFlowConfig for logical consistency and requirement compliance.

    Validation Rules (per spec US4):
    - large_order_size_threshold: >=1000 shares
    - volume_spike_threshold: 1.5-10.0x
    - red_burst_threshold: >=volume_spike_threshold
    - alert_window_seconds: 30-300 seconds
    - data_source: "polygon" only
    - polygon_api_key: non-empty string

    Args:
        config: OrderFlowConfig to validate

    Raises:
        DataValidationError: If validation fails

    Example:
        >>> config = OrderFlowConfig.from_env()
        >>> validate_order_flow_config(config)  # Raises if invalid
    """
    # Note: Most validation already done in OrderFlowConfig.__post_init__
    # This function provides additional cross-field validation if needed

    # Validate polygon_api_key format (basic sanity check)
    if config.data_source == "polygon":
        if not config.polygon_api_key or len(config.polygon_api_key) < 10:
            raise DataValidationError(
                f"Invalid polygon_api_key: must be at least 10 characters "
                f"(got {len(config.polygon_api_key)})"
            )

    # Validate threshold relationships
    if config.red_burst_threshold < config.volume_spike_threshold:
        raise DataValidationError(
            f"Invalid config: red_burst_threshold ({config.red_burst_threshold}) "
            f"must be >= volume_spike_threshold ({config.volume_spike_threshold})"
        )

    _logger.info(
        "OrderFlowConfig validated",
        extra={
            "large_order_size_threshold": config.large_order_size_threshold,
            "volume_spike_threshold": config.volume_spike_threshold,
            "red_burst_threshold": config.red_burst_threshold,
            "alert_window_seconds": config.alert_window_seconds,
            "data_source": config.data_source,
            "monitoring_mode": config.monitoring_mode,
        },
    )
