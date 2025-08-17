"""
Test Configuration and Fixtures

Centralized configuration and fixtures for all tests.
"""

import os
import pytest
from pathlib import Path


def cleanup_test_dump_file():
    """
    Clean up the test dump file created by save_changes() in test mode.
    
    This should be called in finally blocks of tests that call save_changes()
    without overriding the FORTHEREKORD_TEST_DUMP_FILE environment variable.
    """
    dump_file = os.getenv("FORTHEREKORD_TEST_DUMP_FILE", "test_changes_dump.json")
    if Path(dump_file).exists():
        try:
            Path(dump_file).unlink()
        except OSError:
            pass  # File might be in use or already deleted


@pytest.fixture
def temp_test_file():
    """
    Create a temporary test file that gets cleaned up automatically.
    
    Returns:
        Path: Path to a temporary file that will be cleaned up
    """
    import tempfile
    
    # Create a temporary file
    fd, path = tempfile.mkstemp(suffix=".test")
    os.close(fd)
    
    yield Path(path)
    
    # Clean up
    try:
        Path(path).unlink()
    except OSError:
        pass
