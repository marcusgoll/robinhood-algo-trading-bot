"""Semantic error data structure for LLM-friendly error representation.

This module provides a structured format for errors that includes semantic context
(cause, impact, remediation) to help LLMs understand and respond to errors.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, Optional


class ErrorSeverity(str, Enum):
    """Error severity levels for prioritization and alerting."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SemanticError:
    """Semantic error representation with LLM-friendly context.

    Attributes:
        error_code: Unique error code (e.g., "ERR_CIRCUIT_BREAKER_TRIGGERED")
        error_type: Category of error (e.g., "RetriableError", "ValidationError")
        message: Human-readable error message
        cause: Root cause explanation (why this happened)
        impact: Impact description (what this affects)
        remediation: Suggested fix or next steps
        severity: Error severity level (low, medium, high, critical)
        context: Additional context dict (e.g., position_id, symbol, threshold)
        timestamp: When the error occurred (UTC)
    """

    error_code: str
    error_type: str
    message: str
    cause: str
    impact: str
    remediation: str
    severity: ErrorSeverity = ErrorSeverity.MEDIUM
    context: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization.

        Returns:
            Dictionary representation of the semantic error
        """
        return {
            "error_code": self.error_code,
            "error_type": self.error_type,
            "message": self.message,
            "cause": self.cause,
            "impact": self.impact,
            "remediation": self.remediation,
            "severity": self.severity.value,
            "context": self.context,
            "timestamp": self.timestamp.isoformat(),
        }

    def to_jsonl(self) -> str:
        """Convert to JSONL format for logging.

        Returns:
            JSON string representation (single line)
        """
        import json
        return json.dumps(self.to_dict())
