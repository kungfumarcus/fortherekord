"""
E2E Test Configuration and Fixtures

Centralized configuration for end-to-end tests.
"""

import pytest
import subprocess
import sys
import os
import tempfile
from pathlib import Path


def pytest_configure(config):
    """Configure pytest for e2e tests."""
    # Set timeout for all e2e tests
    config.option.timeout = 30


# Configure E2E test timeout globally for this module
pytestmark = [pytest.mark.e2e, pytest.mark.timeout(30)]  # All E2E tests get 30 second timeout


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
        env=env,
    )


@pytest.fixture
def test_environment_with_dump_file():
    """
    Pytest fixture that provides a test environment with dump file.

    Yields:
        tuple: (dump_path, test_env) where test_env contains the test mode variables
    """
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as dump_file:
        dump_path = dump_file.name

    # Set up test environment with Spotify cache path for E2E tests
    spotify_cache_path = Path(__file__).parent / ".spotify_cache_test"

    test_env = {
        "FORTHEREKORD_TEST_MODE": "1",
        "FORTHEREKORD_TEST_DUMP_FILE": dump_path,
        "FORTHEREKORD_SPOTIFY_CACHE_PATH": str(spotify_cache_path),
    }

    try:
        yield dump_path, test_env
    finally:
        if Path(dump_path).exists():
            Path(dump_path).unlink()


@pytest.fixture
def temporary_config_file():
    """
    Pytest fixture that creates a temporary YAML config file.

    Returns:
        function: A function that takes config_content and returns the path
    """
    created_files = []

    def _create_config(config_content: str) -> str:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as config_file:
            config_path = config_file.name
            config_file.write(config_content)
            created_files.append(config_path)
        return config_path

    yield _create_config

    # Cleanup
    for config_path in created_files:
        if Path(config_path).exists():
            Path(config_path).unlink()


def verify_json_dump_file(dump_path: str):
    """
    Verify that a JSON dump file contains valid JSON data.

    Args:
        dump_path: Path to the dump file to verify
    """
    if Path(dump_path).exists():
        with open(dump_path, "r") as f:
            content = f.read().strip()
            if content:  # Only check if there's actual content
                import json

                dump_data = json.loads(content)
                assert isinstance(
                    dump_data, (dict, list)
                ), "Dump should contain valid JSON structure"
