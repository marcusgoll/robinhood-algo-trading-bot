#!/bin/bash
# Docker Deployment Script
#
# Usage: ./scripts/deploy-docker.sh [build|start|stop|restart|logs|status]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    if ! command -v docker &> /dev/null; then
        log_error "Docker not installed. Install from: https://docs.docker.com/get-docker/"
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose not installed"
        exit 1
    fi

    if [ ! -f ".env" ]; then
        log_error ".env file not found. Copy from .env.example and configure."
        exit 1
    fi

    if [ ! -f "config.json" ]; then
        log_error "config.json not found. Copy from config.example.json and configure."
        exit 1
    fi

    log_info "Prerequisites OK"
}

# Build Docker images
build() {
    log_info "Building Docker images..."
    docker-compose build --no-cache
    log_info "Build complete"
}

# Start services
start() {
    log_info "Starting services..."
    check_prerequisites
    docker-compose up -d
    log_info "Services started"
    log_info ""
    log_info "View logs: docker-compose logs -f"
    log_info "Check status: docker-compose ps"
    log_info "Stop services: docker-compose down"
}

# Stop services
stop() {
    log_info "Stopping services..."
    docker-compose down
    log_info "Services stopped"
}

# Restart services
restart() {
    log_info "Restarting services..."
    docker-compose restart
    log_info "Services restarted"
}

# View logs
logs() {
    if [ -n "$2" ]; then
        docker-compose logs -f "$2"
    else
        docker-compose logs -f
    fi
}

# Show status
status() {
    log_info "Service Status:"
    docker-compose ps
    echo ""
    log_info "Resource Usage:"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"
}

# Show help
show_help() {
    cat << EOF
Docker Deployment Script for Trading Bot

Usage: $0 <command> [options]

Commands:
  build       Build Docker images
  start       Start all services in background
  stop        Stop all services
  restart     Restart all services
  logs [svc]  View logs (optional: specify service name)
  status      Show service status and resource usage
  help        Show this help message

Examples:
  $0 build                    # Build images
  $0 start                    # Start services
  $0 logs                     # View all logs
  $0 logs trading-bot         # View bot logs only
  $0 status                   # Check status

Services:
  - trading-bot: Main trading bot (24/7)
  - api: FastAPI monitoring service
  - redis: LLM response cache

EOF
}

# Main
case "${1:-help}" in
    build)
        build
        ;;
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    logs)
        logs "$@"
        ;;
    status)
        status
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        log_error "Unknown command: $1"
        show_help
        exit 1
        ;;
esac
