#!/usr/bin/env python3
"""
Simple test to verify Telegram notifications work in ClaudeCodeManager.
"""
import sys
import time
sys.path.insert(0, "/app/src")

from trading_bot.llm import ClaudeCodeManager, LLMConfig

print("=" * 60)
print("TELEGRAM NOTIFICATION TEST")
print("=" * 60)

# Initialize Claude Code manager
print("\nInitializing ClaudeCodeManager...")
config = LLMConfig(model="haiku")
manager = ClaudeCodeManager(config)

print(f"Telegram enabled: {manager.telegram_enabled}")

if not manager.telegram_enabled:
    print("\n ERROR: Telegram is not enabled!")
    print("Check that TELEGRAM_ENABLED=true in .env")
    sys.exit(1)

# Send test notification directly
print("\nSending test Telegram notification...")
manager._send_telegram_notification(
    " *Test Notification*\n"
    "This is a test from ClaudeCodeManager\n"
    "Time: " + time.strftime("%Y-%m-%d %H:%M:%S")
)

print("\nWaiting 2 seconds for async delivery...")
time.sleep(2)

print("\n" + "=" * 60)
print("Test complete - Check your Telegram for the notification!")
print("=" * 60)
