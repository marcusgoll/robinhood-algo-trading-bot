#!/usr/bin/env python3
"""
Bot Health Monitor - Sends Telegram notifications on status changes

Monitors Docker container health and sends notifications when:
- Bot starts/restarts
- Bot stops
- Bot health check fails
- Bot errors detected in logs
"""
import subprocess
import time
import os
import sys
import asyncio
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from trading_bot.notifications.telegram_client import TelegramClient


class BotMonitor:
    """Monitor bot health and send status updates"""

    def __init__(self):
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.enabled = os.getenv("TELEGRAM_ENABLED", "false").lower() == "true"
        self.include_emojis = os.getenv("TELEGRAM_INCLUDE_EMOJIS", "true").lower() == "true"

        if not self.enabled or not self.bot_token or not self.chat_id:
            print("Telegram not configured, exiting...")
            sys.exit(1)

        self.telegram = TelegramClient(bot_token=self.bot_token, timeout=10.0)
        self.container_name = "trading-bot"
        self.last_status = None
        self.state_file = Path("/tmp/bot-monitor-state.txt")

        # Load last known state
        if self.state_file.exists():
            self.last_status = self.state_file.read_text().strip()

    def get_container_status(self):
        """Get Docker container status"""
        try:
            result = subprocess.run(
                ["docker", "inspect", "--format", "{{.State.Status}}|{{.State.Health.Status}}", self.container_name],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                return "stopped", "unknown"

            parts = result.stdout.strip().split("|")
            status = parts[0] if len(parts) > 0 else "unknown"
            health = parts[1] if len(parts) > 1 else "unknown"

            return status, health

        except Exception as e:
            print(f"Error checking status: {e}")
            return "unknown", "unknown"

    def get_recent_errors(self):
        """Check recent logs for errors"""
        try:
            result = subprocess.run(
                ["docker", "logs", self.container_name, "--tail", "50", "--since", "5m"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                return []

            errors = []
            for line in result.stdout.split("\n") + result.stderr.split("\n"):
                if any(keyword in line.upper() for keyword in ["ERROR", "EXCEPTION", "FAILED", "CRITICAL"]):
                    errors.append(line[:200])  # Truncate long lines

            return errors[-5:]  # Last 5 errors

        except Exception as e:
            print(f"Error checking logs: {e}")
            return []

    async def send_notification(self, message: str):
        """Send Telegram notification"""
        try:
            await self.telegram.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode="Markdown"
            )
            print(f"Sent notification: {message[:100]}...")
        except Exception as e:
            print(f"Failed to send notification: {e}")

    async def check_and_notify(self):
        """Check status and send notifications if changed"""
        status, health = self.get_container_status()
        current_status = f"{status}-{health}"

        # Determine emoji
        if self.include_emojis:
            if status == "running" and health == "healthy":
                emoji = "✅"
            elif status == "running":
                emoji = "⚠️"
            elif status == "stopped":
                emoji = "🛑"
            else:
                emoji = "❌"
        else:
            emoji = ""

        # Check if status changed
        if current_status != self.last_status:
            # Status changed - send notification
            if status == "running" and health == "healthy":
                message = f"{emoji} *Bot Started*\n\nStatus: `Running`\nHealth: `Healthy`\nTime: `{time.strftime('%Y-%m-%d %H:%M:%S')}`"

            elif status == "running" and health in ["unhealthy", "starting"]:
                message = f"{emoji} *Bot Health Issue*\n\nStatus: `Running`\nHealth: `{health.title()}`\nTime: `{time.strftime('%Y-%m-%d %H:%M:%S')}`"

                # Check for errors in logs
                errors = self.get_recent_errors()
                if errors:
                    message += f"\n\nRecent errors:\n```\n{chr(10).join(errors[:3])}\n```"

            elif status == "stopped":
                message = f"{emoji} *Bot Stopped*\n\nStatus: `Stopped`\nTime: `{time.strftime('%Y-%m-%d %H:%M:%S')}`"

                # Check for errors that might have caused the stop
                errors = self.get_recent_errors()
                if errors:
                    message += f"\n\nLast errors:\n```\n{chr(10).join(errors[:3])}\n```"

            else:
                message = f"{emoji} *Bot Status Unknown*\n\nStatus: `{status}`\nHealth: `{health}`\nTime: `{time.strftime('%Y-%m-%d %H:%M:%S')}`"

            await self.send_notification(message)

            # Update last status
            self.last_status = current_status
            self.state_file.write_text(current_status)

        # Also check for new errors even if status unchanged
        elif status == "running":
            errors = self.get_recent_errors()
            if errors:
                # Only notify if we have critical errors
                critical = [e for e in errors if any(k in e.upper() for k in ["CRITICAL", "EXCEPTION"])]
                if critical:
                    message = f"{emoji} *Bot Errors Detected*\n\nStatus: `Running`\nRecent errors:\n```\n{chr(10).join(critical[:2])}\n```"
                    await self.send_notification(message)

    async def run_once(self):
        """Run a single check"""
        await self.check_and_notify()

    async def run_loop(self, interval=60):
        """Continuously monitor with interval in seconds"""
        print(f"Starting bot monitor (interval: {interval}s)...")

        # Send startup notification
        await self.send_notification(
            f"{'📊' if self.include_emojis else ''} *Bot Monitor Started*\n\n"
            f"Monitoring: `{self.container_name}`\n"
            f"Check interval: `{interval}s`"
        )

        while True:
            await self.check_and_notify()
            await asyncio.sleep(interval)


async def main():
    """Main entry point"""
    monitor = BotMonitor()

    # Check if we should run once or continuously
    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        await monitor.run_once()
    else:
        # Continuous monitoring (default: every 60 seconds)
        interval = int(sys.argv[1]) if len(sys.argv) > 1 else 60
        await monitor.run_loop(interval)


if __name__ == "__main__":
    asyncio.run(main())
