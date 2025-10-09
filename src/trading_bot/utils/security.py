"""
Credential masking utilities for secure logging.

Provides functions to mask sensitive credential data in logs according to
Constitution v1.0.0 §Security requirements.

Pattern extracted from RobinhoodAuth._mask_credential (lines 79-88).
"""


def mask_username(username: str) -> str:
    """
    Mask a username/email for logging.

    Pattern: Show first 3 characters + *** + domain (if email)
    Examples:
        "john@example.com" -> "joh***@example.com"
        "johndoe" -> "joh***"
        "" -> "****"

    Args:
        username: Username or email address to mask

    Returns:
        Masked username string safe for logging

    Constitution v1.0.0:
        §Security: Credentials never logged in plaintext
    """
    if not username:
        return "****"

    if "@" in username:
        # Email: preserve domain for debugging
        parts = username.split("@")
        local_part = parts[0][:3] if len(parts[0]) >= 3 else parts[0]
        return f"{local_part}***@{parts[1]}"

    # Non-email: show first 3 chars
    return f"{username[:3]}***" if len(username) >= 3 else "****"


def mask_password(password: str) -> str:
    """
    Mask a password for logging.

    Pattern: Always return "*****" regardless of input
    Examples:
        "any_password_123" -> "*****"
        "" -> "*****"

    Args:
        password: Password to mask

    Returns:
        Masked password string (always "*****")

    Constitution v1.0.0:
        §Security: Passwords never logged in any form
    """
    # Always return same mask regardless of password content or length
    return "*****"


def mask_mfa_secret(mfa_secret: str) -> str:
    """
    Mask an MFA TOTP secret for logging.

    Pattern: Always return "****" regardless of input
    Examples:
        "ABCDEFGHIJKLMNOP" -> "****"
        "" -> "****"

    Args:
        mfa_secret: MFA TOTP secret (base32 string) to mask

    Returns:
        Masked MFA secret string (always "****")

    Constitution v1.0.0:
        §Security: MFA secrets never logged in any form
    """
    # Always return same mask regardless of secret content or length
    return "****"


def mask_device_token(device_token: str) -> str:
    """
    Mask a device token for logging.

    Pattern: Show first 8 characters + ***
    Examples:
        "1a2b3c4d5e6f7g8h" -> "1a2b3c4d***"
        "short" -> "shor***"
        "" -> "****"

    Args:
        device_token: Device authentication token to mask

    Returns:
        Masked device token string safe for logging

    Constitution v1.0.0:
        §Security: Device tokens partially masked for debugging
    """
    if not device_token:
        return "****"

    # Show first 8 chars for debugging token prefix patterns
    return f"{device_token[:8]}***" if len(device_token) >= 8 else f"{device_token}***"
