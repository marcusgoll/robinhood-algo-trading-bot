"""
Rate limiting middleware for API protection.

Limits requests per API token to prevent abuse.
"""

import time
from collections import defaultdict
from typing import Callable, Dict

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


class RateLimiter(BaseHTTPMiddleware):
    """
    Rate limiting middleware.

    Limits requests per API token to prevent abuse:
    - 100 requests per minute per token
    - Returns 429 Too Many Requests when exceeded
    - Includes Retry-After header
    """

    def __init__(self, app, requests_per_minute: int = 100):
        """
        Initialize rate limiter.

        Args:
            app: FastAPI application
            requests_per_minute: Max requests allowed per minute per token
        """
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.request_counts: Dict[str, list] = defaultdict(list)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with rate limiting.

        Args:
            request: Incoming request
            call_next: Next middleware in chain

        Returns:
            Response or 429 error if rate limit exceeded
        """
        # Get API key from header
        api_key = request.headers.get("X-API-Key", "anonymous")

        # Clean old timestamps (older than 1 minute)
        current_time = time.time()
        self.request_counts[api_key] = [
            timestamp
            for timestamp in self.request_counts[api_key]
            if current_time - timestamp < 60
        ]

        # Check rate limit
        if len(self.request_counts[api_key]) >= self.requests_per_minute:
            # Calculate retry-after (time until oldest request expires)
            oldest_timestamp = self.request_counts[api_key][0]
            retry_after = int(60 - (current_time - oldest_timestamp))

            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "RATE_LIMIT_EXCEEDED",
                    "message": f"Rate limit exceeded. Max {self.requests_per_minute} requests per minute.",
                    "retry_after": retry_after,
                },
                headers={"Retry-After": str(retry_after)},
            )

        # Add current request timestamp
        self.request_counts[api_key].append(current_time)

        # Continue to next middleware/route
        response = await call_next(request)
        return response
