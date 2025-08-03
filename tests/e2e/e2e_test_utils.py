"""
E2E Test Utilities

Common utilities for End-to-End testing including config management,
temporary file handling, and test environment setup.
"""

import tempfile
import yaml
import os
import shutil
from pathlib import Path
from contextlib import contextmanager
from typing import Dict, Any, Generator
import subprocess
import sys

from fortherekord.config import get_config_path


@contextmanager
def temporary_config(config_data: Dict[str, Any]) -> Generator[Path, None, None]:
    """
    Context manager that creates a temporary config file in the expected location
    for the application to find, then cleans up afterwards.
    
    This allows E2E tests to run exactly like a user would, with the application
    loading config from its normal location.
    """
    config_path = get_config_path()
    backup_path = None
    
    # Backup existing config if it exists
    if config_path.exists():
        backup_path = config_path.with_suffix('.backup')
        shutil.copy2(config_path, backup_path)
    
    try:
        # Ensure config directory exists
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write temporary config
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)
        
        yield config_path
        
    finally:
        # Cleanup: restore backup or remove temp config
        if backup_path and backup_path.exists():
            shutil.copy2(backup_path, config_path)
            backup_path.unlink()
        elif config_path.exists():
            config_path.unlink()


def run_fortherekord(*args) -> subprocess.CompletedProcess:
    """
    Run the fortherekord CLI with the given arguments.
    Returns the completed process for output inspection.
    """
    cmd = [sys.executable, "-m", "fortherekord"] + list(args)
    return subprocess.run(cmd, capture_output=True, text=True, cwd=Path.cwd())


def get_test_library_path() -> str:
    """Get the absolute path to the test library XML file."""
    return str(Path("tests/e2e/test_library.xml").absolute())


def assert_test_library_exists() -> None:
    """Assert that the test library exists, with helpful error message."""
    test_library = Path(get_test_library_path())
    assert test_library.exists(), f"Test library not found: {test_library}"
