"""FastAPI routes for backtest API endpoints."""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from ..schemas.backtest import BacktestListResponse, BacktestDetailResponse
from ..services.backtest_loader import BacktestLoader

router = APIRouter(
    prefix="/api/v1/backtests",
    tags=["backtests"],
)

# Initialize loader (shared instance)
loader = BacktestLoader()


@router.get("", response_model=BacktestListResponse)
async def list_backtests(
    strategy: Optional[str] = Query(None, description="Filter by strategy name"),
    start_date: Optional[str] = Query(None, description="Filter by start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="Filter by end date (ISO format)"),
    limit: int = Query(50, ge=1, le=100, description="Maximum results to return"),
) -> BacktestListResponse:
    """
    List all backtests with optional filtering.

    Returns summary metadata for each backtest (strategy, date range, key metrics).
    Results are sorted by completion date (newest first).
    """
    summaries = loader.list_backtests(strategy=strategy, start_date=start_date, end_date=end_date)

    # Apply pagination
    summaries = summaries[:limit]

    return BacktestListResponse(
        data=summaries,
        total=len(summaries),
    )


@router.get("/{backtest_id}", response_model=BacktestDetailResponse)
async def get_backtest_detail(backtest_id: str) -> BacktestDetailResponse:
    """
    Get full backtest details by ID.

    Returns complete backtest result including equity curve, all trades,
    and performance metrics.

    Raises:
        404: If backtest ID not found
    """
    result = loader.get_backtest(backtest_id)

    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Backtest not found: {backtest_id}",
        )

    return result
