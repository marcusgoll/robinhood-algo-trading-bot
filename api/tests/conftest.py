"""Pytest configuration and fixtures."""

import sys
from pathlib import Path

# Add api directory to Python path for absolute imports
api_dir = Path(__file__).parent.parent
sys.path.insert(0, str(api_dir))

# Also add parent directory to support 'api.app' imports
parent_dir = api_dir.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))
