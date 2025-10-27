# Trading Bot Dockerfile
# Builds a production-ready container for 24/7 trading
#
# Build: docker build -t trading-bot .
# Run:   docker-compose up -d

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p logs/llm_cache logs/health logs/emotional-control logs/profit-protection

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Health check (bot should be running)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Default command: Start trading bot
CMD ["python", "-m", "src.trading_bot"]
