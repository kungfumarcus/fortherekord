"""
E2E test for playlist synchronization workflow.

Tests the complete workflow from command line execution to verify the sync functionality.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "tests" / "e2e"))
from conftest import (
    run_fortherekord_command,
    test_environment_with_dump_file,
    temporary_config_file,
)


def test_e2e_spotify_playlist_sync_invalid_credentials(
    test_environment_with_dump_file, temporary_config_file
):
    """Test playlist sync command when Spotify credentials are invalid."""

    config_content = """
rekordbox_library_path: "{dump_path}"
spotify_client_id: "invalid_client_id_12345"
spotify_client_secret: "invalid_client_secret_67890"
"""

    dump_path, test_env = test_environment_with_dump_file
    # Convert Windows paths to use forward slashes for YAML compatibility
    dump_path_yaml = dump_path.replace("\\", "/")
    config_path = temporary_config_file(config_content.format(dump_path=dump_path_yaml))

    # Add config path to test environment
    test_env["FORTHEREKORD_CONFIG_PATH"] = config_path

    # Run the main command - should fail gracefully with invalid Spotify credentials
    result = run_fortherekord_command([], env_vars=test_env)

    # Should handle invalid Spotify credentials gracefully
    assert (
        "Invalid client" in result.stdout
        or "Authentication failed" in result.stdout
        or "Error" in result.stdout
        or "401" in result.stdout  # HTTP 401 Unauthorized
        or result.returncode != 0  # Expected to fail
    )
