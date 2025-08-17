"""
E2E Test Configuration and Fixtures

Centralized configuration for end-to-end tests.
"""

import pytest
import subprocess
import sys
import os
from pathlib import Path


def pytest_configure(config):
    """Configure pytest for e2e tests."""
    # Set timeout for all e2e tests
    config.option.timeout = 30


# Configure E2E test timeout globally for this module
pytestmark = [
    pytest.mark.e2e,
    pytest.mark.timeout(30)  # All E2E tests get 30 second timeout
]


def run_fortherekord_command(args: list[str], env_vars: dict = None) -> subprocess.CompletedProcess:
    """
    Helper function to run fortherekord CLI commands as a subprocess.

    Args:
        args: Command line arguments to pass to fortherekord
        env_vars: Additional environment variables to set

    Returns:
        CompletedProcess with stdout, stderr, and return code
    """
    cmd = [sys.executable, "-m", "fortherekord"] + args
    
    # Set up environment with test safety
    env = os.environ.copy()
    if env_vars:
        env.update(env_vars)
    
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent.parent,  # Run from project root
        env=env
    )
