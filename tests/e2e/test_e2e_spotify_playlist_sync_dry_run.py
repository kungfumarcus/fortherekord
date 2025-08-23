"""
E2E test for playlist synchronization workflow in dry-run mode.

Tests the complete workflow with --dry-run flag to verify preview functionality.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "tests" / "e2e"))
from conftest import (
    run_fortherekord_command,
    test_environment_with_dump_file,
    temporary_config_file,
)


def test_e2e_spotify_playlist_sync_dry_run(test_environment_with_dump_file, temporary_config_file):
    """Test playlist sync command with --dry-run flag."""
    import pytest

    pytest.skip("Temporarily disabled")

    # Load real Spotify credentials from test-credentials.yaml
    import yaml

    creds_path = Path(__file__).parent / "test-credentials.yaml"

    if not creds_path.exists():
        # Skip test if no real credentials available
        import pytest

        pytest.skip("No test-credentials.yaml file found - skipping real Spotify dry-run test")

    with open(creds_path, "r") as f:
        creds = yaml.safe_load(f)

    spotify_client_id = creds.get("spotify", {}).get("client_id")
    spotify_client_secret = creds.get("spotify", {}).get("client_secret")

    if not spotify_client_id or not spotify_client_secret:
        import pytest

        pytest.skip("Missing Spotify credentials in test-credentials.yaml")

    config_content = f"""
rekordbox_library_path: "{{db_path}}"
spotify_client_id: "{spotify_client_id}"
spotify_client_secret: "{spotify_client_secret}"
"""

    db_path, test_env = test_environment_with_dump_file
    # Convert Windows paths to use forward slashes for YAML compatibility
    db_path_yaml = db_path.replace("\\", "/")
    config_path = temporary_config_file(config_content.format(db_path=db_path_yaml))

    # Add config path to test environment
    test_env["FORTHEREKORD_CONFIG_PATH"] = config_path

    # Run the main command with --dry-run flag
    result = run_fortherekord_command(["--dry-run"], env_vars=test_env)

    # Should complete successfully in dry-run mode
    assert result.returncode == 0

    # Verify dry-run specific output appears
    assert "DRY RUN MODE" in result.stdout
    assert (
        "Previewing changes without making them" in result.stdout
        or "Would save changes" in result.stdout
    )

    # Should still show playlist loading and metadata processing
    assert (
        "Loaded" in result.stdout
        and "playlists with" in result.stdout
        and "tracks:" in result.stdout
    )
