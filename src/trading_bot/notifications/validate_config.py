"""
Telegram Configuration Validator

CLI tool to validate Telegram credentials and test Bot API connection.

Usage:
    python -m trading_bot.notifications.validate_config

Output:
    Exit code 0 if valid, 1 if invalid (with error message)

Task: T056 [GREEN] - Create validate_config.py CLI tool
"""

import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.trading_bot.notifications.telegram_client import TelegramClient


async def validate_telegram_config() -> int:
    """
    Validate Telegram configuration and test Bot API connection.

    Returns:
        0 if valid, 1 if invalid
    """
    # Load environment variables
    load_dotenv()

    print("Telegram Configuration Validator")
    print("=" * 50)

    # Check TELEGRAM_ENABLED
    enabled = os.getenv("TELEGRAM_ENABLED", "false").lower() == "true"
    print(f"\n1. TELEGRAM_ENABLED: {enabled}")

    if not enabled:
        print("\n[ERROR] Telegram notifications are disabled.")
        print("   Set TELEGRAM_ENABLED=true in .env to enable.")
        return 1

    # Check TELEGRAM_BOT_TOKEN
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    print(f"\n2. TELEGRAM_BOT_TOKEN: {'[OK]' if bot_token else '[MISSING]'}")

    if not bot_token:
        print("\n[ERROR] TELEGRAM_BOT_TOKEN is missing.")
        print("   Get bot token from @BotFather on Telegram:")
        print("   1. Open Telegram and search for @BotFather")
        print("   2. Send /newbot and follow instructions")
        print("   3. Copy the bot token to .env")
        return 1

    # Check TELEGRAM_CHAT_ID
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    print(f"\n3. TELEGRAM_CHAT_ID: {'[OK]' if chat_id else '[MISSING]'}")

    if not chat_id:
        print("\n[ERROR] TELEGRAM_CHAT_ID is missing.")
        print("   Get your chat ID:")
        print("   1. Open Telegram and search for @userinfobot")
        print("   2. Send /start")
        print("   3. Copy your chat ID to .env")
        return 1

    # Test Bot API connection
    print("\n4. Testing Telegram Bot API connection...")

    try:
        client = TelegramClient(bot_token=bot_token, timeout=10.0)

        # Validate credentials
        response = await client.validate_credentials()

        if not response.success:
            print(f"\n[ERROR] Bot API validation failed: {response.error_message}")
            print("\nTroubleshooting:")
            print("   - Verify bot token is correct")
            print("   - Check internet connection")
            print("   - Ensure bot is not blocked by firewall")
            return 1

        print("   [OK] Bot API connection successful")

        # Send test message
        print("\n5. Sending test message...")

        test_message = "[PASS] Telegram notifications configured successfully\n\nYour trading bot is ready to send notifications."

        response = await client.send_message(
            chat_id=chat_id,
            text=test_message,
            parse_mode="Markdown"
        )

        if not response.success:
            print(f"\n[ERROR] Test message failed: {response.error_message}")
            print("\nTroubleshooting:")
            print("   - Verify chat ID is correct")
            print("   - Ensure you've started a chat with the bot")
            print("   - Open Telegram, search for your bot, and send /start")
            return 1

        print(f"   [OK] Test message sent successfully (message_id={response.message_id})")
        print(f"   Delivery time: {response.delivery_time_ms:.1f}ms")

        # Success summary
        print("\n" + "=" * 50)
        print("[SUCCESS] All checks passed!")
        print("\nTelegram notifications are configured and working.")
        print("Check your Telegram app for the test message.")
        print("\nNext steps:")
        print("   1. Run your trading bot")
        print("   2. Execute a trade (position entry/exit)")
        print("   3. Verify notifications arrive in Telegram")

        return 0

    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {type(e).__name__}: {str(e)}")
        print("\nPlease check your configuration and try again.")
        return 1


def main():
    """Main entry point for CLI."""
    exit_code = asyncio.run(validate_telegram_config())
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
