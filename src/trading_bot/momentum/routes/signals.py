"""
Momentum Signals Query API

GET /api/v1/momentum/signals - Query historical momentum signals with filtering

Constitution v1.0.0:
- §Safety_First: Read-only endpoint, no trading actions
- §Data_Integrity: Query JSONL logs with proper filtering
- §Security: Authentication required (TODO: add auth middleware)

Feature: momentum-detection
Task: T051 - Create FastAPI routes for GET /api/v1/momentum/signals
"""

import logging
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/momentum", tags=["momentum"])


class MomentumSignalResponse(BaseModel):
    """Response model for momentum signal."""

    signal_id: str = Field(..., description="Unique signal identifier")
    symbol: str = Field(..., description="Stock ticker symbol")
    signal_type: str = Field(..., description="Type of signal (catalyst, premarket, pattern, composite)")
    strength: float = Field(..., description="Signal strength score (0-100)")
    detected_at: str = Field(..., description="When signal was detected (ISO 8601 UTC)")
    details: dict = Field(..., description="Signal-specific metadata")


class SignalsQueryResponse(BaseModel):
    """Response model for signals query endpoint."""

    signals: list[MomentumSignalResponse] = Field(..., description="List of momentum signals")
    total: int = Field(..., description="Total count before pagination")
    count: int = Field(..., description="Number of signals in this response")
    has_more: bool = Field(..., description="Whether more results exist")


@router.get("/signals", response_model=SignalsQueryResponse)
async def get_signals(
    symbols: str | None = Query(
        None,
        description="Comma-separated list of symbols to filter (e.g., 'AAPL,GOOGL')"
    ),
    signal_type: str | None = Query(
        None,
        description="Filter by signal type (catalyst, premarket, pattern, composite)"
    ),
    min_strength: float | None = Query(
        0.0,
        ge=0.0,
        le=100.0,
        description="Minimum signal strength (0-100)"
    ),
    start_time: str | None = Query(
        None,
        description="Start time filter (ISO 8601 UTC, e.g., '2025-10-16T00:00:00Z')"
    ),
    end_time: str | None = Query(
        None,
        description="End time filter (ISO 8601 UTC)"
    ),
    sort_by: str = Query(
        "strength",
        description="Sort field (strength, symbol, detected_at)"
    ),
    limit: int = Query(
        50,
        ge=1,
        le=500,
        description="Maximum number of results (default 50, max 500)"
    ),
    offset: int = Query(
        0,
        ge=0,
        description="Number of results to skip (for pagination)"
    )
) -> SignalsQueryResponse:
    """Query momentum signals with filtering, sorting, and pagination.

    Reads signals from JSONL log files and applies filters. Supports:
    - Symbol filtering (comma-separated list)
    - Signal type filtering (catalyst, premarket, pattern, composite)
    - Strength threshold filtering
    - Time range filtering (start_time to end_time)
    - Sorting (strength, symbol, detected_at)
    - Pagination (limit, offset)

    Returns:
        SignalsQueryResponse with filtered signals and pagination metadata

    Example:
        GET /api/v1/momentum/signals?symbols=AAPL,MSFT&min_strength=50&limit=10
    """
    try:
        # Parse comma-separated symbols
        symbol_list = []
        if symbols:
            symbol_list = [s.strip().upper() for s in symbols.split(",")]

        # Parse time range filters
        start_dt = None
        end_dt = None
        if start_time:
            try:
                start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            except ValueError:
                logger.warning(f"Invalid start_time format: {start_time}")

        if end_time:
            try:
                end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
            except ValueError:
                logger.warning(f"Invalid end_time format: {end_time}")

        # Query signals from JSONL logs
        signals = await _query_signals_from_logs(
            symbol_list=symbol_list,
            signal_type=signal_type,
            min_strength=min_strength,
            start_time=start_dt,
            end_time=end_dt
        )

        # Sort signals
        signals = _sort_signals(signals, sort_by)

        # Apply pagination
        total = len(signals)
        paginated_signals = signals[offset : offset + limit]
        count = len(paginated_signals)
        has_more = (offset + count) < total

        # Build response
        response = SignalsQueryResponse(
            signals=[
                MomentumSignalResponse(
                    signal_id=sig.get("signal_id", "unknown"),
                    symbol=sig.get("symbol", ""),
                    signal_type=sig.get("signal_type", ""),
                    strength=sig.get("strength", 0.0),
                    detected_at=sig.get("detected_at", ""),
                    details=sig.get("details", {})
                )
                for sig in paginated_signals
            ],
            total=total,
            count=count,
            has_more=has_more
        )

        logger.info(
            f"Signals query: {count}/{total} results (symbols={symbol_list}, "
            f"signal_type={signal_type}, min_strength={min_strength})"
        )

        return response

    except Exception as e:
        logger.error(f"Failed to query signals: {e}")
        # Return empty result on error (graceful degradation)
        return SignalsQueryResponse(
            signals=[],
            total=0,
            count=0,
            has_more=False
        )


