"""
ConfigValidator service for bot configuration management.

Provides validation, diff generation, apply, and rollback capabilities
with audit trail logging.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..schemas.config import (
    BotConfigRequest,
    ConfigChangeResult,
    ConfigDiff,
    ConfigHistoryEntry,
    ValidationResult,
)


class ConfigValidator:
    """
    Service for validating and managing bot configuration changes.

    Provides:
    - JSON schema validation
    - Configuration diff generation
    - Safe config apply with rollback
    - Audit trail in JSONL format
    """

    def __init__(
        self,
        config_file: str = "config/bot_config.json",
        history_file: str = "config/config_history.jsonl",
        schema_file: str = "config/config.schema.json",
    ):
        """
        Initialize ConfigValidator.

        Args:
            config_file: Path to current bot configuration file
            history_file: Path to configuration history (JSONL)
            schema_file: Path to JSON schema for validation
        """
        self.config_file = Path(config_file)
        self.history_file = Path(history_file)
        self.schema_file = Path(schema_file)
        self._ensure_files_exist()

    def _ensure_files_exist(self) -> None:
        """Ensure config directory and files exist."""
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.config_file.exists():
            # Initialize with default config
            default_config = {
                "risk_per_trade": 0.02,
                "max_position_size": 5000,
                "circuit_breaker_thresholds": {
                    "daily_loss": -0.05,
                    "max_drawdown": -0.10,
                },
                "trading_hours": {"start": "09:30", "end": "16:00"},
                "max_daily_trades": 10,
            }
            self.config_file.write_text(json.dumps(default_config, indent=2))

        if not self.history_file.exists():
            self.history_file.touch()

    def get_current_config(self) -> Dict[str, Any]:
        """
        Get current active configuration.

        Returns:
            Dict containing current bot configuration
        """
        return json.loads(self.config_file.read_text())

    def validate(self, config: BotConfigRequest) -> ValidationResult:
        """
        Validate configuration against JSON schema and business rules.

        Args:
            config: Configuration request to validate

        Returns:
            ValidationResult with validation status and any errors/warnings
        """
        errors: List[str] = []
        warnings: List[str] = []

        # Pydantic already validates field constraints
        # Additional business rule validation
        try:
            # Check risk_per_trade is reasonable
            if config.risk_per_trade > 0.03:
                warnings.append(
                    f"risk_per_trade {config.risk_per_trade} is higher than recommended (3%)"
                )

            # Check max_position_size is reasonable
            if config.max_position_size > 7500:
                warnings.append(
                    f"max_position_size ${config.max_position_size} is higher than recommended ($7500)"
                )

            # Check circuit breakers are not too aggressive
            cb_thresholds = config.circuit_breaker_thresholds
            if cb_thresholds.get("daily_loss", 0) < -0.10:
                warnings.append(
                    "daily_loss threshold is very aggressive (< -10%)"
                )

            # Check trading hours format
            if config.trading_hours:
                start = config.trading_hours.get("start", "")
                end = config.trading_hours.get("end", "")
                if not (
                    len(start) == 5
                    and start[2] == ":"
                    and len(end) == 5
                    and end[2] == ":"
                ):
                    errors.append(
                        "trading_hours must be in HH:MM format (e.g., 09:30)"
                    )

            # Check max_daily_trades
            if (
                config.max_daily_trades is not None
                and config.max_daily_trades < 5
            ):
                warnings.append(
                    f"max_daily_trades {config.max_daily_trades} is lower than recommended (5+)"
                )

        except Exception as e:
            errors.append(f"Validation error: {str(e)}")

        return ValidationResult(
            valid=len(errors) == 0, errors=errors, warnings=warnings
        )

    def generate_diff(
        self, old_config: Dict[str, Any], new_config: Dict[str, Any]
    ) -> ConfigDiff:
        """
        Generate diff between old and new configuration.

        Args:
            old_config: Current configuration
            new_config: Proposed new configuration

        Returns:
            ConfigDiff showing changes, additions, and removals
        """
        changes: Dict[str, Dict[str, Any]] = {}
        added: List[str] = []
        removed: List[str] = []
        unchanged = 0

        all_keys = set(old_config.keys()) | set(new_config.keys())

        for key in all_keys:
            if key not in old_config:
                added.append(key)
            elif key not in new_config:
                removed.append(key)
            elif old_config[key] != new_config[key]:
                changes[key] = {"old": old_config[key], "new": new_config[key]}
            else:
                unchanged += 1

        return ConfigDiff(
            changes=changes, added=added, removed=removed, unchanged=unchanged
        )

    def apply(
        self, config: BotConfigRequest, applied_by: str = "api_user", reason: Optional[str] = None
    ) -> ConfigChangeResult:
        """
        Apply new configuration with audit trail.

        Args:
            config: New configuration to apply
            applied_by: User or system applying the change
            reason: Optional reason for the change

        Returns:
            ConfigChangeResult with success status and version number
        """
        try:
            # Validate first
            validation = self.validate(config)
            if not validation.valid:
                return ConfigChangeResult(
                    success=False,
                    message=f"Validation failed: {', '.join(validation.errors)}",
                    config_version=self._get_current_version(),
                    applied_at=datetime.utcnow(),
                    rollback_available=True,
                )

            # Get current config and generate diff
            old_config = self.get_current_config()
            new_config = config.model_dump(exclude_none=True)
            diff = self.generate_diff(old_config, new_config)

            # Get next version number
            new_version = self._get_current_version() + 1

            # Write new config
            self.config_file.write_text(json.dumps(new_config, indent=2))

            # Write to audit trail
            history_entry = ConfigHistoryEntry(
                version=new_version,
                timestamp=datetime.utcnow(),
                changes=diff,
                applied_by=applied_by,
                reason=reason,
            )
            self._append_history(history_entry)

            return ConfigChangeResult(
                success=True,
                message="Configuration applied successfully",
                config_version=new_version,
                applied_at=datetime.utcnow(),
                rollback_available=True,
            )

        except Exception as e:
            return ConfigChangeResult(
                success=False,
                message=f"Failed to apply configuration: {str(e)}",
                config_version=self._get_current_version(),
                applied_at=datetime.utcnow(),
                rollback_available=True,
            )

    def rollback(self, versions: int = 1) -> ConfigChangeResult:
        """
        Rollback to previous configuration.

        Args:
            versions: Number of versions to roll back (default: 1)

        Returns:
            ConfigChangeResult with rollback status
        """
        try:
            history = self._get_history()
            if len(history) < versions:
                return ConfigChangeResult(
                    success=False,
                    message=f"Cannot rollback {versions} versions (only {len(history)} in history)",
                    config_version=self._get_current_version(),
                    applied_at=datetime.utcnow(),
                    rollback_available=False,
                )

            # Get config from N versions ago
            target_entry = history[-(versions + 1)] if len(history) > versions else history[0]

            # Reconstruct old config by reversing changes
            current_config = self.get_current_config()
            for i in range(versions):
                entry = history[-(i + 1)]
                for key, change in entry.changes.changes.items():
                    current_config[key] = change["old"]
                # Handle added/removed fields
                for key in entry.changes.added:
                    current_config.pop(key, None)

            # Write rolled-back config
            self.config_file.write_text(json.dumps(current_config, indent=2))

            new_version = self._get_current_version() + 1

            # Log rollback in history
            rollback_entry = ConfigHistoryEntry(
                version=new_version,
                timestamp=datetime.utcnow(),
                changes=ConfigDiff(
                    changes={}, added=[], removed=[], unchanged=0
                ),
                applied_by="system",
                reason=f"Rollback {versions} version(s)",
            )
            self._append_history(rollback_entry)

            return ConfigChangeResult(
                success=True,
                message=f"Rolled back {versions} version(s)",
                config_version=new_version,
                applied_at=datetime.utcnow(),
                rollback_available=len(history) > 1,
            )

        except Exception as e:
            return ConfigChangeResult(
                success=False,
                message=f"Rollback failed: {str(e)}",
                config_version=self._get_current_version(),
                applied_at=datetime.utcnow(),
                rollback_available=True,
            )

    def _get_current_version(self) -> int:
        """Get current configuration version number."""
        history = self._get_history()
        return history[-1].version if history else 0

    def _get_history(self) -> List[ConfigHistoryEntry]:
        """Load configuration history from JSONL file."""
        if not self.history_file.exists():
            return []

        history = []
        for line in self.history_file.read_text().strip().split("\n"):
            if line:
                entry_data = json.loads(line)
                history.append(ConfigHistoryEntry(**entry_data))
        return history

    def _append_history(self, entry: ConfigHistoryEntry) -> None:
        """Append configuration change to history file."""
        with open(self.history_file, "a") as f:
            f.write(entry.model_dump_json() + "\n")
