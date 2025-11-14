"""
Authentication middleware for API endpoints.

Provides API key-based authentication with environment variable configuration.
"""

import os
import logging
from typing import Optional
from fastapi import Request, HTTPException, status
from fastapi.security import APIKeyHeader
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# API key header scheme
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    """
    API Key authentication middleware.

    Validates API key from X-API-Key header against environment variable.
    Exempts public endpoints from authentication.
    """

    def __init__(self, app, exempt_paths: Optional[list[str]] = None):
        """
        Initialize auth middleware.

        Args:
            app: FastAPI application
            exempt_paths: List of path prefixes to exempt from auth (e.g., ["/health", "/docs"])
        """
        super().__init__(app)
        self.api_key = os.getenv("API_KEY")

        # Default exempt paths - health checks and API docs
        self.exempt_paths = exempt_paths or [
            "/api/v1/health/",
            "/docs",
            "/redoc",
            "/openapi.json",
        ]

        if not self.api_key:
            logger.warning(
                "API_KEY environment variable not set - all requests will be rejected. "
                "Set API_KEY to enable authentication."
            )

    async def dispatch(self, request: Request, call_next):
        """
        Process request and validate API key.

        Args:
            request: Incoming request
            call_next: Next middleware/route handler

        Returns:
            Response from next handler

        Raises:
            HTTPException: If authentication fails
        """
        # Check if path is exempt from authentication
        if any(request.url.path.startswith(path) for path in self.exempt_paths):
            return await call_next(request)

        # Get API key from header
        api_key = request.headers.get("X-API-Key")

        # Validate API key
        if not self.api_key:
            # No API key configured - reject all requests
            logger.error(f"Authentication failed for {request.url.path}: No API key configured")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="API authentication not configured"
            )

        if not api_key:
            logger.warning(f"Authentication failed for {request.url.path}: No API key provided")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key required",
                headers={"WWW-Authenticate": "ApiKey"},
            )

        if api_key != self.api_key:
            logger.warning(f"Authentication failed for {request.url.path}: Invalid API key")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid API key"
            )

        # Authentication successful
        logger.debug(f"Authentication successful for {request.url.path}")
        return await call_next(request)


def get_api_key(api_key: str = api_key_header) -> str:
    """
    Dependency to get and validate API key.

    Use this as a FastAPI dependency for individual routes:
        @router.get("/protected", dependencies=[Depends(get_api_key)])
        async def protected_route():
            return {"message": "Access granted"}

    Args:
        api_key: API key from X-API-Key header

    Returns:
        Validated API key

    Raises:
        HTTPException: If API key is missing or invalid
    """
    expected_api_key = os.getenv("API_KEY")

    if not expected_api_key:
        logger.error("API authentication not configured")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API authentication not configured"
        )

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    if api_key != expected_api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key"
        )

    return api_key
