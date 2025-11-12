"""
Momentum Scan API

POST /api/v1/momentum/scan - Trigger on-demand momentum scan
GET /api/v1/momentum/scans/{scan_id} - Poll scan status and results

Constitution v1.0.0:
- §Safety_First: Async background execution, no blocking
- §Risk_Management: Rate limiting, input validation
- §Security: Authentication required (TODO: add auth middleware)

Feature: momentum-detection
Task: T052 - Create FastAPI routes for POST /api/v1/momentum/scan
"""

import asyncio
import logging
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field

from .. import MomentumEngine
from ..config import MomentumConfig

# Import auth middleware
try:
    from api.app.middleware.auth import get_api_key
    HAS_AUTH = True
except ImportError:
    # Fallback if API middleware not available
    HAS_AUTH = False
    def get_api_key():
        """Dummy auth dependency for testing."""
        return None

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/momentum", tags=["momentum"])

# Storage for scan results (Redis with in-memory fallback)
from ..storage import ScanResultStorage
import os

# Initialize storage backend
# Use Redis if REDIS_URL environment variable is set, otherwise use in-memory
_storage = ScanResultStorage(
    redis_url=os.getenv("REDIS_URL"),
    ttl_seconds=int(os.getenv("SCAN_RESULT_TTL", "3600"))  # 1 hour default
)


class ScanRequest(BaseModel):
    """Request model for momentum scan."""

    symbols: list[str] = Field(
        ...,
        min_items=1,
        max_items=100,
        description="List of stock ticker symbols to scan (1-100 symbols)"
    )
    scan_types: list[str] | None = Field(
        None,
        description="Scan types to execute (catalyst, premarket, pattern). Default: all"
    )


class ScanResponse(BaseModel):
    """Response model for scan initiation."""

    scan_id: str = Field(..., description="Unique scan identifier for polling results")
    status: str = Field(..., description="Scan status (queued, running, completed, failed)")
    message: str = Field(..., description="Human-readable status message")


class ScanStatusResponse(BaseModel):
    """Response model for scan status query."""

    scan_id: str = Field(..., description="Unique scan identifier")
    status: str = Field(..., description="Scan status (queued, running, completed, failed)")
    created_at: str = Field(..., description="When scan was initiated (ISO 8601 UTC)")
    completed_at: str | None = Field(None, description="When scan completed (ISO 8601 UTC)")
    symbols: list[str] = Field(..., description="Symbols being scanned")
    signal_count: int = Field(..., description="Number of signals detected (0 if incomplete)")
    signals: list[dict] = Field(..., description="Detected signals (empty if incomplete)")
    error: str | None = Field(None, description="Error message if scan failed")


@router.post("/scan", response_model=ScanResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_scan(
    request: ScanRequest,
    api_key: str = Depends(get_api_key)
) -> ScanResponse:
    """Trigger an on-demand momentum scan for specified symbols.

    Initiates a background scan task and returns immediately with scan_id.
    Client should poll GET /api/v1/momentum/scans/{scan_id} for results.

    Args:
        request: ScanRequest with symbols and optional scan_types

    Returns:
        ScanResponse with scan_id and status

    Example:
        POST /api/v1/momentum/scan
        {
            "symbols": ["AAPL", "GOOGL", "TSLA"],
            "scan_types": ["catalyst", "premarket"]
        }

    Response:
        HTTP 202 Accepted
        {
            "scan_id": "550e8400-e29b-41d4-a716-446655440000",
            "status": "queued",
            "message": "Scan initiated for 3 symbols"
        }
    """
    try:
        # Generate unique scan ID
        scan_id = str(uuid.uuid4())

        # Validate symbols (uppercase, non-empty)
        symbols = [s.strip().upper() for s in request.symbols if s.strip()]
        if not symbols:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Symbols list cannot be empty"
            )

        # Validate scan_types
        valid_scan_types = {"catalyst", "premarket", "pattern"}
        scan_types = request.scan_types or list(valid_scan_types)

        invalid_types = [t for t in scan_types if t not in valid_scan_types]
        if invalid_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid scan_types: {invalid_types}. Valid types: {valid_scan_types}"
            )

        # Initialize scan result in storage
        scan_data = {
            "scan_id": scan_id,
            "status": "queued",
            "created_at": datetime.now(UTC).isoformat(),
            "completed_at": None,
            "symbols": symbols,
            "scan_types": scan_types,
            "signal_count": 0,
            "signals": [],
            "error": None
        }
        _storage.store_scan(scan_id, scan_data)

        # Launch background scan task
        asyncio.create_task(_execute_scan(scan_id, symbols, scan_types))

        logger.info(
            f"Scan {scan_id} initiated: {len(symbols)} symbols, "
            f"types={scan_types}"
        )

        return ScanResponse(
            scan_id=scan_id,
            status="queued",
            message=f"Scan initiated for {len(symbols)} symbols"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to initiate scan: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate scan: {str(e)}"
        ) from e


