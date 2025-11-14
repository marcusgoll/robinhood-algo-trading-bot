#!/bin/bash
# Docker Backup Script
#
# Backs up:
# - Configuration files (.env, config.json)
# - Logs
# - LLM cache
# - Robinhood session
#
# Usage: ./scripts/docker-backup.sh [local|remote]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="$PROJECT_DIR/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="trading-bot-backup-$DATE"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[BACKUP]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[BACKUP]${NC} $1"
}

# Create backup directory
mkdir -p "$BACKUP_DIR/$BACKUP_NAME"

log_info "Starting backup: $BACKUP_NAME"

# Backup configuration
log_info "Backing up configuration..."
cp "$PROJECT_DIR/.env" "$BACKUP_DIR/$BACKUP_NAME/" 2>/dev/null || log_warn ".env not found"
cp "$PROJECT_DIR/config.json" "$BACKUP_DIR/$BACKUP_NAME/" 2>/dev/null || log_warn "config.json not found"

# Backup session
log_info "Backing up Robinhood session..."
cp "$PROJECT_DIR/.robinhood.pickle" "$BACKUP_DIR/$BACKUP_NAME/" 2>/dev/null || log_warn "Session file not found"

# Backup logs (compress)
log_info "Backing up logs..."
if [ -d "$PROJECT_DIR/logs" ]; then
    tar -czf "$BACKUP_DIR/$BACKUP_NAME/logs.tar.gz" \
        -C "$PROJECT_DIR" logs \
        2>/dev/null || log_warn "Failed to backup logs"
fi

# Backup LLM cache (if exists)
log_info "Backing up LLM cache..."
if [ -d "$PROJECT_DIR/logs/llm_cache" ]; then
    tar -czf "$BACKUP_DIR/$BACKUP_NAME/llm_cache.tar.gz" \
        -C "$PROJECT_DIR/logs" llm_cache \
        2>/dev/null || log_warn "Failed to backup LLM cache"
fi

# Create manifest
cat > "$BACKUP_DIR/$BACKUP_NAME/manifest.txt" << EOF
Trading Bot Backup
==================
Date: $(date)
Hostname: $(hostname)
Docker: $(docker --version)

Contents:
- .env (credentials)
- config.json (configuration)
- .robinhood.pickle (session)
- logs.tar.gz (all logs)
- llm_cache.tar.gz (LLM cache)
EOF

# Calculate backup size
BACKUP_SIZE=$(du -sh "$BACKUP_DIR/$BACKUP_NAME" | cut -f1)
log_info "Backup size: $BACKUP_SIZE"

# Compress entire backup
log_info "Compressing backup..."
cd "$BACKUP_DIR"
tar -czf "$BACKUP_NAME.tar.gz" "$BACKUP_NAME"
rm -rf "$BACKUP_NAME"

FINAL_SIZE=$(du -sh "$BACKUP_NAME.tar.gz" | cut -f1)
log_info "Compressed size: $FINAL_SIZE"

# Cleanup old backups (keep last 30 days)
log_info "Cleaning up old backups..."
find "$BACKUP_DIR" -name "trading-bot-backup-*.tar.gz" -mtime +30 -delete

BACKUP_COUNT=$(find "$BACKUP_DIR" -name "trading-bot-backup-*.tar.gz" | wc -l)
log_info "Total backups: $BACKUP_COUNT"

log_info "Backup complete: $BACKUP_DIR/$BACKUP_NAME.tar.gz"

# Optional: Upload to remote (S3, rsync, etc.)
if [ "$1" == "remote" ]; then
    log_info "Uploading to remote storage..."
    # Example: AWS S3
    # aws s3 cp "$BACKUP_DIR/$BACKUP_NAME.tar.gz" s3://my-bucket/backups/
    # Example: rsync
    # rsync -avz "$BACKUP_DIR/$BACKUP_NAME.tar.gz" user@backup-server:/backups/
    log_warn "Remote upload not configured. Edit this script to enable."
fi

echo ""
log_info "📦 Backup Summary:"
log_info "   Location: $BACKUP_DIR/$BACKUP_NAME.tar.gz"
log_info "   Size: $FINAL_SIZE"
log_info "   Total backups: $BACKUP_COUNT"
