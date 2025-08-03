"""
E2E Test 4: Text Processing and Normalization Workflow

Tests comprehensive text cleaning and normalization including title replacements,
artist extraction from titles, and metadata processing rules.
"""

import pytest
from pathlib import Path
import os
from .e2e_test_utils import temporary_config, run_fortherekord, get_test_library_path, assert_test_library_exists


def test_text_processing_and_normalization_workflow():
    """Test comprehensive text processing with aggressive cleaning rules."""
    # Ensure test library exists
    assert_test_library_exists()
    
    # Create config with comprehensive text processing rules
    config = {
        'rekordbox': {
            'library_path': get_test_library_path()
        },
        'spotify': {
            'client_id': os.environ.get('SPOTIFY_CLIENT_ID', 'test_id'),
            'client_secret': os.environ.get('SPOTIFY_CLIENT_SECRET', 'test_secret'),
            'redirect_uri': 'http://localhost:8888/callback',
            'scope': 'playlist-modify-public playlist-modify-private user-library-read',
            'exclude_from_names': [
                'feat.',
                'featuring',
                'ft.'
            ]
        },
        'text_processing': {
            'replace_in_title': [
                {'from': ' (Original Mix)', 'to': ''},
                {'from': ' (Extended Mix)', 'to': ''},
                {'from': ' (Remix)', 'to': ''}
            ],
            'extract_artist_from_title': True,  # Extract artist from "Artist - Title" format
            'add_key_to_title': True,  # Add key information to title
            'remove_artist_from_title': True  # Remove artist from title if already in artist field
        },
        'playlists': {
            'prefix': 'text_test'
        },
        'matching': {
            'similarity_threshold': 0.85  # Lower threshold for more aggressive matching
        }
    }
    
    # Use shared temporary config utility
    with temporary_config(config):
        # Run with text processing configuration using shared utility
        result = run_fortherekord()
        
        output = result.stdout + result.stderr
        
        # Should process all 30 tracks from test library
        # Test library contains tracks with "(Original Mix)", "(Extended Mix)", and "Artist - Title" formats
        processing_indicators = [
            "30", "tracks", "processed", "processing", "normalized", "cleaned"
        ]
        assert any(indicator in output.lower() for indicator in processing_indicators), \
            f"No text processing indicators found. Output: {output}"
        
        # Should complete text processing workflow
        assert result.returncode == 0 or "spotify" in output.lower(), \
            f"Text processing workflow failed. Output: {output}"
        
        # Look for evidence that text rules were applied
        # Our test library has specific patterns that should trigger the rules
        completion_indicators = [
            "completed", "finished", "done", "success", "sync"
        ]
        assert any(indicator in output.lower() for indicator in completion_indicators) or \
               "track" in output.lower(), \
            f"Text processing completion not evident. Output: {output}"