@router.get("/scans/{scan_id}", response_model=ScanStatusResponse)
async def get_scan_status(
    scan_id: str,
    api_key: str = Depends(get_api_key)
) -> ScanStatusResponse:
    """Get status and results of a momentum scan.

    Polls scan status using scan_id from POST /api/v1/momentum/scan.
    Returns current status and results (if completed).

    Args:
        scan_id: Unique scan identifier

    Returns:
        ScanStatusResponse with current status and results

    Example:
        GET /api/v1/momentum/scans/550e8400-e29b-41d4-a716-446655440000

    Response:
        {
            "scan_id": "550e8400-e29b-41d4-a716-446655440000",
            "status": "completed",
            "created_at": "2025-10-16T14:30:00Z",
            "completed_at": "2025-10-16T14:30:15Z",
            "symbols": ["AAPL", "GOOGL"],
            "signal_count": 5,
            "signals": [...]
        }
    """
    # Check if scan exists
    scan_result = _storage.get_scan(scan_id)

    if not scan_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scan {scan_id} not found"
        )

    return ScanStatusResponse(
        scan_id=scan_result["scan_id"],
        status=scan_result["status"],
        created_at=scan_result["created_at"],
        completed_at=scan_result.get("completed_at"),
        symbols=scan_result["symbols"],
        signal_count=scan_result["signal_count"],
        signals=scan_result["signals"],
        error=scan_result.get("error")
    )


async def _execute_scan(scan_id: str, symbols: list[str], scan_types: list[str]) -> None:
    """Execute momentum scan in background task.

    Updates storage with status and results.

    Args:
        scan_id: Unique scan identifier
        symbols: List of symbols to scan
        scan_types: List of scan types to execute
    """
    try:
        # Get current scan data and update status to running
        scan_data = _storage.get_scan(scan_id)
        if scan_data:
            scan_data["status"] = "running"
            _storage.store_scan(scan_id, scan_data)

        # Initialize MomentumEngine
        # TODO: Get these from dependency injection or global state
        config = MomentumConfig.from_env()
        market_data = None  # TODO: Initialize MarketDataService
        engine = MomentumEngine(config, market_data)

        # Execute scan
        signals = await engine.scan(symbols)

        # Convert signals to dict format
        signal_dicts = [
            {
                "symbol": sig.symbol,
                "signal_type": sig.signal_type.value,
                "strength": sig.strength,
                "detected_at": sig.detected_at.isoformat(),
                "details": sig.details
            }
            for sig in signals
        ]

        # Update scan result
        scan_data = _storage.get_scan(scan_id)
        if scan_data:
            scan_data["status"] = "completed"
            scan_data["completed_at"] = datetime.now(UTC).isoformat()
            scan_data["signal_count"] = len(signal_dicts)
            scan_data["signals"] = signal_dicts
            _storage.store_scan(scan_id, scan_data)

        logger.info(
            f"Scan {scan_id} completed: {len(signal_dicts)} signals detected"
        )

    except Exception as e:
        # Update scan result with error
        scan_data = _storage.get_scan(scan_id)
        if scan_data:
            scan_data["status"] = "failed"
            scan_data["completed_at"] = datetime.now(UTC).isoformat()
            scan_data["error"] = str(e)
            _storage.store_scan(scan_id, scan_data)

        logger.error(f"Scan {scan_id} failed: {e}")
