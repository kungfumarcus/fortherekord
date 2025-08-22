"""
E2E test for help command.

Tests that the --help command works correctly.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "tests" / "e2e"))
from conftest import run_fortherekord_command


def test_help_command():
    """Test help command e2e functionality."""
    help_result = run_fortherekord_command(["--help"])
    assert help_result.returncode == 0
    assert "ForTheRekord" in help_result.stdout
