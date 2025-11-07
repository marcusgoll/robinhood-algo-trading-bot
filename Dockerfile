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

# Install Claude Code CLI
RUN curl -fsSL https://api.claude.ai/api/v1/download/cli/linux-x64 -o /usr/local/bin/claude && \
    chmod +x /usr/local/bin/claude

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies
# Use --no-cache-dir to reduce image size
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY mcp_servers/ ./mcp_servers/
COPY .claude/ ./.claude/
COPY .spec-flow/ ./.spec-flow/

# Create necessary directories
RUN mkdir -p /app/logs/orchestrator \
             /app/logs/llm \
             /app/logs/backtest \
             /app/logs/trades \
             /app/.backtest_cache

# Set Python path
ENV PYTHONPATH=/app/src

# Health check - verify bot can start in dry-run mode
HEALTHCHECK --interval=5m --timeout=30s --start-period=30s --retries=3 \
    CMD python -m trading_bot --dry-run --json || exit 1

# Default to paper trading mode for safety
# Override with: docker run ... trading-bot:latest orchestrator --orchestrator-mode live
CMD ["python", "-m", "trading_bot", "orchestrator", "--orchestrator-mode", "paper"]
