"""
Manual Telegram Notification Test Script

Tests all notification types:
- Position entry
- Position exit
- Risk alert

Usage:
    python scripts/test_telegram_notification.py

Output:
    Success/failure message with delivery time

Task: T057 - Create manual test script
"""

import asyncio
import sys
from decimal import Decimal
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.trading_bot.notifications import get_notification_service
from src.trading_bot.notifications.message_formatter import (
    PositionEntryData,
    PositionExitData,
    RiskAlertData,
)


async def test_position_entry_notification():
    """Test position entry notification."""
    print("\n1. Testing Position Entry Notification...")

    service = get_notification_service()

    if not service.is_enabled():
        print("   ❌ Telegram notifications disabled (set TELEGRAM_ENABLED=true)")
        return False

    # Create sample trade data
    entry_data = PositionEntryData(
        symbol="AAPL",
        entry_price=Decimal("150.00"),
        quantity=100,
        total_value=Decimal("15000.00"),
        stop_loss=Decimal("147.00"),
        target=Decimal("156.00"),
        execution_mode="PAPER",
        strategy_name="bull-flag-breakout",
        entry_type="breakout",
    )

    # Format and send
    message = service.formatter.format_position_entry(entry_data)

    import time
    start = time.time()

    response = await service.client.send_message(
        chat_id=service.chat_id,
        text=message,
        parse_mode=service.parse_mode
    )

    delivery_time = (time.time() - start) * 1000

    if response.success:
        print(f"   ✓ Position entry notification sent ({delivery_time:.1f}ms)")
        return True
    else:
        print(f"   ❌ Failed: {response.error_message}")
        return False


async def test_position_exit_notification():
    """Test position exit notification."""
    print("\n2. Testing Position Exit Notification...")

    service = get_notification_service()

    if not service.is_enabled():
        return False

    # Create sample exit data (profit)
    exit_data = PositionExitData(
        symbol="NVDA",
        exit_price=Decimal("500.00"),
        exit_reasoning="Take Profit",
        profit_loss=Decimal("600.00"),
        profit_loss_pct=4.0,
        hold_duration_seconds=8100,  # 2h 15m
        execution_mode="LIVE",
    )

    # Format and send
    message = service.formatter.format_position_exit(exit_data)

    import time
    start = time.time()

    response = await service.client.send_message(
        chat_id=service.chat_id,
        text=message,
        parse_mode=service.parse_mode
    )

    delivery_time = (time.time() - start) * 1000

    if response.success:
        print(f"   ✓ Position exit notification sent ({delivery_time:.1f}ms)")
        return True
    else:
        print(f"   ❌ Failed: {response.error_message}")
        return False


async def test_risk_alert_notification():
    """Test risk alert notification."""
    print("\n3. Testing Risk Alert Notification...")

    service = get_notification_service()

    if not service.is_enabled():
        return False

    # Create sample alert data
    from datetime import datetime

    alert_data = RiskAlertData(
        breach_type="max_daily_loss",
        current_value="$-450.00",
        threshold="$-300.00",
        timestamp=datetime.utcnow().isoformat() + "Z",
    )

    # Format and send
    message = service.formatter.format_risk_alert(alert_data)

    import time
    start = time.time()

    response = await service.client.send_message(
        chat_id=service.chat_id,
        text=message,
        parse_mode=service.parse_mode
    )

    delivery_time = (time.time() - start) * 1000

    if response.success:
        print(f"   ✓ Risk alert notification sent ({delivery_time:.1f}ms)")
        return True
    else:
        print(f"   ❌ Failed: {response.error_message}")
        return False


async def main():
    """Run all notification tests."""
    print("Telegram Notification Test Suite")
    print("=" * 50)

    try:
        service = get_notification_service()

        if not service.is_enabled():
            print("\n❌ Telegram notifications are disabled.")
            print("   Set TELEGRAM_ENABLED=true in .env and configure credentials.")
            print("\nRun: python -m trading_bot.notifications.validate_config")
            return 1

        print(f"\nTesting notifications to chat_id: {service.chat_id}")
        print("Check your Telegram app for test messages...")

        # Run tests
        results = []
        results.append(await test_position_entry_notification())

        # Wait 1 second between messages to avoid rate limiting
        await asyncio.sleep(1)

        results.append(await test_position_exit_notification())

        await asyncio.sleep(1)

        results.append(await test_risk_alert_notification())

        # Summary
        print("\n" + "=" * 50)
        passed = sum(results)
        total = len(results)

        if passed == total:
            print(f"✅ All tests passed ({passed}/{total})")
            print("\nTelegram notifications are working correctly!")
            return 0
        else:
            print(f"❌ Some tests failed ({passed}/{total} passed)")
            print("\nCheck error messages above for troubleshooting.")
            return 1

    except Exception as e:
        print(f"\n❌ Unexpected error: {type(e).__name__}: {str(e)}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
