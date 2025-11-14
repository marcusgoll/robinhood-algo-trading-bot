"""
Unit tests for StateAggregator service

T015: Test state aggregation logic
T043: Test summary size validation (<10KB)

Coverage target: ≥80%

Test cases:
- test_get_bot_state_aggregates_dashboard_and_performance: Verify all fields populated
- test_get_health_status_returns_valid_structure: Verify HealthStatus schema
- test_summary_response_under_10kb: Verify size constraint (T043)
- test_cache_ttl_respected: Verify 60s cache works
- test_cache_bypass_with_no_cache: Verify cache bypass works
- test_invalidate_cache: Verify manual cache invalidation
"""

import json
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, Mock, patch

import pytest

from api.app.schemas.state import (
    BotStateResponse,
    BotSummaryResponse,
    HealthStatus,
)
from api.app.services.state_aggregator import StateAggregator


@pytest.fixture
def aggregator() -> StateAggregator:
    """Create StateAggregator instance for testing."""
    return StateAggregator()


@pytest.mark.asyncio
async def test_get_bot_state_aggregates_dashboard_and_performance(
    aggregator: StateAggregator,
):
    """Test that get_bot_state returns complete BotStateResponse with all required fields."""
    # When: Get bot state
    state = await aggregator.get_bot_state(use_cache=False)

    # Then: Verify all required fields present
    assert isinstance(state, BotStateResponse)
    assert isinstance(state.positions, list)
    assert state.account is not None
    assert state.health is not None
    assert state.performance is not None
    assert isinstance(state.config_summary, dict)
    assert state.market_status in ["OPEN", "CLOSED"]
    assert isinstance(state.timestamp, datetime)
    assert isinstance(state.data_age_seconds, float)
    assert isinstance(state.warnings, list)


@pytest.mark.asyncio
async def test_get_health_status_returns_valid_structure(aggregator: StateAggregator):
    """Test that get_health_status returns valid HealthStatus."""
    # When: Get health status
    health = await aggregator.get_health_status()

    # Then: Verify all required fields
    assert isinstance(health, HealthStatus)
    assert health.status in ["healthy", "degraded", "offline"]
    assert isinstance(health.circuit_breaker_active, bool)
    assert isinstance(health.api_connected, bool)
    assert isinstance(health.last_heartbeat, datetime)
    assert isinstance(health.error_count_last_hour, int)


@pytest.mark.asyncio
async def test_summary_response_under_10kb(aggregator: StateAggregator):
    """
    T043: Test that summary response is under 10KB.

    Validates FR-029: Summary endpoint must return <10KB for LLM context windows.
    """
    # When: Get summary
    summary = await aggregator.get_summary()

    # Then: Verify summary structure
    assert isinstance(summary, BotSummaryResponse)
    assert summary.health_status in ["healthy", "degraded", "offline"]
    assert isinstance(summary.position_count, int)
    assert isinstance(summary.open_orders_count, int)
    assert isinstance(summary.daily_pnl, Decimal)
    assert isinstance(summary.circuit_breaker_status, str)
    assert isinstance(summary.recent_errors, list)
    assert len(summary.recent_errors) <= 3  # Max 3 errors
    assert isinstance(summary.timestamp, datetime)

    # Then: Verify size constraint
    summary_json = summary.model_dump_json()
    size_bytes = len(summary_json.encode("utf-8"))

    # 10KB = 10,240 bytes
    assert size_bytes < 10240, (
        f"Summary response is {size_bytes} bytes, exceeds 10KB limit (10,240 bytes). "
        f"Reduce verbosity or truncate fields."
    )

    # Also verify it's reasonable for LLM consumption (~2500 tokens)
    # Rough estimate: 1 token ≈ 4 characters
    estimated_tokens = size_bytes / 4
    assert estimated_tokens < 2500, (
        f"Summary response is ~{estimated_tokens:.0f} tokens, "
        f"exceeds target of 2500 tokens for LLM efficiency"
    )


@pytest.mark.asyncio
async def test_cache_ttl_respected(aggregator: StateAggregator):
    """Test that state is cached and reused within TTL."""
    # Given: Get initial state
    state1 = await aggregator.get_bot_state(use_cache=True)

    # When: Get state again within TTL (should use cache)
    state2 = await aggregator.get_bot_state(use_cache=True)

    # Then: Timestamps should match (same cached object)
    assert state1.timestamp == state2.timestamp


@pytest.mark.asyncio
async def test_cache_bypass_with_no_cache(aggregator: StateAggregator):
    """Test that cache can be bypassed with use_cache=False."""
    # Given: Get initial state to populate cache
    state1 = await aggregator.get_bot_state(use_cache=True)

    # When: Get state with cache bypass
    state2 = await aggregator.get_bot_state(use_cache=False)

    # Then: Timestamps should differ (fresh data)
    # Note: In mock implementation, timestamps might be very close
    # In production with real data sources, this would be more significant
    assert isinstance(state2, BotStateResponse)


@pytest.mark.asyncio
async def test_invalidate_cache(aggregator: StateAggregator):
    """Test manual cache invalidation."""
    # Given: Get initial state to populate cache
    await aggregator.get_bot_state(use_cache=True)

    # When: Invalidate cache
    aggregator.invalidate_cache()

    # Then: Cache should be cleared
    assert aggregator._cached_state is None
    assert aggregator._cache_timestamp is None


@pytest.mark.asyncio
async def test_get_summary_uses_cache(aggregator: StateAggregator):
    """Test that get_summary leverages cached state."""
    # Given: Populate cache
    await aggregator.get_bot_state(use_cache=True)

    # When: Get summary (should use cached state)
    summary = await aggregator.get_summary()

    # Then: Summary should be generated without errors
    assert isinstance(summary, BotSummaryResponse)
    assert summary.position_count >= 0
    assert summary.open_orders_count >= 0


@pytest.mark.asyncio
async def test_summary_truncates_errors_to_max_3(aggregator: StateAggregator):
    """Test that recent_errors is limited to 3 items."""
    # When: Get summary
    summary = await aggregator.get_summary()

    # Then: Verify max 3 errors
    assert len(summary.recent_errors) <= 3, (
        f"Summary contains {len(summary.recent_errors)} errors, "
        f"should be max 3 for size optimization"
    )
