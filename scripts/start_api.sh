#!/bin/bash

# Startup script for Trading Bot API service
# Usage: ./scripts/start_api.sh

set -e  # Exit on error

echo "Starting Trading Bot API..."

# Load environment variables
if [ -f .env ]; then
    echo "Loading environment variables from .env"
    export $(grep -v '^#' .env | xargs)
else
    echo "Warning: .env file not found. Using default values."
fi

# Set defaults
export BOT_API_PORT=${BOT_API_PORT:-8000}
export BOT_API_HOST=${BOT_API_HOST:-0.0.0.0}

# Validate required environment variables
if [ -z "$BOT_API_AUTH_TOKEN" ]; then
    echo "Error: BOT_API_AUTH_TOKEN not set. Please set it in .env file."
    exit 1
fi

echo "API Configuration:"
echo "  Host: $BOT_API_HOST"
echo "  Port: $BOT_API_PORT"
echo "  Auth: Configured"

# Start API server with uvicorn
echo "Starting uvicorn server..."
uvicorn api.app.main:app \
    --host "$BOT_API_HOST" \
    --port "$BOT_API_PORT" \
    --log-level info \
    --access-log \
    --reload
