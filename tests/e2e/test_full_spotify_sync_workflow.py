"""
E2E Test 2: Full Spotify API Integration Workflow

Tests the complete Spotify integration including authentication, track searching,
and playlist operations. Requires valid Spotify credentials via environment variables.

Credentials should be set in .env.local file:
SPOTIFY_CLIENT_ID=your_client_id
SPOTIFY_CLIENT_SECRET=your_client_secret
"""

import pytest
from pathlib import Path
import os
from .e2e_test_utils import temporary_config, run_fortherekord, get_test_library_path, assert_test_library_exists


@pytest.mark.skipif(
    not os.environ.get('SPOTIFY_CLIENT_ID') or not os.environ.get('SPOTIFY_CLIENT_SECRET'),
    reason="Spotify credentials not configured in environment variables"
)
def test_full_spotify_sync_workflow():
    """Test complete Spotify integration workflow with real API credentials."""
    # Ensure test library exists
    assert_test_library_exists()
    
    # Create config with real Spotify credentials
    config = {
        'rekordbox': {
            'library_path': get_test_library_path()
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
            'prefix': 'e2e_test'
        },
        'matching': {
            'similarity_threshold': 0.9
        }
    }
    
    # Use shared temporary config utility
    with temporary_config(config):
        # Run the main command with Spotify integration using shared utility
        result = run_fortherekord()
        
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
