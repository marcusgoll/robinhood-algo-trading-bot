"""
Momentum Logging Module

Structured JSONL logging for momentum detection events:
- Signal detection (catalyst, pre-market, pattern)
- Scan lifecycle (started, completed, failed)
- Performance metrics (execution times, API latencies)
- Error tracking with full context

MomentumLogger wraps the shared TradingLogger infrastructure with
momentum-specific event types and metadata formatting.

Logs are written to: logs/momentum/YYYY-MM-DD.jsonl (rotated daily)
"""

from .momentum_logger import MomentumLogger

__all__ = ["MomentumLogger"]
