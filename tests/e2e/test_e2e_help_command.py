"""
E2E test for help command.

Tests that the --help command works correctly.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "tests" / "e2e"))
from conftest import e2e_harness


def test_help_command(e2e_harness):
    """Test help command e2e functionality."""
    result = e2e_harness.run(["--help"])

    e2e_harness.assert_process_succeeded(True)
    assert "ForTheRekord" in result.stdout
