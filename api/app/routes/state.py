"""State API routes for bot monitoring and operations.

Provides endpoints for querying bot state, health, and summary information.
"""

from fastapi import APIRouter, Depends, Header
from typing import Annotated

from api.app.core.auth import verify_api_key
from api.app.schemas.state import BotStateResponse, BotSummaryResponse, HealthStatus
from api.app.services.state_aggregator import StateAggregator


router = APIRouter(
    prefix="/api/v1",
    tags=["state"],
    dependencies=[Depends(verify_api_key)],
)

# Dependency: State aggregator instance
def get_state_aggregator() -> StateAggregator:
    """Get StateAggregator instance (singleton pattern)."""
    # In production, this would be managed by FastAPI dependency injection
    # or application lifespan context
    return StateAggregator()


@router.get(
    "/state",
    response_model=BotStateResponse,
    summary="Get complete bot state",
    description="""
    Returns complete trading bot state including positions, orders, account status,
    health, performance metrics, and configuration summary.

    **Authentication**: Requires X-API-Key header

    **Caching**: State is cached for 60 seconds by default (configurable via BOT_STATE_CACHE_TTL)

    **Response time**: <200ms P95

    **Example**:
    ```bash
    curl -H "X-API-Key: your-api-key" http://localhost:8000/api/v1/state
    ```
    """,
)
async def get_state(
    aggregator: Annotated[StateAggregator, Depends(get_state_aggregator)],
    cache_control: str = Header(None),
) -> BotStateResponse:
    """
    Get complete bot state.

    Args:
        aggregator: StateAggregator dependency
        cache_control: Optional Cache-Control header (no-cache to bypass cache)

    Returns:
        BotStateResponse with all state data
    """
    # Check if client requested cache bypass
    use_cache = cache_control != "no-cache" if cache_control else True

    return await aggregator.get_bot_state(use_cache=use_cache)


@router.get(
    "/summary",
    response_model=BotSummaryResponse,
    summary="Get compressed bot summary",
    description="""
    Returns compressed bot state summary optimized for LLM context windows.

    **Size**: <10KB guaranteed (<2500 tokens)

    **Authentication**: Requires X-API-Key header

    **Caching**: Leverages same cache as /state endpoint

    **Use case**: Ideal for LLM status queries where full state is too verbose

    **Example**:
    ```bash
    curl -H "X-API-Key: your-api-key" http://localhost:8000/api/v1/summary
    ```
    """,
)
async def get_summary(
    aggregator: Annotated[StateAggregator, Depends(get_state_aggregator)],
) -> BotSummaryResponse:
    """
    Get compressed bot summary.

    Args:
        aggregator: StateAggregator dependency

    Returns:
        BotSummaryResponse with critical state only
    """
    return await aggregator.get_summary()


@router.get(
    "/health",
    response_model=HealthStatus,
    summary="Get bot health status",
    description="""
    Returns bot health status including circuit breaker state, API connectivity,
    and recent error count.

    **Authentication**: Requires X-API-Key header

    **Use case**: Health checks, monitoring dashboards, uptime tracking

    **Example**:
    ```bash
    curl -H "X-API-Key: your-api-key" http://localhost:8000/api/v1/health
    ```
    """,
)
async def get_health(
    aggregator: Annotated[StateAggregator, Depends(get_state_aggregator)],
) -> HealthStatus:
    """
    Get bot health status.

    Args:
        aggregator: StateAggregator dependency

    Returns:
        HealthStatus with health indicators
    """
    return await aggregator.get_health_status()


@router.get(
    "/heartbeat",
    summary="Get last heartbeat from bot logs",
    description="""
    Returns the last heartbeat log entry proving bot is alive and functioning.

    **Authentication**: Requires X-API-Key header

    **Use case**: Verify bot trading loop is running (not just container alive)

    **Example**:
    ```bash
    curl -H "X-API-Key: your-api-key" http://localhost:8000/api/v1/heartbeat
    ```
    """,
)
async def get_heartbeat():
    """
    Get last heartbeat from bot logs.

    Reads the most recent heartbeat entry from trading_bot.log to verify
    the bot's trading loop is actively running.

    Returns:
        dict: Last heartbeat data with timestamp and status
    """
    import re
    from pathlib import Path
    from datetime import datetime, timezone

    log_path = Path("/app/logs/trading_bot.log")
    if not log_path.exists():
        return {
            "error": "Log file not found",
            "status": "unknown",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # Read last 100 lines and find most recent heartbeat
    try:
        with open(log_path, 'r') as f:
            lines = f.readlines()
            heartbeat_lines = [l for l in lines if "HEARTBEAT" in l]

            if not heartbeat_lines:
                return {
                    "error": "No heartbeat found in logs",
                    "status": "no_heartbeat",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }

            # Parse last heartbeat line
            last_heartbeat = heartbeat_lines[-1]

            # Extract structured data from heartbeat log
            # Format: "💓 HEARTBEAT | Status=running | Market=OPEN | Positions=0 | ..."
            parts = {}
            for part in last_heartbeat.split(" | "):
                if "=" in part:
                    key, value = part.split("=", 1)
                    parts[key.strip()] = value.strip()

            return {
                "status": "alive",
                "log_line": last_heartbeat.strip(),
                "parsed_data": parts,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
    except Exception as e:
        return {
            "error": str(e),
            "status": "error",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


@router.get(
    "/scans",
    summary="Get recent momentum scan results",
    description="""
    Returns recent momentum scan activity from JSONL logs.

    **Authentication**: Requires X-API-Key header

    **Use case**: Verify momentum scanning is working and see detected signals

    **Query Parameters**:
    - limit: Number of recent scans to return (default: 10, max: 100)

    **Example**:
    ```bash
    curl -H "X-API-Key: your-api-key" http://localhost:8000/api/v1/scans?limit=5
    ```
    """,
)
async def get_scans(limit: int = 10):
    """
    Get recent momentum scan results.

    Reads from daily JSONL scan activity logs to show recent momentum
    detection results.

    Args:
        limit: Number of recent scans to return (default: 10, max: 100)

    Returns:
        dict: Recent scan results with signals
    """
    import json
    from pathlib import Path
    from datetime import datetime, timezone

    limit = min(limit, 100)  # Cap at 100
    log_dir = Path("/app/logs")

    if not log_dir.exists():
        return {
            "error": "Log directory not found",
            "scans": [],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # Find today's scan log
    today = datetime.now().strftime("%Y-%m-%d")
    scan_log_path = log_dir / f"scan_activity_{today}.jsonl"

    if not scan_log_path.exists():
        # Try yesterday's log as fallback
        from datetime import timedelta
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        scan_log_path = log_dir / f"scan_activity_{yesterday}.jsonl"

        if not scan_log_path.exists():
            return {
                "error": "No scan logs found for today or yesterday",
                "scans": [],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    # Read JSONL file
    try:
        scans = []
        with open(scan_log_path, 'r') as f:
            for line in f:
                if line.strip():
                    scans.append(json.loads(line))

        # Return most recent N scans
        recent_scans = scans[-limit:] if len(scans) > limit else scans

        return {
            "status": "ok",
            "scans": recent_scans,
            "total_scans_today": len(scans),
            "returned_count": len(recent_scans),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        return {
            "error": str(e),
            "scans": [],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
