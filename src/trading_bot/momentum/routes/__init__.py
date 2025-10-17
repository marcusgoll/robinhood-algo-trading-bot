"""
Momentum API Routes Module

FastAPI route handlers for momentum detection endpoints:
- GET /api/v1/momentum/signals - Query historical signals with filtering
- POST /api/v1/momentum/scan - Trigger on-demand momentum scan
- GET /api/v1/momentum/scans/{scan_id} - Poll scan status and results

All routes require authentication and implement rate limiting.
Responses follow standard API conventions with pagination and error handling.
"""

from .scan import router as scan_router
from .signals import router as signals_router

__all__ = ["signals_router", "scan_router"]
