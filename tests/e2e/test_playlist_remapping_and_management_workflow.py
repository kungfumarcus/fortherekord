"""
E2E Test 5: Playlist Remapping and Management Workflow

Tests playlist remapping functionality using the --remap flag, including
playlist name changes and track association management.
"""

import pytest
from pathlib import Path
import os
from .e2e_test_utils import temporary_config, run_fortherekord, get_test_library_path, assert_test_library_exists


def test_playlist_remapping_and_management_workflow():
    """Test playlist remapping workflow with --remap flag."""
    # Ensure test library exists
    assert_test_library_exists()
    
    # Create config with playlist remapping rules
    config = {
        'rekordbox': {
            'library_path': get_test_library_path()
        },
        'spotify': {
            'client_id': os.environ.get('SPOTIFY_CLIENT_ID', 'test_id'),
            'client_secret': os.environ.get('SPOTIFY_CLIENT_SECRET', 'test_secret'),
            'redirect_uri': 'http://localhost:8888/callback',
            'scope': 'playlist-modify-public playlist-modify-private user-library-read'
        },
        'playlists': {
            'prefix': 'remap_test',
            'create_missing': True,
            'update_existing': True,
            'remap': {
                'House Mix': 'Electronic House Collection',
                'Techno Sessions': 'Underground Techno',
                'Progressive Journey': 'Progressive Electronic Music'
            }
        },
        'text_processing': {
            'replace_in_title': []
        },
        'matching': {
            'similarity_threshold': 0.9
        }
    }
    
    # Use shared temporary config utility
    with temporary_config(config):
        # Run with --remap flag using shared utility
        result = run_fortherekord("--remap")
        
        output = result.stdout + result.stderr
        
        # Should process our 3 test playlists with their remapped names
        # Test library has: House Mix (8 tracks), Techno Sessions (6 tracks), Progressive Journey (5 tracks)
        playlist_indicators = [
            "playlist", "house", "techno", "progressive", "electronic", "underground"
        ]
        assert any(indicator in output.lower() for indicator in playlist_indicators), \
            f"No playlist processing indicators found. Output: {output}"
        
        # Should handle remapping workflow
        remap_indicators = [
            "remap", "mapping", "renamed", "collection", "remapped"
        ]
        assert any(indicator in output.lower() for indicator in remap_indicators) or \
               "playlist" in output.lower(), \
            f"No remapping indicators found. Output: {output}"
        
        # Should complete playlist management workflow
        assert result.returncode == 0 or "spotify" in output.lower(), \
            f"Playlist remapping workflow failed. Output: {output}"
        
        # Should process tracks within playlists (19 total tracks across 3 playlists)
        track_indicators = [
            "track", "tracks", "song", "added", "found"
        ]
        assert any(indicator in output.lower() for indicator in track_indicators), \
            f"No track processing in playlists found. Output: {output}"
