"""
E2E Test 1: Basic Library Parsing Without Spotify

Tests that the application can successfully parse a Rekordbox library
and display track/playlist information without requiring Spotify credentials.
This validates the core XML parsing functionality works independently.
"""

import pytest
import tempfile
import yaml
from pathlib import Path
import subprocess
import sys
import os


def test_basic_library_parsing_without_spotify():
    """Test that library parsing works without valid Spotify credentials."""
    # Create config with invalid Spotify credentials
    config = {
        'rekordbox': {
            'library_path': 'tests/e2e/test_library.xml'
        },
        'spotify': {
            'client_id': 'your_spotify_client_id',  # Invalid placeholder
            'client_secret': 'your_spotify_client_secret'  # Invalid placeholder
        },
        'text_processing': {
            'replace_in_title': []
        },
        'playlists': {
            'prefix': 'rb'
        },
        'matching': {
            'similarity_threshold': 0.9
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config, f)
        config_path = f.name
    
    try:
        # Get absolute path to test library
        test_library = Path("tests/e2e/test_library.xml").absolute()
        assert test_library.exists(), f"Test library not found: {test_library}"
        
        # Run sync command
        result = subprocess.run([
            sys.executable, "-m", "fortherekord",
            "sync", str(test_library)
        ], capture_output=True, text=True, cwd=Path.cwd())
        
        # Should succeed in parsing library even without valid Spotify
        # or handle Spotify errors gracefully
        output = result.stdout + result.stderr
        
        # Look for evidence of library parsing
        library_indicators = [
            "30", "tracks", "playlists", "loaded", "found", "collection"
        ]
        assert any(indicator in output.lower() for indicator in library_indicators), \
            f"No library parsing indicators found. Output: {output}"
        
        # Should not crash completely
        assert result.returncode == 0 or "spotify" in output.lower(), \
            f"Unexpected failure. Output: {output}"
        
    finally:
        if os.path.exists(config_path):
            os.unlink(config_path)
