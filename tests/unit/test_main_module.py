"""
Tests for __main__.py entry point.

Tests the module entry point functionality.
"""

import subprocess
import sys


def test_main_module_execution():
    """Test that the module can be executed via python -m."""
    # Test that the module can be imported and executed
    result = subprocess.run(
        [sys.executable, "-m", "fortherekord", "--help"], capture_output=True, text=True, timeout=5
    )

    assert result.returncode == 0
    assert "ForTheRekord" in result.stdout
