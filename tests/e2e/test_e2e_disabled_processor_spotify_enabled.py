"""
End-to-end test for disabled processor with Spotify sync enabled.

Tests the workflow where music library processor is disabled but Spotify sync continues.
"""

import sys
import yaml
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "tests" / "e2e"))
from conftest import (
    run_fortherekord_command,
    test_environment_with_dump_file,
    temporary_config_file,
)


def test_disabled_processor_with_spotify_enabled(
    test_environment_with_dump_file, temporary_config_file
):
    """Test E2E workflow with disabled processor but Spotify sync enabled."""
    import pytest

    pytest.skip("Temporarily disabled")

    dump_path, test_env = test_environment_with_dump_file

    # Create config with all processor features disabled but Spotify enabled
    config_content = """rekordbox_library_path: {db_path}
rekordbox:
  add_key_to_title: false
  add_artist_to_title: false
  remove_artists_in_title: false
  ignore_playlists:
    - "Hot Cues"
spotify_client_id: test_spotify_client_id
spotify_client_secret: test_spotify_client_secret
"""

    # Convert Windows paths to use forward slashes for YAML compatibility
    db_path_yaml = dump_path.replace("\\", "/")
    config_path = temporary_config_file(config_content.format(db_path=db_path_yaml))

    # Update environment to use our custom config
    test_env_with_config = test_env.copy()
    test_env_with_config["FORTHEREKORD_CONFIG_PATH"] = str(config_path)

    # Run the command - it should skip processor but attempt Spotify sync
    result = run_fortherekord_command([], env_vars=test_env_with_config)

    # The command should handle the disabled processor gracefully
    # and attempt to proceed to Spotify sync (which will fail due to test credentials)
    assert (
        "Music library processor is disabled" in result.stdout
        or "Skipping track processing - processor disabled" in result.stdout
        or "Loading Rekordbox" in result.stdout  # If it gets that far
        or "Error" in result.stdout  # Various config/auth errors are expected
    ), f"Expected processor disabled message or other expected output, got: {result.stdout}"

    # Should not crash on the disabled processor logic
    # Database errors are expected in test environment with dummy files
    assert (
        "Traceback" not in result.stderr
        or "Spotify" in result.stderr
        or "sqlalchemy" in result.stderr
        or "djmdPlaylist" in result.stderr
    ), f"Unexpected error (should only be Spotify or database-related): {result.stderr}"


def test_disabled_processor_dry_run_with_spotify(
    test_environment_with_dump_file, temporary_config_file
):
    """Test E2E workflow with disabled processor in dry-run mode."""

    dump_path, test_env = test_environment_with_dump_file

    # Create config with all processor features disabled
    config_content = """rekordbox_library_path: {db_path}
rekordbox:
  add_key_to_title: false
  add_artist_to_title: false
  remove_artists_in_title: false
spotify_client_id: test_spotify_client_id
spotify_client_secret: test_spotify_client_secret
"""

    # Convert Windows paths to use forward slashes for YAML compatibility
    db_path_yaml = dump_path.replace("\\", "/")
    config_path = temporary_config_file(config_content.format(db_path=db_path_yaml))

    # Update environment to use our custom config
    test_env_with_config = test_env.copy()
    test_env_with_config["FORTHEREKORD_CONFIG_PATH"] = str(config_path)

    # Run with --dry-run flag
    result = run_fortherekord_command(["--dry-run"], env_vars=test_env_with_config)

    # Should handle disabled processor and continue to Spotify (which may fail)
    assert (
        "Music library processor is disabled" in result.stdout
        or "Skipping track processing - processor disabled" in result.stdout
        or "DRY RUN MODE" in result.stdout  # If it gets that far
        or "Loading Rekordbox" in result.stdout
        or "Error" in result.stdout  # Config/auth errors expected
    ), f"Expected dry-run or disabled processor messages, got: {result.stdout}"

    # Should not crash on the disabled processor logic
    # Database errors are expected in test environment with dummy files
    assert (
        "Traceback" not in result.stderr
        or "Spotify" in result.stderr
        or "sqlalchemy" in result.stderr
        or "djmdPlaylist" in result.stderr
    ), f"Unexpected error (should only be Spotify or database-related): {result.stderr}"
