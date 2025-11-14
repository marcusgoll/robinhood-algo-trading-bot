#!/bin/bash
# Trading Bot Health Monitor
# Checks bot health and restarts if necessary
# Run via cron: */5 * * * * /opt/trading-bot/deployment/health-monitor.sh

set -euo pipefail

# Configuration
BOT_DIR="/opt/trading-bot"
LOG_FILE="$BOT_DIR/logs/health-monitor.log"
API_URL="http://localhost:8000"
MAX_MEMORY_MB=2048
MAX_CPU_PERCENT=90
ALERT_EMAIL=""  # Set this for email alerts

# Logging
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

# Send alert (customize for your alerting system)
send_alert() {
    local message="$1"
    log "ALERT: $message"

    # Email alert (if configured)
    if [[ -n "$ALERT_EMAIL" ]]; then
        echo "$message" | mail -s "Trading Bot Alert" "$ALERT_EMAIL"
    fi

    # Telegram alert (if bot is configured)
    if [[ -f "$BOT_DIR/.env" ]] && grep -q "TELEGRAM_BOT_TOKEN" "$BOT_DIR/.env"; then
        source "$BOT_DIR/.env"
        if [[ -n "${TELEGRAM_BOT_TOKEN:-}" ]] && [[ -n "${TELEGRAM_CHAT_ID:-}" ]]; then
            curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
                -d "chat_id=${TELEGRAM_CHAT_ID}" \
                -d "text=🚨 Trading Bot Alert: $message" > /dev/null
        fi
    fi
}

# Check if bot process is running
check_process() {
    if pgrep -f "trading_bot" > /dev/null; then
        return 0
    else
        return 1
    fi
}

# Check API health
check_api() {
    local response
    response=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$API_URL/health" 2>/dev/null || echo "000")

    if [[ "$response" == "200" ]]; then
        return 0
    else
        log "API health check failed with status: $response"
        return 1
    fi
}

# Check resource usage
check_resources() {
    local pid
    pid=$(pgrep -f "trading_bot" | head -1)

    if [[ -z "$pid" ]]; then
        return 1
    fi

    # Check memory usage
    local mem_mb
    mem_mb=$(ps -p "$pid" -o rss= | awk '{print int($1/1024)}')

    if [[ $mem_mb -gt $MAX_MEMORY_MB ]]; then
        send_alert "High memory usage: ${mem_mb}MB (limit: ${MAX_MEMORY_MB}MB)"
        return 1
    fi

    # Check CPU usage
    local cpu_percent
    cpu_percent=$(ps -p "$pid" -o %cpu= | awk '{print int($1)}')

    if [[ $cpu_percent -gt $MAX_CPU_PERCENT ]]; then
        log "Warning: High CPU usage: ${cpu_percent}% (limit: ${MAX_CPU_PERCENT}%)"
    fi

    return 0
}

# Check log file for errors
check_errors() {
    local error_count
    error_count=$(tail -100 "$BOT_DIR/logs/trading_bot.log" 2>/dev/null | grep -c "ERROR" || echo 0)

    if [[ $error_count -gt 10 ]]; then
        send_alert "High error rate detected: $error_count errors in last 100 log lines"
    fi
}

# Check trading state
check_trading_state() {
    cd "$BOT_DIR"

    # Use CLI to check bot status
    local status
    status=$(python cli.py bot status 2>&1 || echo "FAILED")

    if echo "$status" | grep -q "not running"; then
        return 1
    fi

    return 0
}

# Check disk space
check_disk_space() {
    local disk_usage
    disk_usage=$(df -h "$BOT_DIR" | awk 'NR==2 {print $5}' | sed 's/%//')

    if [[ $disk_usage -gt 90 ]]; then
        send_alert "Low disk space: ${disk_usage}% used"
    fi
}

# Restart bot
restart_bot() {
    log "Restarting trading bot..."

    if systemctl is-active --quiet trading-bot; then
        sudo systemctl restart trading-bot
        sleep 5

        if systemctl is-active --quiet trading-bot; then
            log "Bot restarted successfully"
            send_alert "Trading bot was automatically restarted"
        else
            send_alert "CRITICAL: Failed to restart trading bot"
        fi
    else
        send_alert "CRITICAL: Bot service is not enabled"
    fi
}

# Main health check
main() {
    log "Starting health check..."

    local needs_restart=false

    # Check if process is running
    if ! check_process; then
        log "Bot process not found"
        needs_restart=true
    fi

    # Check API health
    if ! check_api; then
        log "API health check failed"
        needs_restart=true
    fi

    # Check resources
    if ! check_resources; then
        log "Resource check failed"
        needs_restart=true
    fi

    # Check for errors
    check_errors

    # Check disk space
    check_disk_space

    # Check trading state
    if ! check_trading_state; then
        log "Trading state check failed"
        needs_restart=true
    fi

    # Restart if needed
    if [[ "$needs_restart" == true ]]; then
        restart_bot
    else
        log "Health check passed"
    fi
}

# Run main function
main
