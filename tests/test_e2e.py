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
    assert "sync" in help_result.stdout
    
    # Test version works
    version_result = run_fortherekord_command(["--version"])
    assert version_result.returncode == 0
    assert "version" in version_result.stdout.lower()
    
    # Test sync command (not implemented)
    sync_result = run_fortherekord_command(["sync"])
    assert sync_result.returncode == 0
    assert "not yet implemented" in sync_result.stdout.lower()
