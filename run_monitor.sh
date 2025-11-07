#!/bin/bash
# Wrapper script to run bot monitor with environment variables

# Read .env file and export Telegram variables (handling Windows line endings and comments)
export TELEGRAM_ENABLED=$(grep "^TELEGRAM_ENABLED" .env | cut -d'=' -f2 | cut -d'#' -f1 | tr -d '\r' | xargs)
export TELEGRAM_BOT_TOKEN=$(grep "^TELEGRAM_BOT_TOKEN" .env | cut -d'=' -f2 | cut -d'#' -f1 | tr -d '\r' | xargs)
export TELEGRAM_CHAT_ID=$(grep "^TELEGRAM_CHAT_ID" .env | cut -d'=' -f2 | cut -d'#' -f1 | tr -d '\r' | xargs)
export TELEGRAM_INCLUDE_EMOJIS=$(grep "^TELEGRAM_INCLUDE_EMOJIS" .env | cut -d'=' -f2 | cut -d'#' -f1 | tr -d '\r' | xargs)

# Run monitor
python3 monitor_bot_status.py "$@"
