"""
E2E test for Spotify sync workflow in dry-run mode.

Tests the complete workflow with --dry-run flag to verify preview functionality.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "tests" / "e2e"))
from conftest import e2e_harness


def test_e2e_spotify_sync_dry_run(e2e_harness):
    """Test Spotify sync command with --dry-run flag."""
    import pytest

    # Disable processor for this test - focus on Spotify sync only
    e2e_harness.update_config({
        "processor": None  # Remove processor config to disable it
    })
    
    # Run the main command with --dry-run flag
    result = e2e_harness.run(["--dry-run"])

    # Should complete successfully in dry-run mode  
    e2e_harness.assert_process_succeeded(True)
    e2e_harness.assert_rekordbox_loaded(True)
    e2e_harness.assert_processor_ran(False)
    e2e_harness.assert_spotify_synced(True, dry_run=True)
    e2e_harness.assert_rekordbox_save(False)
