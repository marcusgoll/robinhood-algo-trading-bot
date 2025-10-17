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

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from .. import MomentumEngine
from ..config import MomentumConfig

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/momentum", tags=["momentum"])

# In-memory storage for scan results (MVP implementation)
# TODO Phase 2: Replace with Redis or database for production
_scan_results: dict[str, dict] = {}


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
async def trigger_scan(request: ScanRequest) -> ScanResponse:
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

        # Initialize scan result in memory
        _scan_results[scan_id] = {
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
async def get_scan_status(scan_id: str) -> ScanStatusResponse:
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
    if scan_id not in _scan_results:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scan {scan_id} not found"
        )

    scan_result = _scan_results[scan_id]

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

    Updates _scan_results with status and results.

    Args:
        scan_id: Unique scan identifier
        symbols: List of symbols to scan
        scan_types: List of scan types to execute
    """
    try:
        # Update status to running
        _scan_results[scan_id]["status"] = "running"

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
        _scan_results[scan_id]["status"] = "completed"
        _scan_results[scan_id]["completed_at"] = datetime.now(UTC).isoformat()
        _scan_results[scan_id]["signal_count"] = len(signal_dicts)
        _scan_results[scan_id]["signals"] = signal_dicts

        logger.info(
            f"Scan {scan_id} completed: {len(signal_dicts)} signals detected"
        )

    except Exception as e:
        # Update scan result with error
        _scan_results[scan_id]["status"] = "failed"
        _scan_results[scan_id]["completed_at"] = datetime.now(UTC).isoformat()
        _scan_results[scan_id]["error"] = str(e)

        logger.error(f"Scan {scan_id} failed: {e}")
