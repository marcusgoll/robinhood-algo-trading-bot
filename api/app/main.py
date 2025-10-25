"""FastAPI application entry point for Order Execution API.

This module initializes the FastAPI application with:
- Health check endpoints
- CORS middleware
- API routers
- Error handlers
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timezone

from .routes import orders, state

app = FastAPI(
    title="Trading Bot API",
    description="REST API for order execution and bot operations monitoring",
    version="1.0.0",
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(orders.router)
app.include_router(state.router)


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
