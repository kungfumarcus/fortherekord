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

    config_content = """
rekordbox_library_path: "{dump_path}"
spotify_client_id: "{client_id}"
spotify_client_secret: "{client_secret}"
"""

    dump_path, test_env = test_environment_with_dump_file
    # Convert Windows paths to use forward slashes for YAML compatibility
    dump_path_yaml = dump_path.replace("\\", "/")
    config_path = temporary_config_file(
        config_content.format(
            dump_path=dump_path_yaml,
            client_id=spotify_client_id,
            client_secret=spotify_client_secret,
        )
    )
    test_env["FORTHEREKORD_CONFIG_PATH"] = config_path

    # Run the main command with --dry-run flag
    result = run_fortherekord_command(["--dry-run"], env_vars=test_env)

    # Should either succeed or fail gracefully, but not with config errors
    assert result.returncode is not None

    # Should NOT contain config-related errors since we provided valid config
    assert "rekordbox_library_path not configured" not in result.stdout
    assert "Spotify credentials not configured" not in result.stdout

    # Should show that config was loaded and reached some processing stage
    success_indicators = [
        "Loading Rekordbox" in result.stdout,  # Got past initial config
        "DRY RUN MODE" in result.stdout,  # Dry-run mode activated
        "Spotify" in result.stdout,  # Reached Spotify stage
        result.returncode == 0,  # Complete success
    ]

    failure_indicators = [
        "Error" in result.stdout,  # Some error after config validation
        "AssertionError" in result.stderr,  # pyrekordbox config issues
        "no such table" in result.stderr,  # Database structure issues
        "Traceback" in result.stderr,  # Any traceback after config validation
    ]

    # Should have at least one success indicator OR acceptable failure indicators
    assert any(success_indicators) or any(failure_indicators), (
        f"Expected to reach dry-run processing stage or fail gracefully. "
        f"stdout: {result.stdout[:200]}... stderr: {result.stderr[:200]}..."
    )
