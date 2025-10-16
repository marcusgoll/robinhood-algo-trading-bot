"""
Cache utilities for incremental performance summary updates.
"""

from pathlib import Path
from typing import Dict, Optional


def load_index() -> Dict[str, str]:
    """
    Load the cache index file containing checksums and metadata.

    Returns:
        Dictionary mapping file paths to checksums
    """
    raise NotImplementedError("To be implemented in GREEN phase")


def update_index(index: Dict[str, str], index_path: Path) -> None:
    """
    Update the cache index file atomically.

    Args:
        index: Updated index dictionary
        index_path: Path to index file
    """
    raise NotImplementedError("To be implemented in GREEN phase")


def needs_refresh(file_path: Path, checksum: Optional[str]) -> bool:
    """
    Check if a file needs to be reprocessed based on checksum.

    Args:
        file_path: Path to trade log file
        checksum: Previously stored checksum

    Returns:
        True if file has changed or is new
    """
    raise NotImplementedError("To be implemented in GREEN phase")
