"""
Tests for __main__.py module entry point.
"""

import subprocess
import sys
from pathlib import Path


class TestMainModule:
    """Test the __main__.py entry point."""
    
    def test_main_module_can_be_executed(self):
        """Test that 'python -m fortherekord' can be executed."""
        # Test that the module can be run (will fail due to missing config, but should not crash)
        result = subprocess.run(
            [sys.executable, "-m", "fortherekord", "--help"],
            capture_output=True,
            text=True,
            cwd=Path.cwd()
        )
        
        # Should show help and exit successfully
        assert result.returncode == 0
        assert "ForTheRekord" in result.stdout or "Usage:" in result.stdout
    
    def test_main_module_version_flag(self):
        """Test that version flag works through module execution."""
        result = subprocess.run(
            [sys.executable, "-m", "fortherekord", "--version"],
            capture_output=True,
            text=True,
            cwd=Path.cwd()
        )
        
        # Should show version and exit successfully
        assert result.returncode == 0
        # Version output should contain some version info
        assert len(result.stdout.strip()) > 0
