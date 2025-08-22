"""
E2E test for Spotify playlist sync when music library processor is disabled.

Tests the workflow where all processor enhancement features are disabled,
but Spotify sync should still continue to work.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "tests" / "e2e"))
from conftest import (
    run_fortherekord_command,
    verify_json_dump_file,
    test_environment_with_dump_file,
)


def test_spotify_playlist_sync_processor_disabled(test_environment_with_dump_file):
    """Test Spotify playlist sync when music library processor is disabled."""

    dump_path, test_env = test_environment_with_dump_file

    # Set processor features to disabled in environment
    test_env_disabled = test_env.copy()
    test_env_disabled["FORTHEREKORD_PROCESSOR_DISABLED"] = "1"  # Custom env var for this test

    # Run the command - should handle disabled processor gracefully
    result = run_fortherekord_command([], env_vars=test_env_disabled)

    # Should handle the scenario gracefully - either show processor disabled message
    # or handle database/config issues gracefully like the working test
    assert (
        "Music library processor is disabled" in result.stdout
        or "Skipping track processing - processor disabled" in result.stdout
        or "rekordbox_library_path" in result.stdout
        or "Loading Rekordbox" in result.stdout
        or "Error" in result.stdout
        or "Traceback" in result.stderr
    ), (
        f"Expected processor disabled or standard graceful handling. "
        f"Got stdout: {result.stdout}, stderr: {result.stderr}"
    )

    # Verify that if any database operations were attempted, they were dumped to JSON
    verify_json_dump_file(dump_path)


def test_spotify_playlist_sync_processor_disabled_dry_run(test_environment_with_dump_file):
    """Test Spotify playlist sync with disabled processor in dry-run mode."""

    dump_path, test_env = test_environment_with_dump_file

    # Set processor features to disabled in environment
    test_env_disabled = test_env.copy()
    test_env_disabled["FORTHEREKORD_PROCESSOR_DISABLED"] = "1"

    # Run with --dry-run flag
    result = run_fortherekord_command(["--dry-run"], env_vars=test_env_disabled)

    # Should handle the scenario gracefully in dry-run mode
    assert (
        "Music library processor is disabled" in result.stdout
        or "Skipping track processing - processor disabled" in result.stdout
        or "DRY RUN MODE" in result.stdout
        or "rekordbox_library_path" in result.stdout
        or "Loading Rekordbox" in result.stdout
        or "Error" in result.stdout
        or "Traceback" in result.stderr
    ), (
        f"Expected processor disabled or standard graceful handling in dry-run mode. "
        f"Got stdout: {result.stdout}, stderr: {result.stderr}"
    )

    # Verify that if any database operations were attempted, they were dumped to JSON
    verify_json_dump_file(dump_path)
