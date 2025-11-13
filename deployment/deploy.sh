#!/bin/bash
# Trading Bot Deployment Script
# Deploys the bot to a VPS for 24/7 operation

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
DEPLOY_USER="tradingbot"
DEPLOY_DIR="/opt/trading-bot"
SERVICE_NAME="trading-bot"
PYTHON_VERSION="3.11"

# Logging
log_info() {
    echo -e "${GREEN}[INFO]${NC} $*"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*"
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

# Create deployment user
create_user() {
    log_info "Creating deployment user..."

    if id "$DEPLOY_USER" &>/dev/null; then
        log_info "User $DEPLOY_USER already exists"
    else
        useradd -r -m -d "$DEPLOY_DIR" -s /bin/bash "$DEPLOY_USER"
        log_info "Created user: $DEPLOY_USER"
    fi
}

# Install system dependencies
install_dependencies() {
    log_info "Installing system dependencies..."

    apt-get update -qq
    apt-get install -y \
        python3 \
        python3-pip \
        python3-venv \
        git \
        curl \
        logrotate \
        postgresql-client \
        build-essential \
        libssl-dev \
        libffi-dev \
        python3-dev

    log_info "System dependencies installed"
}

# Setup Python virtual environment
setup_venv() {
    log_info "Setting up Python virtual environment..."

    cd "$DEPLOY_DIR"

    if [[ ! -d "venv" ]]; then
        sudo -u "$DEPLOY_USER" python3 -m venv venv
        log_info "Virtual environment created"
    fi

    sudo -u "$DEPLOY_USER" venv/bin/pip install --upgrade pip setuptools wheel
    log_info "Pip upgraded"
}

# Install Python dependencies
install_python_deps() {
    log_info "Installing Python dependencies..."

    cd "$DEPLOY_DIR"
    sudo -u "$DEPLOY_USER" venv/bin/pip install -r requirements.txt
    log_info "Python dependencies installed"
}

# Setup directories
setup_directories() {
    log_info "Setting up directories..."

    local dirs=("logs" "data" "logs/trades" "backups")

    for dir in "${dirs[@]}"; do
        mkdir -p "$DEPLOY_DIR/$dir"
        chown "$DEPLOY_USER:$DEPLOY_USER" "$DEPLOY_DIR/$dir"
    done

    log_info "Directories created"
}

# Setup log rotation
setup_logrotate() {
    log_info "Setting up log rotation..."

    cat > /etc/logrotate.d/trading-bot <<'EOF'
/opt/trading-bot/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 tradingbot tradingbot
    sharedscripts
    postrotate
        systemctl reload trading-bot > /dev/null 2>&1 || true
    endscript
}

/opt/trading-bot/logs/trades/*.jsonl {
    daily
    rotate 90
    compress
    delaycompress
    notifempty
    create 0640 tradingbot tradingbot
}
EOF

    log_info "Log rotation configured"
}

# Install systemd service
install_service() {
    log_info "Installing systemd service..."

    cp "$DEPLOY_DIR/deployment/trading-bot.service" /etc/systemd/system/
    systemctl daemon-reload
    systemctl enable "$SERVICE_NAME"

    log_info "Service installed and enabled"
}

# Setup health monitoring
setup_monitoring() {
    log_info "Setting up health monitoring..."

    # Make health monitor executable
    chmod +x "$DEPLOY_DIR/deployment/health-monitor.sh"

    # Add cron job for health monitoring (every 5 minutes)
    local cron_entry="*/5 * * * * $DEPLOY_DIR/deployment/health-monitor.sh"

    (crontab -u "$DEPLOY_USER" -l 2>/dev/null | grep -v "health-monitor.sh"; echo "$cron_entry") | \
        crontab -u "$DEPLOY_USER" -

    log_info "Health monitoring configured"
}

# Setup backup
setup_backup() {
    log_info "Setting up automated backups..."

    # Create backup script
    cat > "$DEPLOY_DIR/deployment/backup.sh" <<'EOF'
#!/bin/bash
BACKUP_DIR="/opt/trading-bot/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/backup_$DATE.tar.gz"

cd /opt/trading-bot
tar -czf "$BACKUP_FILE" \
    --exclude='venv' \
    --exclude='*.pyc' \
    --exclude='__pycache__' \
    data/ logs/ config.json .env

# Keep only last 7 days of backups
find "$BACKUP_DIR" -name "backup_*.tar.gz" -mtime +7 -delete

echo "Backup completed: $BACKUP_FILE"
EOF

    chmod +x "$DEPLOY_DIR/deployment/backup.sh"
    chown "$DEPLOY_USER:$DEPLOY_USER" "$DEPLOY_DIR/deployment/backup.sh"

    # Add daily backup cron job (2 AM)
    local cron_entry="0 2 * * * $DEPLOY_DIR/deployment/backup.sh"

    (crontab -u "$DEPLOY_USER" -l 2>/dev/null | grep -v "backup.sh"; echo "$cron_entry") | \
        crontab -u "$DEPLOY_USER" -

    log_info "Automated backups configured"
}

# Setup firewall
setup_firewall() {
    log_info "Configuring firewall..."

    if command -v ufw &> /dev/null; then
        # Allow SSH
        ufw allow 22/tcp

        # Allow API (if needed externally)
        # ufw allow 8000/tcp

        # Enable firewall
        ufw --force enable

        log_info "Firewall configured"
    else
        log_warn "UFW not installed, skipping firewall setup"
    fi
}

# Validate configuration
validate_config() {
    log_info "Validating configuration..."

    cd "$DEPLOY_DIR"

    if [[ ! -f ".env" ]]; then
        log_error ".env file not found. Please create it with your credentials."
        return 1
    fi

    if [[ ! -f "config.json" ]]; then
        log_error "config.json not found. Please create your configuration."
        return 1
    fi

    # Test imports
    if ! sudo -u "$DEPLOY_USER" venv/bin/python -c "import trading_bot" 2>/dev/null; then
        log_error "Failed to import trading_bot module"
        return 1
    fi

    log_info "Configuration validated"
    return 0
}

# Start the bot
start_bot() {
    log_info "Starting trading bot..."

    systemctl start "$SERVICE_NAME"
    sleep 3

    if systemctl is-active --quiet "$SERVICE_NAME"; then
        log_info "Trading bot started successfully"
        systemctl status "$SERVICE_NAME" --no-pager
    else
        log_error "Failed to start trading bot"
        journalctl -u "$SERVICE_NAME" -n 50 --no-pager
        return 1
    fi
}

# Main deployment function
main() {
    log_info "Starting deployment..."

    check_root
    create_user
    install_dependencies
    setup_directories
    setup_venv
    install_python_deps
    setup_logrotate
    install_service
    setup_monitoring
    setup_backup
    setup_firewall

    log_info "Deployment complete!"
    echo ""
    log_info "Next steps:"
    echo "  1. Copy your .env file to $DEPLOY_DIR/.env"
    echo "  2. Copy your config.json to $DEPLOY_DIR/config.json"
    echo "  3. Validate: sudo -u $DEPLOY_USER python cli.py config validate"
    echo "  4. Start bot: sudo systemctl start $SERVICE_NAME"
    echo "  5. Check status: sudo systemctl status $SERVICE_NAME"
    echo "  6. View logs: sudo journalctl -u $SERVICE_NAME -f"
}

# Run deployment
main
