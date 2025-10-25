"""Authentication middleware for JWT token validation and API key verification."""

from __future__ import annotations

import os
from typing import Optional
from uuid import UUID

from fastapi import Header, HTTPException, status


async def get_current_trader_id(
    authorization: Optional[str] = Header(None),
) -> UUID:
    """
    Extract trader_id from JWT Bearer token.

    This is a simplified implementation for MVP.
    In production, this would:
    1. Validate JWT signature (RS256 with Clerk JWKs)
    2. Check token expiration
    3. Verify token claims
    4. Extract trader_id from claims

    Args:
        authorization: Authorization header with Bearer token

    Returns:
        UUID: Trader ID extracted from token

    Raises:
        HTTPException: 401 if token is missing or invalid
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format. Expected 'Bearer <token>'",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization[7:]  # Remove "Bearer " prefix

    # MVP: Simple token validation (in production, verify JWT signature)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # MVP: Extract trader_id from token (in production, decode JWT claims)
    # For testing, accept UUID format tokens
    try:
        trader_id = UUID(token)
        return trader_id
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def verify_api_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
) -> bool:
    """
    Verify API key for bot operations endpoints.

    This provides simple token-based authentication for LLM access to bot state
    and operations. The API key is stored in the BOT_API_AUTH_TOKEN environment variable.

    Args:
        x_api_key: API key from X-API-Key header

    Returns:
        bool: True if API key is valid

    Raises:
        HTTPException: 401 if API key is missing or invalid

    Examples:
        >>> # In FastAPI route
        >>> @router.get("/api/v1/state", dependencies=[Depends(verify_api_key)])
        >>> async def get_state():
        >>>     return {"status": "running"}
    """
    expected_key = os.getenv("BOT_API_AUTH_TOKEN")

    # Fail securely: if no token configured, reject all requests
    if not expected_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API authentication not configured (BOT_API_AUTH_TOKEN missing)",
        )

    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-API-Key header",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Constant-time comparison to prevent timing attacks
    if not _constant_time_compare(x_api_key, expected_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return True


def _constant_time_compare(a: str, b: str) -> bool:
    """Compare two strings in constant time to prevent timing attacks.

    Args:
        a: First string
        b: Second string

    Returns:
        bool: True if strings are equal
    """
    if len(a) != len(b):
        return False

    result = 0
    for x, y in zip(a, b):
        result |= ord(x) ^ ord(y)

    return result == 0
