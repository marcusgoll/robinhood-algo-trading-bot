#!/bin/bash
#
# Trading Bot VPS Deployment Script
# Deploys the bot to Hetzner VPS via SSH and Docker Compose
#
# Usage:
#   ./deploy-to-vps.sh         # Deploy to VPS
#   ./deploy-to-vps.sh --help  # Show help

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
VPS_HOST="hetzner"
DEPLOY_DIR="/opt/trading-bot"
REPO_URL="https://github.com/marcusgoll/robinhood-algo-trading-bot.git"
BRANCH="main"

# Functions
print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ️  $1${NC}"
}

print_header() {
    echo ""
    echo "=================================="
    echo "$1"
    echo "=================================="
    echo ""
}

show_help() {
    cat << EOF
Trading Bot VPS Deployment Script

Usage:
  ./deploy-to-vps.sh [OPTIONS]

Options:
  --help          Show this help message
  --check         Check VPS status only (no deployment)
  --logs          Show bot logs after deployment
  --restart       Restart existing deployment

Examples:
  ./deploy-to-vps.sh              # Full deployment
  ./deploy-to-vps.sh --check      # Check status
  ./deploy-to-vps.sh --restart    # Restart bot

Environment:
  VPS_HOST: $VPS_HOST
  DEPLOY_DIR: $DEPLOY_DIR
  REPO: $REPO_URL
  BRANCH: $BRANCH

EOF
}

check_vps() {
    print_header "Checking VPS Status"

    print_info "Testing SSH connection..."
    if ssh $VPS_HOST "echo 'SSH OK'" > /dev/null 2>&1; then
        print_success "SSH connection successful"
    else
        print_error "SSH connection failed"
        exit 1
    fi

    print_info "Checking Docker..."
    if ssh $VPS_HOST "docker --version" > /dev/null 2>&1; then
        print_success "Docker installed"
    else
        print_error "Docker not found"
        exit 1
    fi

    print_info "Checking Dokploy..."
    if ssh $VPS_HOST "docker ps | grep dokploy" > /dev/null 2>&1; then
        print_success "Dokploy running on port 3000"
    else
        print_error "Dokploy not running"
        exit 1
    fi
}

deploy_bot() {
    print_header "Deploying Trading Bot to VPS"

    # Step 1: Check prerequisites
    check_vps

    # Step 2: Create deployment directory
    print_info "Creating deployment directory..."
    ssh $VPS_HOST "sudo mkdir -p $DEPLOY_DIR && sudo chown \$USER:$USER $DEPLOY_DIR"
    print_success "Directory created: $DEPLOY_DIR"

    # Step 3: Clone or update repository
    print_info "Syncing code from GitHub..."
    ssh $VPS_HOST "
        if [ -d $DEPLOY_DIR/.git ]; then
            cd $DEPLOY_DIR && git fetch origin && git reset --hard origin/$BRANCH
            echo 'Repository updated'
        else
            git clone $REPO_URL $DEPLOY_DIR
            cd $DEPLOY_DIR && git checkout $BRANCH
            echo 'Repository cloned'
        fi
    "
    print_success "Code synced"

    # Step 4: Copy environment file
    print_info "Checking for .env file..."
    if [ -f ".env" ]; then
        print_info "Copying .env to VPS..."
        scp .env $VPS_HOST:$DEPLOY_DIR/.env
        print_success ".env copied"
    else
        print_error ".env file not found locally"
        print_info "You'll need to create .env on VPS manually"
        echo "Run: ssh $VPS_HOST 'nano $DEPLOY_DIR/.env'"
        exit 1
    fi

    # Step 5: Copy config.json
    if [ -f "config.json" ]; then
        print_info "Copying config.json to VPS..."
        scp config.json $VPS_HOST:$DEPLOY_DIR/config.json
        print_success "config.json copied"
    else
        print_error "config.json not found"
        exit 1
    fi

    # Step 6: Stop existing containers (if any)
    print_info "Stopping existing containers..."
    ssh $VPS_HOST "
        cd $DEPLOY_DIR
        docker compose down 2>/dev/null || true
    "
    print_success "Existing containers stopped"

    # Step 7: Build and start containers
    print_info "Building and starting containers..."
    ssh $VPS_HOST "
        cd $DEPLOY_DIR
        docker compose up -d --build
    "
    print_success "Containers started"

    # Step 8: Wait for startup
    print_info "Waiting for bot to start (10 seconds)..."
    sleep 10

    # Step 9: Verify deployment
    print_header "Verifying Deployment"

    print_info "Checking running containers..."
    ssh $VPS_HOST "docker ps | grep trading-bot"

    print_info "Checking bot logs..."
    ssh $VPS_HOST "docker logs trading-bot --tail 20"

    # Step 10: Health checks
    print_info "Testing API health..."
    if ssh $VPS_HOST "curl -sf http://localhost:8000/api/v1/health/healthz" > /dev/null 2>&1; then
        print_success "API is healthy"
    else
        print_error "API health check failed"
    fi

    print_success "Deployment complete!"

    echo ""
    print_info "Access points:"
    echo "  - Dokploy UI: http://$(ssh $VPS_HOST 'curl -s ifconfig.me'):3000"
    echo "  - Bot API: http://$(ssh $VPS_HOST 'curl -s ifconfig.me'):8000"
    echo "  - Dashboard: http://$(ssh $VPS_HOST 'curl -s ifconfig.me'):3002"
    echo ""
    print_info "Useful commands:"
    echo "  - View logs: ssh $VPS_HOST 'docker logs trading-bot -f'"
    echo "  - Check status: ssh $VPS_HOST 'docker ps'"
    echo "  - Restart: ssh $VPS_HOST 'cd $DEPLOY_DIR && docker compose restart'"
    echo "  - Stop: ssh $VPS_HOST 'cd $DEPLOY_DIR && docker compose down'"
}

show_logs() {
    print_header "Bot Logs (Live)"
    ssh $VPS_HOST "docker logs trading-bot -f"
}

restart_bot() {
    print_header "Restarting Bot"

    print_info "Restarting containers..."
    ssh $VPS_HOST "cd $DEPLOY_DIR && docker compose restart"
    print_success "Containers restarted"

    print_info "Checking status..."
    ssh $VPS_HOST "docker ps | grep trading-bot"
}

# Main script
case "${1:-}" in
    --help|-h)
        show_help
        ;;
    --check)
        check_vps
        ;;
    --logs)
        show_logs
        ;;
    --restart)
        restart_bot
        ;;
    "")
        deploy_bot
        ;;
    *)
        print_error "Unknown option: $1"
        show_help
        exit 1
        ;;
esac
