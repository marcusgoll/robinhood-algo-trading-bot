"""
Technical Indicators Module

Provides VWAP, EMA, and MACD calculations for trade entry validation
and position management.

Constitution v1.0.0:
- §Data_Integrity: All calculations use Decimal for precision
- §Risk_Management: Conservative AND-gate entry validation
- §Audit_Everything: All indicator calculations logged

Example:
    from trading_bot.indicators import TechnicalIndicatorsService
    from trading_bot.market_data import MarketDataService

    service = TechnicalIndicatorsService(market_data_service)
    indicators = service.get_all_indicators("AAPL")
    entry_allowed = service.validate_entry("AAPL", Decimal("152.00"))
"""

__all__ = [
    # Configuration
    "IndicatorConfig",
    # Exceptions
    "InsufficientDataError",
    # Service (facade will be added in Phase 5)
]
