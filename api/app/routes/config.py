"""API routes for bot configuration management."""

from __future__ import annotations

from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status

from ..core.auth import verify_api_key
from ..schemas.config import (
    BotConfigRequest,
    ConfigChangeResult,
    ConfigDiff,
    ValidationResult,
)
from ..services.config_validator import ConfigValidator

router = APIRouter(prefix="/config", tags=["config"])


def get_config_validator() -> ConfigValidator:
    """Dependency injection for ConfigValidator."""
    return ConfigValidator()


@router.get(
    "",
    response_model=Dict[str, Any],
    summary="Get current bot configuration",
    description="Returns the currently active bot configuration",
)
async def get_current_config(
    _: bool = Depends(verify_api_key),
    validator: ConfigValidator = Depends(get_config_validator),
) -> Dict[str, Any]:
    """
    Get current bot configuration.

    Returns:
        Current active configuration as JSON dict
    """
    return validator.get_current_config()


@router.post(
    "/validate",
    response_model=ValidationResult,
    summary="Validate configuration without applying",
    description="Validates a configuration change against schema and business rules",
)
async def validate_config(
    config: BotConfigRequest,
    _: bool = Depends(verify_api_key),
    validator: ConfigValidator = Depends(get_config_validator),
) -> ValidationResult:
    """
    Validate configuration without applying.

    Args:
        config: Configuration to validate

    Returns:
        ValidationResult with errors and warnings
    """
    return validator.validate(config)


@router.get(
    "/diff",
    response_model=ConfigDiff,
    summary="Preview configuration changes",
    description="Shows what would change if new configuration is applied",
)
async def get_config_diff(
    config: BotConfigRequest,
    _: bool = Depends(verify_api_key),
    validator: ConfigValidator = Depends(get_config_validator),
) -> ConfigDiff:
    """
    Get diff between current and proposed configuration.

    Args:
        config: Proposed new configuration

    Returns:
        ConfigDiff showing changes, additions, and removals
    """
    current = validator.get_current_config()
    new_config = config.model_dump(exclude_none=True)
    return validator.generate_diff(current, new_config)


@router.put(
    "",
    response_model=ConfigChangeResult,
    summary="Apply new configuration",
    description="Applies new configuration with validation and audit trail",
)
async def apply_config(
    config: BotConfigRequest,
    reason: str | None = None,
    _: bool = Depends(verify_api_key),
    validator: ConfigValidator = Depends(get_config_validator),
) -> ConfigChangeResult:
    """
    Apply new bot configuration.

    Args:
        config: New configuration to apply
        reason: Optional reason for the change

    Returns:
        ConfigChangeResult with success status and version number
    """
    result = validator.apply(config, applied_by="api_user", reason=reason)
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.message,
        )
    return result


@router.put(
    "/rollback",
    response_model=ConfigChangeResult,
    summary="Rollback to previous configuration",
    description="Rolls back to previous configuration version(s)",
)
async def rollback_config(
    versions: int = 1,
    _: bool = Depends(verify_api_key),
    validator: ConfigValidator = Depends(get_config_validator),
) -> ConfigChangeResult:
    """
    Rollback configuration to previous version.

    Args:
        versions: Number of versions to roll back (default: 1)

    Returns:
        ConfigChangeResult with rollback status
    """
    if versions < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Versions must be >= 1",
        )

    result = validator.rollback(versions)
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.message,
        )
    return result
