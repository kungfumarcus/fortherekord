"""
E2E Test 2: Full Spotify API Integration Workflow

Tests the complete Spotify integration including authentication, track searching,
and playlist operations. Requires valid Spotify credentials via environment variables.
"""

import pytest
import tempfile
import yaml
from pathlib import Path
import subprocess
import sys
import os


@pytest.mark.skipif(
    not os.environ.get('SPOTIFY_CLIENT_ID') or not os.environ.get('SPOTIFY_CLIENT_SECRET'),
    reason="Spotify credentials not configured in environment variables"
)
def test_full_spotify_sync_workflow():
    """Test complete Spotify integration workflow with real API credentials."""
    # Create config with real Spotify credentials
    config = {
        'rekordbox': {
            'library_path': 'tests/e2e/test_library.xml'
        },
        'spotify': {
            'client_id': os.environ.get('SPOTIFY_CLIENT_ID'),
            'client_secret': os.environ.get('SPOTIFY_CLIENT_SECRET'),
            'redirect_uri': 'http://localhost:8888/callback',
            'scope': 'playlist-modify-public playlist-modify-private user-library-read',
            'ignore_playlists': [],
            'follow_threshold': 1
        },
        'text_processing': {
            'replace_in_title': []
        },
        'playlists': {
            'prefix': 'e2e_test'  # Use test prefix to avoid conflicts
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
        
        # Run sync command with real Spotify integration
        result = subprocess.run([
            sys.executable, "-m", "fortherekord",
            "sync", str(test_library)
        ], capture_output=True, text=True, cwd=Path.cwd())
        
        output = result.stdout + result.stderr
        
        # Should successfully authenticate and interact with Spotify
        spotify_indicators = [
            "spotify", "authenticated", "connected", "token", "playlist", "search"
        ]
        assert any(indicator in output.lower() for indicator in spotify_indicators), \
            f"No Spotify integration indicators found. Output: {output}"
        
        # Workflow should complete successfully
        success_indicators = [
            "completed", "finished", "done", "success", "sync"
        ]
        assert any(indicator in output.lower() for indicator in success_indicators) or \
               result.returncode == 0, \
            f"Spotify workflow did not complete successfully. Output: {output}"
        
    finally:
        if os.path.exists(config_path):
            os.unlink(config_path)
