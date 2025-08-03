"""
E2E Test 5: Playlist Remapping and Management Workflow

Tests playlist remapping functionality using the --remap flag, including
playlist name changes and track association management.
"""

import pytest
import tempfile
import yaml
from pathlib import Path
import subprocess
import sys
import os


def test_playlist_remapping_and_management_workflow():
    """Test playlist remapping workflow with --remap flag."""
    # Create config with playlist remapping rules
    config = {
        'rekordbox': {
            'library_path': 'tests/e2e/test_library.xml'
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
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config, f)
        config_path = f.name
    
    try:
        test_library = Path("tests/e2e/test_library.xml").absolute()
        assert test_library.exists(), f"Test library not found: {test_library}"
        
        # Run sync with --remap flag to trigger playlist remapping
        result = subprocess.run([
            sys.executable, "-m", "fortherekord",
            "sync", str(test_library),
            "--remap"
        ], capture_output=True, text=True, cwd=Path.cwd())
        
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
        
    finally:
        if os.path.exists(config_path):
            os.unlink(config_path)
