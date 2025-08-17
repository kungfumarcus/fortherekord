"""
CRITICAL: Database Safety Tests - Must Run First

These tests MUST pass before any other tests run to ensure database safety.
Test file is named with 000_ prefix to ensure it runs first alphabetically.
"""

import os
import pytest


class TestDatabaseSafetyFirst:
    """Critical database safety tests that must pass before anything else."""

    def test_000_test_mode_is_enabled(self):
        """CRITICAL: Verify test mode is enabled to prevent database commits."""
        test_mode = os.getenv("FORTHEREKORD_TEST_MODE", "")
        
        if test_mode != "1":
            pytest.fail(
                f"CRITICAL FAILURE: FORTHEREKORD_TEST_MODE is '{test_mode}', expected '1'. "
                "Database commits are NOT SAFE! Tests must not run without test mode enabled."
            )
    
    def test_001_test_dump_file_is_configured(self):
        """CRITICAL: Verify test dump file is configured."""
        dump_file = os.getenv("FORTHEREKORD_TEST_DUMP_FILE", "")
        
        if not dump_file:
            pytest.fail(
                "CRITICAL FAILURE: FORTHEREKORD_TEST_DUMP_FILE is not set. "
                "Database safety dump mechanism is not configured!"
            )
    
    def test_002_database_safety_mechanism_works(self):
        """CRITICAL: Verify the database safety mechanism prevents commits."""
        from unittest.mock import Mock
        from fortherekord.rekordbox_library import RekordboxLibrary
        
        # Test that save_changes never calls commit in test mode
        mock_db = Mock()
        library = RekordboxLibrary("/test/db.edb")
        library._db = mock_db
        
        # This should NOT call commit due to test mode
        result = library.save_changes()
        
        # Verify it succeeded but never called commit
        assert result is True, "save_changes should succeed in test mode"
        mock_db.commit.assert_not_called(), "CRITICAL: Database commit was called during test mode!"


# If any of these tests fail, we want to stop immediately
# This ensures database safety before running any other tests