async def _query_signals_from_logs(
    symbol_list: list[str],
    signal_type: str | None,
    min_strength: float,
    start_time: datetime | None,
    end_time: datetime | None
) -> list[dict]:
    """Query signals from JSONL log files with filtering.

    Reads all JSONL files in logs/momentum/ directory and applies filters.

    Args:
        symbol_list: List of symbols to filter (empty = all symbols)
        signal_type: Signal type filter (None = all types)
        min_strength: Minimum strength threshold
        start_time: Start time filter (None = no start bound)
        end_time: End time filter (None = no end bound)

    Returns:
        List of signal dicts matching filters
    """
    import json

    signals = []
    log_dir = Path("logs/momentum")

    # Check if log directory exists
    if not log_dir.exists():
        logger.debug(f"Log directory does not exist: {log_dir}")
        return []

    # Read all JSONL files in logs/momentum/
    for log_file in sorted(log_dir.glob("*.jsonl")):
        try:
            with open(log_file) as f:
                for line in f:
                    try:
                        entry = json.loads(line)

                        # Only process signal_detected events
                        if entry.get("event_type") != "signal_detected":
                            continue

                        # Apply filters
                        if symbol_list and entry.get("symbol") not in symbol_list:
                            continue

                        if signal_type and entry.get("signal_type") != signal_type:
                            continue

                        if entry.get("strength", 0.0) < min_strength:
                            continue

                        # Parse detected_at timestamp
                        try:
                            detected_at = datetime.fromisoformat(
                                entry.get("detected_at", "").replace("Z", "+00:00")
                            )

                            if start_time and detected_at < start_time:
                                continue

                            if end_time and detected_at > end_time:
                                continue

                        except (ValueError, AttributeError):
                            # Skip entries with invalid timestamps
                            continue

                        # Add signal to results
                        signals.append(entry)

                    except json.JSONDecodeError:
                        # Skip malformed lines
                        continue

        except Exception as e:
            logger.warning(f"Error reading log file {log_file}: {e}")
            continue

    return signals


def _sort_signals(signals: list[dict], sort_by: str) -> list[dict]:
    """Sort signals by specified field.

    Args:
        signals: List of signal dicts
        sort_by: Sort field (strength, symbol, detected_at)

    Returns:
        Sorted list of signals
    """
    if sort_by == "strength":
        return sorted(signals, key=lambda s: s.get("strength", 0.0), reverse=True)
    elif sort_by == "symbol":
        return sorted(signals, key=lambda s: s.get("symbol", ""))
    elif sort_by == "detected_at":
        return sorted(
            signals,
            key=lambda s: s.get("detected_at", ""),
            reverse=True  # Most recent first
        )
    else:
        # Default to strength sorting
        return sorted(signals, key=lambda s: s.get("strength", 0.0), reverse=True)
