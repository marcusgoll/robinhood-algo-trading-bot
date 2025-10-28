"""FastAPI application entry point for Order Execution API.

This module initializes the FastAPI application with:
- Health check endpoints
- CORS middleware
- API routers
- Error handlers
- WebSocket broadcast loop for real-time streaming
"""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timezone

from .routes import orders, state, config, metrics, workflows, commands
from .core.websocket import manager as ws_manager
from .services.state_aggregator import StateAggregator

logger = logging.getLogger(__name__)


# Background task for WebSocket broadcasting
async def broadcast_state_updates():
    """Background task that broadcasts bot state every 5 seconds."""
    aggregator = StateAggregator()
    while True:
        try:
            # Only broadcast if there are active connections
            if ws_manager.get_active_count() > 0:
                state = aggregator.get_bot_state()
                await ws_manager.broadcast({
                    "type": "state_update",
                    "state": state.model_dump(),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
                logger.debug(
                    f"Broadcasted state to {ws_manager.get_active_count()} connections"
                )
        except Exception as e:
            logger.error(f"Error broadcasting state: {e}")

        await asyncio.sleep(5)  # 5-second interval


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup/shutdown events.

    Startup:
    - Start WebSocket broadcast loop

    Shutdown:
    - Stop broadcast loop
    - Close all WebSocket connections
    """
    # Startup
    broadcast_task = asyncio.create_task(broadcast_state_updates())
    logger.info("WebSocket broadcast loop started")

    yield

    # Shutdown
    broadcast_task.cancel()
    await ws_manager.close_all()
    logger.info("WebSocket broadcast loop stopped")


app = FastAPI(
    lifespan=lifespan,
    title="Trading Bot API",
    description="LLM-friendly operations API for trading bot monitoring, state queries, and workflow execution",
    version="1.0.0",
    openapi_tags=[
        {
            "name": "state",
            "description": "Bot state queries and summary endpoints for LLM consumption",
        },
        {
            "name": "metrics",
            "description": "Real-time metrics streaming and performance data",
        },
        {
            "name": "config",
            "description": "Configuration management with validation and rollback",
        },
        {
            "name": "workflows",
            "description": "YAML-based workflow execution and tracking",
        },
        {
            "name": "commands",
            "description": "Bot control commands (pause/resume trading)",
        },
        {
            "name": "orders",
            "description": "Order execution and management endpoints",
        },
        {
            "name": "health",
            "description": "Health check endpoints for deployment monitoring",
        },
    ],
)

# Middleware configuration
# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting (100 requests/minute per token)
from .middleware.rate_limiter import RateLimiter
app.add_middleware(RateLimiter, requests_per_minute=100)

# Include routers
app.include_router(orders.router)
app.include_router(state.router)
app.include_router(config.router, prefix="/api/v1")
app.include_router(metrics.router, prefix="/api/v1")
app.include_router(workflows.router, prefix="/api/v1")
app.include_router(commands.router, prefix="/api/v1")


@app.get("/api/v1/health/healthz")
async def healthz() -> dict[str, str]:
    """
    Health check endpoint for liveness probe.

    Returns:
        dict: Status and timestamp
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/v1/health/readyz")
async def readyz() -> dict[str, str]:
    """
    Readiness check endpoint for deployment verification.

    Returns:
        dict: Status and timestamp
    """
    return {
        "status": "ready",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    """
    Global handler for ValueError exceptions.

    Args:
        request: FastAPI request object
        exc: ValueError exception

    Returns:
        JSONResponse: 400 Bad Request with error message
    """
    return JSONResponse(
        status_code=400,
        content={"error": str(exc)},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
