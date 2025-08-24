"""
E2E test for Spotify sync workflow in dry-run mode.

Tests the complete workflow with --dry-run flag to verify preview functionality.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "tests" / "e2e"))
from conftest import e2e_harness


def test_e2e_process_library_spotify_sync_dry_run(e2e_harness):
    """Test Spotify sync command with --dry-run flag."""
    import pytest

    # Run the main command with --dry-run flag
    result = e2e_harness.run(["--dry-run"])

    # Should complete successfully in dry-run mode
    assert "DRY RUN MODE" in result.stdout
    
    # Should have loaded Rekordbox, processor disabled, and Spotify credentials missing
    e2e_harness.assert_process_succeeded(True)
    e2e_harness.assert_rekordbox_loaded(True)
    e2e_harness.assert_processor_ran(True)
    e2e_harness.assert_spotify_synced(True)
    e2e_harness.assert_rekordbox_save(False)