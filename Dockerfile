# LLM Trading Bot - Production Dockerfile
# Phase 6: Forward Testing - VPS Deployment
#
# Build: docker build -t trading-bot:latest .
# Run:   docker run -d --name trading-bot --restart unless-stopped \
#          -v $(pwd)/logs:/app/logs \
#          -v $(pwd)/.env:/app/.env \
#          -v $(pwd)/config.json:/app/config.json \
#          -v $(pwd)/.robinhood.pickle:/app/.robinhood.pickle \
#          trading-bot:latest

FROM python:3.11-slim

# Metadata
LABEL maintainer="trading-bot"
LABEL version="1.0.0"
LABEL description="LLM-Enhanced Trading Bot with Claude Code Integration"

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Claude Code CLI using official install script
RUN curl -fsSL https://claude.ai/install.sh | bash

# Add Claude CLI to PATH
ENV PATH="/root/.local/bin:$PATH"

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies
# Use --no-cache-dir to reduce image size
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY scripts/ ./scripts/
COPY mcp_servers/ ./mcp_servers/

# Create necessary directories
RUN mkdir -p /app/logs/orchestrator \
             /app/logs/llm \
             /app/logs/backtest \
             /app/logs/trades \
             /app/.backtest_cache

# Initialize SQLite database tables
RUN python scripts/init_sqlite_tables.py

# Set Python path
ENV PYTHONPATH=/app/src

# Disable Python stdout/stderr buffering for Docker logs
ENV PYTHONUNBUFFERED=1

# Health check - verify bot process is running by checking database exists
# Database is created on startup and updated during operations
HEALTHCHECK --interval=2m --timeout=10s --start-period=2m --retries=3 \
    CMD test -f /app/logs/trading_bot.db || exit 1

# Default to paper trading mode for safety
# Override with: docker run ... trading-bot:latest orchestrator --orchestrator-mode live
CMD ["python", "-m", "trading_bot", "orchestrator", "--orchestrator-mode", "paper"]
