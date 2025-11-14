"""
Tests for cache utilities.

Test T013 - RED phase
"""

import pytest
from pathlib import Path
import json

from trading_bot.performance.cache import load_index, update_index, needs_refresh


class TestCacheIndex:
    """T013: Incremental cache index persists checksums."""

    def test_cache_index_read_write(self, tmp_path):
        """
        Cache index read/write with checksum detection.

        Expected behavior (RED phase):
        - load_index() reads existing index
        - update_index() writes atomically
        - needs_refresh() detects stale files
        """
        index_path = tmp_path / "performance-index.json"

        # Initial empty index
        index = load_index(index_path)
        assert isinstance(index, dict)

        # Add entries
        index["logs/trades/2025-10-15.jsonl"] = "abc123"
        update_index(index, index_path)

        # Verify persistence
        assert index_path.exists()
        loaded = load_index(index_path)
        assert loaded["logs/trades/2025-10-15.jsonl"] == "abc123"

    def test_needs_refresh_detects_changes(self, tmp_path):
        """
        needs_refresh() detects file changes via checksum.

        Expected behavior (RED phase):
        - New file → needs refresh
        - Matching checksum → skip refresh
        - Changed checksum → needs refresh
        """
        test_file = tmp_path / "test.jsonl"
        test_file.write_text('{"trade": "data"}')

        # New file (no checksum)
        assert needs_refresh(test_file, None) is True

        # Compute checksum
        import hashlib

        checksum = hashlib.md5(test_file.read_bytes()).hexdigest()

        # Matching checksum
        assert needs_refresh(test_file, checksum) is False

        # Change file
        test_file.write_text('{"trade": "changed"}')
        assert needs_refresh(test_file, checksum) is True
