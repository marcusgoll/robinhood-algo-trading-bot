"""
Telegram Command Handler Module

Interactive command handlers for the Telegram bot to enable remote control
and monitoring of the trading bot via Telegram messages.

Classes:
    TelegramCommandHandler: Main orchestrator for command routing and lifecycle
    InternalAPIClient: HTTP client for calling internal REST API

Functions:
    ResponseFormatter functions for formatting command responses with emoji and markdown

Author: Trading Bot Team
Feature: 031-telegram-command-handlers
"""

__all__ = [
    "TelegramCommandHandler",
    "InternalAPIClient",
]
