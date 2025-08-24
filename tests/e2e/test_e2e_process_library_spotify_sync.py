"""
E2E test for Spotify playlist synchronization with real credentials.

Tests the complete workflow from command line execution to Spotify authentication and sync.
Requires real Spotify credentials in the user's config file.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "tests" / "e2e"))
from conftest import e2e_harness


def test_e2e_process_library_spotify_sync(e2e_harness):
    """Test complete E2E playlist sync workflow with real Spotify credentials."""
    import pytest

    # Run the main command - should get to Spotify authentication stage
    result = e2e_harness.run()

    # Should complete successfully and show that it loaded the library and authenticated with Spotify
    e2e_harness.assert_process_succeeded(True)
    e2e_harness.assert_rekordbox_loaded(True)
    e2e_harness.assert_spotify_synced(True)
    e2e_harness.assert_rekordbox_save(True)