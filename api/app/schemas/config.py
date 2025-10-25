"""Pydantic schemas for bot configuration management."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class BotConfigRequest(BaseModel):
    """
    Request schema for bot configuration updates.

    Attributes:
        risk_per_trade: Risk percentage per trade (0.01-0.05)
        max_position_size: Maximum position size in dollars (100-10000)
        circuit_breaker_thresholds: Circuit breaker configuration
        trading_hours: Trading hours configuration
        max_daily_trades: Maximum trades per day
    """

    risk_per_trade: float = Field(
        ..., ge=0.01, le=0.05, description="Risk percentage per trade (1-5%)"
    )
    max_position_size: int = Field(
        ..., ge=100, le=10000, description="Maximum position size in dollars"
    )
    circuit_breaker_thresholds: Dict[str, float] = Field(
        ...,
        description="Circuit breaker thresholds (e.g., daily_loss: -0.05, max_drawdown: -0.10)",
    )
    trading_hours: Optional[Dict[str, str]] = Field(
        None, description="Trading hours (start/end times)"
    )
    max_daily_trades: Optional[int] = Field(
        None, ge=1, le=100, description="Maximum trades per day"
    )

    @field_validator("circuit_breaker_thresholds")
    @classmethod
    def validate_circuit_breaker(
        cls, v: Dict[str, float]
    ) -> Dict[str, float]:
        """Validate circuit breaker thresholds are negative percentages."""
        required_keys = {"daily_loss", "max_drawdown"}
        if not required_keys.issubset(v.keys()):
            raise ValueError(
                f"Circuit breaker must include {required_keys}"
            )
        for key, value in v.items():
            if value >= 0:
                raise ValueError(
                    f"Circuit breaker threshold {key} must be negative"
                )
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "risk_per_trade": 0.02,
                    "max_position_size": 5000,
                    "circuit_breaker_thresholds": {
                        "daily_loss": -0.05,
                        "max_drawdown": -0.10,
                    },
                    "trading_hours": {"start": "09:30", "end": "16:00"},
                    "max_daily_trades": 10,
                }
            ]
        }
    }


class ValidationResult(BaseModel):
    """
    Result of configuration validation.

    Attributes:
        valid: Whether the configuration passed validation
        errors: List of validation error messages
        warnings: List of validation warnings (non-blocking)
    """

    valid: bool = Field(..., description="Validation passed")
    errors: List[str] = Field(
        default_factory=list, description="Validation errors"
    )
    warnings: List[str] = Field(
        default_factory=list, description="Validation warnings"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "valid": False,
                    "errors": [
                        "risk_per_trade exceeds maximum allowed (5%)",
                        "circuit_breaker daily_loss threshold too aggressive",
                    ],
                    "warnings": [
                        "max_daily_trades is lower than recommended (10)"
                    ],
                }
            ]
        }
    }


class ConfigDiff(BaseModel):
    """
    Difference between old and new configuration.

    Attributes:
        changes: Dict mapping field name to (old_value, new_value) tuple
        added: List of newly added fields
        removed: List of removed fields
        unchanged: Count of unchanged fields
    """

    changes: Dict[str, Dict[str, Any]] = Field(
        ..., description="Changed fields with old and new values"
    )
    added: List[str] = Field(
        default_factory=list, description="Added fields"
    )
    removed: List[str] = Field(
        default_factory=list, description="Removed fields"
    )
    unchanged: int = Field(..., description="Number of unchanged fields")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "changes": {
                        "risk_per_trade": {"old": 0.02, "new": 0.03},
                        "max_position_size": {"old": 5000, "new": 7500},
                    },
                    "added": ["max_daily_trades"],
                    "removed": [],
                    "unchanged": 2,
                }
            ]
        }
    }


class ConfigChangeResult(BaseModel):
    """
    Result of configuration change operation.

    Attributes:
        success: Whether the change was applied successfully
        message: Human-readable status message
        config_version: Version number of applied configuration
        applied_at: Timestamp of when config was applied
        rollback_available: Whether rollback is available
    """

    success: bool = Field(..., description="Change applied successfully")
    message: str = Field(..., description="Status message")
    config_version: int = Field(..., description="Configuration version")
    applied_at: datetime = Field(..., description="Application timestamp")
    rollback_available: bool = Field(
        ..., description="Rollback capability available"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "success": True,
                    "message": "Configuration applied successfully",
                    "config_version": 5,
                    "applied_at": "2025-10-24T12:00:00Z",
                    "rollback_available": True,
                }
            ]
        }
    }


class ConfigHistoryEntry(BaseModel):
    """
    Historical configuration change record.

    Attributes:
        version: Configuration version number
        timestamp: When the change was made
        changes: Config diff for this change
        applied_by: User/system that applied the change
        reason: Optional reason for the change
    """

    version: int = Field(..., description="Configuration version")
    timestamp: datetime = Field(..., description="Change timestamp")
    changes: ConfigDiff = Field(..., description="Configuration diff")
    applied_by: str = Field(..., description="User or system")
    reason: Optional[str] = Field(None, description="Change reason")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "version": 5,
                    "timestamp": "2025-10-24T12:00:00Z",
                    "changes": {
                        "changes": {
                            "risk_per_trade": {"old": 0.02, "new": 0.03}
                        },
                        "added": [],
                        "removed": [],
                        "unchanged": 4,
                    },
                    "applied_by": "api_user",
                    "reason": "Increased risk tolerance after testing",
                }
            ]
        }
    }
