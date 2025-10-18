"""Authentication middleware for JWT token validation."""

from __future__ import annotations

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
