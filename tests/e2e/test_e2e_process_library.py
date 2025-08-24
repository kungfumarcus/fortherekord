"""
End-to-end test for ForTheRekord metadata processing workflow.

Tests the complete metadata processing workflow with database safety mechanisms.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "tests" / "e2e"))
from conftest import e2e_harness


def test_e2e_process_library(e2e_harness):
    """Test the complete metadata processing workflow with database safety."""

    # Configure the test to enable music library processing features
    e2e_harness.update_config({"spotify": None})

    # Run the main command - database writes will be captured in JSON dump
    result = e2e_harness.run()
    
    e2e_harness.assert_process_succeeded(True)
    e2e_harness.assert_rekordbox_loaded(True)
    e2e_harness.assert_processor_ran(True)
    e2e_harness.assert_spotify_synced(False)
    e2e_harness.assert_rekordbox_save(True)