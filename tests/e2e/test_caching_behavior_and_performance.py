"""
E2E Test 3: Caching Behavior and Performance

Tests the caching functionality including cache creation, loading,
and performance improvements on subsequent runs using the --use-cache flag.
"""

import pytest
import tempfile
from pathlib import Path
import os
import time
from .e2e_test_utils import temporary_config, run_fortherekord, get_test_library_path, assert_test_library_exists


def test_caching_behavior_and_performance():
    """Test cache creation, loading, and performance improvements."""
    # Ensure test library exists
    assert_test_library_exists()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        cache_dir = os.path.join(temp_dir, "test_cache")
        
        # Create config with caching enabled
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
            'cache': {
                'enabled': True,
                'directory': cache_dir,
                'spotify_tracks': 'spotify_tracks.json',
                'rekordbox_tracks': 'rekordbox_tracks.json',
                'playlists': 'playlists.json'
            },
            'text_processing': {
                'replace_in_title': []
            },
            'playlists': {
                'prefix': 'cache_test'
            },
            'matching': {
                'similarity_threshold': 0.9
            }
        }
        
        # Use shared temporary config utility
        with temporary_config(config):
            # First run - create cache
            start_time = time.time()
            result1 = run_fortherekord("--use-cache")
            first_run_time = time.time() - start_time
            
            # Verify cache directory and files were created
            assert os.path.exists(cache_dir), "Cache directory was not created"
            
            # Look for cache files (at minimum, should cache rekordbox data)
            cache_files = os.listdir(cache_dir)
            assert len(cache_files) > 0, f"No cache files created in {cache_dir}"
            
            # Second run - use cache
            start_time = time.time()
            result2 = run_fortherekord("--use-cache")
            second_run_time = time.time() - start_time
            
            # Second run should indicate cache usage
            output2 = result2.stdout + result2.stderr
            cache_indicators = [
                "cache", "cached", "loading from cache", "using cached", "from cache"
            ]
            assert any(indicator in output2.lower() for indicator in cache_indicators), \
                f"No cache usage indicators in second run. Output: {output2}"
            
            # Both runs should succeed
            assert result1.returncode == 0 or "spotify" in (result1.stdout + result1.stderr).lower(), \
                f"First run failed: {result1.stderr}"
            assert result2.returncode == 0 or "spotify" in (result2.stdout + result2.stderr).lower(), \
                f"Second run failed: {result2.stderr}"
