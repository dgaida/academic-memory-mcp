"""Configuration for pytest."""
import pytest
from pathlib import Path

@pytest.fixture
def temp_dir(tmp_path: Path) -> Path:
    """Provides a temporary directory for testing.

    Args:
        tmp_path (Path): Pytest fixture for a temporary directory.

    Returns:
        Path: The path to the temporary directory.
    """
    return tmp_path
