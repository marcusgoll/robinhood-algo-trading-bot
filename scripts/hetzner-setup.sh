#!/bin/bash
# Hetzner VPS Setup Script
#
# Automated deployment to Hetzner Cloud VPS
# Run on fresh Ubuntu 22.04 server
#
# Usage:
#   1. Create Hetzner VPS (CPX11 recommended)
#   2. SSH into server
#   3. Run: bash <(curl -s https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO/main/scripts/hetzner-setup.sh)

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[$(date +'%H:%M:%S')]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[$(date +'%H:%M:%S')]${NC} $1"
}

log_error() {
    echo -e "${RED}[$(date +'%H:%M:%S')]${NC} $1"
}

log_section() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

# Configuration
REPO_URL="https://github.com/marcusgoll/robinhood-algo-trading-bot.git"
INSTALL_DIR="/opt/trading-bot"
USER="trading"

log_section "Trading Bot - Hetzner VPS Setup"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    log_error "Please run as root (use: sudo bash setup.sh)"
    exit 1
fi

# Update system
log_section "Step 1/8: System Update"
log_info "Updating package lists..."
apt-get update -qq

log_info "Upgrading packages..."
apt-get upgrade -y -qq

# Install dependencies
log_section "Step 2/8: Installing Dependencies"
log_info "Installing Docker, Git, Python..."
apt-get install -y -qq \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    git \
    python3.11 \
    python3.11-venv \
    python3-pip

# Install Docker
log_info "Installing Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
    log_info "Docker installed"
else
    log_info "Docker already installed"
fi

# Install Docker Compose
log_info "Installing Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" \
        -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    log_info "Docker Compose installed"
else
    log_info "Docker Compose already installed"
fi

# Create trading user
log_section "Step 3/8: Creating User"
if id "$USER" &>/dev/null; then
    log_info "User $USER already exists"
else
    useradd -m -s /bin/bash "$USER"
    usermod -aG docker "$USER"
    log_info "User $USER created"
fi

# Clone repository
log_section "Step 4/8: Cloning Repository"
if [ -d "$INSTALL_DIR" ]; then
    log_warn "Directory $INSTALL_DIR exists, pulling latest changes..."
    cd "$INSTALL_DIR"
    sudo -u "$USER" git pull
else
    log_info "Cloning repository to $INSTALL_DIR..."
    sudo -u "$USER" git clone "$REPO_URL" "$INSTALL_DIR"
fi

cd "$INSTALL_DIR"

# Create directories
log_section "Step 5/8: Setting Up Directories"
mkdir -p logs/{llm_cache,health,emotional-control,profit-protection}
mkdir -p backups
chown -R "$USER:$USER" logs backups

# Configure environment
log_section "Step 6/8: Configuration"
if [ ! -f ".env" ]; then
    log_warn ".env file not found"
    log_info "Copying .env.example to .env..."
    cp .env.example .env
    chown "$USER:$USER" .env
    chmod 600 .env

    echo ""
    log_warn "⚠️  IMPORTANT: Edit .env with your credentials!"
    log_warn "    nano $INSTALL_DIR/.env"
    echo ""
fi

if [ ! -f "config.json" ]; then
    log_info "Copying config.example.json to config.json..."
    cp config.example.json config.json
    chown "$USER:$USER" config.json
fi

# Setup systemd service
log_section "Step 7/8: Setting Up Systemd Service"
cat > /etc/systemd/system/trading-bot.service << EOF
[Unit]
Description=Trading Bot Docker Compose
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$INSTALL_DIR
User=$USER
Group=$USER

ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable trading-bot.service

log_info "Systemd service created and enabled"

# Setup firewall
log_section "Step 8/8: Configuring Firewall"
if command -v ufw &> /dev/null; then
    log_info "Configuring UFW firewall..."
    ufw --force enable
    ufw allow 22/tcp  # SSH
    ufw allow 8000/tcp  # API (optional)
    log_info "Firewall configured"
else
    log_warn "UFW not installed, skipping firewall setup"
fi

# Setup cron backup
log_info "Setting up automated backups..."
(crontab -u "$USER" -l 2>/dev/null; echo "0 2 * * * cd $INSTALL_DIR && bash scripts/docker-backup.sh") | crontab -u "$USER" -

# Final summary
log_section "Setup Complete!"

cat << EOF
${GREEN}✓${NC} Trading bot installed successfully!

${BLUE}Location:${NC} $INSTALL_DIR
${BLUE}User:${NC} $USER

${YELLOW}Next Steps:${NC}

1. Configure credentials:
   ${BLUE}nano $INSTALL_DIR/.env${NC}

   Add your:
   - ROBINHOOD_USERNAME
   - ROBINHOOD_PASSWORD
   - ROBINHOOD_MFA_SECRET
   - OPENAI_API_KEY (optional, for LLM)

2. Review configuration:
   ${BLUE}nano $INSTALL_DIR/config.json${NC}

3. Build and start services:
   ${BLUE}cd $INSTALL_DIR${NC}
   ${BLUE}sudo -u $USER docker-compose build${NC}
   ${BLUE}sudo systemctl start trading-bot${NC}

4. View logs:
   ${BLUE}sudo -u $USER docker-compose logs -f${NC}

5. Check status:
   ${BLUE}systemctl status trading-bot${NC}
   ${BLUE}sudo -u $USER docker-compose ps${NC}

${YELLOW}Important:${NC}
- Bot runs 24/7 automatically
- Restarts on reboot (systemd)
- Logs in: $INSTALL_DIR/logs/
- Backups daily at 2 AM

${GREEN}Documentation:${NC}
- README.md: Full feature docs
- docs/DEPLOYMENT.md: Deployment guide
- docs/OPERATIONS.md: Daily operations

${GREEN}Support:${NC}
https://github.com/marcusgoll/robinhood-algo-trading-bot/issues

EOF
