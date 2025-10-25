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
