"""
Structured Trade Logging Package

Provides structured logging for trade execution, querying, and analysis.

Constitution v1.0.0:
- Audit_Everything: All trades logged with structured data
- Safety_First: Immutable trade records prevent tampering
- Data_Driven: Queryable logs enable performance analysis
"""

# T009-T013 [GREEN]: TradeRecord implemented and tested
# T026-T029 [GREEN]: TradeQueryHelper implemented and tested
from .query_helper import TradeQueryHelper

# T018-T021 [GREEN]: StructuredTradeLogger implemented and tested
from .structured_logger import StructuredTradeLogger
from .trade_record import TradeRecord

__all__ = ['TradeRecord', 'StructuredTradeLogger', 'TradeQueryHelper']
