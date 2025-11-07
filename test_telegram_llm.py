#!/usr/bin/env python3
"""
Test script to trigger LLM and verify Telegram notifications.
"""
import sys
sys.path.insert(0, "/app/src")

from trading_bot.llm import ClaudeCodeManager, LLMConfig

print("=" * 60)
print("TELEGRAM LLM NOTIFICATION TEST")
print("=" * 60)

# Initialize Claude Code manager with small budget for testing
print("\nInitializing Claude Code manager...")
config = LLMConfig(
    daily_budget_usd=1.0,
    model="haiku",
    timeout_seconds=30
)
manager = ClaudeCodeManager(config)

print(f"  Model: {config.model.value}")
print(f"  Budget: ${config.daily_budget_usd}/day")
print(f"  Telegram enabled: {manager.telegram_enabled}")

# Send a simple test prompt
test_prompt = "What is 2+2? Respond with just the number."
print(f"\nSending test prompt: '{test_prompt}'")
print("  (This should trigger Telegram notifications)")

# Invoke LLM
print("\nInvoking LLM...")
result = manager.invoke(test_prompt)

print("\n" + "=" * 60)
if result.success:
    print("SUCCESS - LLM Response:")
    print("=" * 60)
    print(f"  Data: {result.data}")
    print(f"  Cost: ${result.cost_usd:.4f}")
    print(f"  Latency: {result.latency_seconds:.2f}s")
    print(f"  Model: {result.model}")
    print("\nTelegram notifications should have been sent:")
    print("  1. LLM Triggered (start)")
    print("  2. LLM Completed (success)")
else:
    print("FAILURE - LLM Error:")
    print("=" * 60)
    print(f"  Error: {result.error}")
    print("\nTelegram error notification should have been sent")

# Show daily stats
print("\n" + "=" * 60)
print("Daily LLM Stats:")
print("=" * 60)
stats = manager.get_daily_stats()
for key, value in stats.items():
    print(f"  {key}: {value}")

print("\n" + "=" * 60)
print("Test complete - Check your Telegram for notifications!")
print("=" * 60)
