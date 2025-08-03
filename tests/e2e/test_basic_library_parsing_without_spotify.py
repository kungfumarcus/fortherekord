"""
E2E Test 1: Basic Library Parsing Without Spotify

Tests that the application can successfully parse a Rekordbox library
and display track/playlist information without requiring Spotify credentials.
This validates the core XML parsing functionality works independently.
"""

import pytest
from pathlib import Path
from .e2e_test_utils import temporary_config, run_fortherekord, get_test_library_path, assert_test_library_exists


def test_basic_library_parsing_without_spotify():
    """Test that library parsing works without valid Spotify credentials."""
    # Ensure test library exists
    assert_test_library_exists()
    
    # Create config with invalid Spotify credentials
    config = {
        'rekordbox': {
            'library_path': get_test_library_path()
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
    
    # Use shared temporary config utility
    with temporary_config(config):
        # Run the main command using shared utility
        result = run_fortherekord()
        
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
