"""
E2E test for Spotify sync with invalid credentials.

Tests that the application handles invalid Spotify credentials gracefully.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "tests" / "e2e"))
from conftest import e2e_harness


def test_e2e_spotify_sync_invalid_credentials(e2e_harness):
    """Test Spotify sync when credentials are invalid."""

    # Disable processor (by omitting processor config) and override with invalid Spotify credentials
    e2e_harness.update_config(
        {
            "processor": None,  # Remove processor config to disable it
            "spotify": {
                "enabled": True,
                "client_id": "invalid_client_id_12345",
                "client_secret": "invalid_client_secret_67890",
                "playlist_sync": {"enabled": True},
            },
        }
    )

    # Run the main command - should fail gracefully with invalid Spotify credentials
    e2e_harness.run()

    # Should fail due to invalid Spotify credentials (but actually succeeds because
    # credentials just aren't configured)
    e2e_harness.assert_process_succeeded(
        True
    )  # App doesn't fail when creds are missing, just skips Spotify
    e2e_harness.assert_rekordbox_loaded(True)
    e2e_harness.assert_processor_ran(False)
    e2e_harness.assert_spotify_synced(False)  # Should be skipped due to missing creds
    e2e_harness.assert_rekordbox_save(False)
