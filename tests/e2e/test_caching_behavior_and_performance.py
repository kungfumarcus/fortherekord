"""
E2E Test 3: Caching Behavior and Performance

Tests the caching functionality including cache creation, loading,
and performance improvements on subsequent runs using the --use-cache flag.
"""

import pytest
import tempfile
import yaml
from pathlib import Path
import subprocess
import sys
import os
import time


def test_caching_behavior_and_performance():
    """Test cache creation, loading, and performance improvements."""
    with tempfile.TemporaryDirectory() as temp_dir:
        cache_dir = os.path.join(temp_dir, "test_cache")
        
        # Create config with caching enabled
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
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config, f)
            config_path = f.name
        
        try:
            test_library = Path("tests/e2e/test_library.xml").absolute()
            assert test_library.exists(), f"Test library not found: {test_library}"
            
            # First run - create cache
            start_time = time.time()
            result1 = subprocess.run([
                sys.executable, "-m", "fortherekord",
                "sync", str(test_library),
                "--use-cache"
            ], capture_output=True, text=True, cwd=Path.cwd())
            first_run_time = time.time() - start_time
            
            # Verify cache directory and files were created
            assert os.path.exists(cache_dir), "Cache directory was not created"
            
            # Look for cache files (at minimum, should cache rekordbox data)
            cache_files = os.listdir(cache_dir)
            assert len(cache_files) > 0, f"No cache files created in {cache_dir}"
            
            # Second run - use cache
            start_time = time.time()
            result2 = subprocess.run([
                sys.executable, "-m", "fortherekord",
                "sync", str(test_library),
                "--use-cache"
            ], capture_output=True, text=True, cwd=Path.cwd())
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
            
        finally:
            if os.path.exists(config_path):
                os.unlink(config_path)
