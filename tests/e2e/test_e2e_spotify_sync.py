"""
E2E test for Spotify playlist sync when music library processor is disabled.

Tests the workflow where all processor enhancement features are disabled,
but Spotify sync should still continue to work.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "tests" / "e2e"))
from conftest import e2e_harness


def test_e2e_spotify_sync(e2e_harness):
    """Test Spotify playlist sync when music library processor is disabled."""

    # Configure with processor disabled (by omitting processor config)
    e2e_harness.update_config({
        "processor": None  # Remove processor config to disable it
    })

    # Run the command - should handle disabled processor gracefully
    result = e2e_harness.run()

    # Should handle the scenario gracefully
    e2e_harness.assert_process_succeeded(True)
    e2e_harness.assert_rekordbox_loaded(True)
    e2e_harness.assert_processor_ran(False)
    e2e_harness.assert_spotify_synced(True)
    e2e_harness.assert_rekordbox_save(False)
