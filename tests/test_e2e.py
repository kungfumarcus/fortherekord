"""
End-to-end test for ForTheRekord CLI application.

Single comprehensive test that verifies the basic CLI functionality works end-to-end.
"""

import subprocess
import sys
from pathlib import Path


def run_fortherekord_command(args: list[str]) -> subprocess.CompletedProcess:
    """
    Helper function to run fortherekord CLI commands as a subprocess.

    Args:
        args: Command line arguments to pass to fortherekord

    Returns:
        CompletedProcess with stdout, stderr, and return code
    """
    cmd = [sys.executable, "-m", "fortherekord"] + args
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent,  # Run from project root
    )


def test_basic_cli_functionality():
    """Test basic CLI functionality end-to-end."""
    # Test help works
    help_result = run_fortherekord_command(["--help"])
    assert help_result.returncode == 0
    assert "ForTheRekord" in help_result.stdout

    # Test version works
    version_result = run_fortherekord_command(["--version"])
    assert version_result.returncode == 0

    # Test main command with no config (should create config and show error)
    main_result = run_fortherekord_command([])
    assert main_result.returncode == 0
    # Should attempt to create config and handle missing database gracefully
    assert (
        "rekordbox_library_path" in main_result.stdout or "Loading Rekordbox" in main_result.stdout
    )
