"""
E2E test for version command.

Tests that the --version command works correctly.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "tests" / "e2e"))
from conftest import run_fortherekord_command


def test_version_command():
    """Test version command e2e functionality."""
    version_result = run_fortherekord_command(["--version"])
    assert version_result.returncode == 0
    assert "0.1" in version_result.stdout
