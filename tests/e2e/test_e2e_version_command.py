"""
E2E test for version command.

Tests that the --version command works correctly.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "tests" / "e2e"))
from conftest import e2e_harness


def test_version_command(e2e_harness):
    """Test version command e2e functionality."""
    result = e2e_harness.run(["--version"])
    
    e2e_harness.assert_process_succeeded(True)
    assert "0.1" in result.stdout
