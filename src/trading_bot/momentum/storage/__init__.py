"""Storage backends for momentum scan results."""

from .redis_storage import ScanResultStorage

__all__ = ["ScanResultStorage"]
