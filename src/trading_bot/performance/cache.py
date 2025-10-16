"""
Cache utilities for incremental performance summary updates.
"""

import hashlib
import json
from pathlib import Path


def load_index(index_path: Path = Path("logs/performance/performance-index.json")) -> dict[str, str]:
    """
    Load the cache index file containing checksums and metadata.

    Args:
        index_path: Path to index file (default: logs/performance/performance-index.json)

    Returns:
        Dictionary mapping file paths to MD5 checksums.
        Returns empty dict if file doesn't exist.
    """
    if not index_path.exists():
        return {}

    try:
        with open(index_path, encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        # Corrupt index - return empty
        return {}


def update_index(index: dict[str, str], index_path: Path) -> None:
    """
    Update the cache index file atomically.

    Uses temp file + rename pattern for atomic writes to prevent
    corruption if process is interrupted.

    Args:
        index: Updated index dictionary mapping paths to checksums
        index_path: Path to index file
    """
    # Ensure directory exists
    index_path.parent.mkdir(parents=True, exist_ok=True)

    # Write to temp file first (atomic rename)
    temp_path = index_path.with_suffix('.tmp')
    with open(temp_path, 'w', encoding='utf-8') as f:
        json.dump(index, f, indent=2)

    # Atomic rename
    temp_path.replace(index_path)


def needs_refresh(file_path: Path, checksum: str | None) -> bool:
    """
    Check if a file needs to be reprocessed based on MD5 checksum.

    Args:
        file_path: Path to trade log file
        checksum: Previously stored checksum (None if new file)

    Returns:
        True if file has changed or is new, False if unchanged
    """
    # New file - always refresh
    if checksum is None:
        return True

    # File doesn't exist - no refresh needed
    if not file_path.exists():
        return False

    # Compute current checksum
    # MD5 is used for file integrity checking, not cryptographic security
    current_checksum = hashlib.md5(file_path.read_bytes(), usedforsecurity=False).hexdigest()  # nosec B324

    # Compare
    return current_checksum != checksum
