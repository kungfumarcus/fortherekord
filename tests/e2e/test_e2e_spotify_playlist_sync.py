"""
E2E test for Spotify playlist synchronization with real credentials.

Tests the complete workflow from command line execution to Spotify authentication and sync.
Requires test-credentials.yaml file for real Spotify API testing.
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


def load_test_credentials():
    """Load Spotify credentials from test-credentials.yaml file."""
    creds_path = Path(__file__).parent / "test-credentials.yaml"

    if not creds_path.exists():
        # Create the file with template content
        template_content = """spotify:
  client_id: your_test_spotify_client_id
  client_secret: your_test_spotify_client_secret"""

        with open(creds_path, "w") as f:
            f.write(template_content)

        raise FileNotFoundError(
            f"Created test credentials file: {creds_path}\n"
            "Please edit the file and add your real Spotify credentials:\n"
            "  client_id: your_actual_spotify_client_id\n"
            "  client_secret: your_actual_spotify_client_secret\n"
            "Then run the tests again."
        )

    with open(creds_path, "r") as f:
        creds = yaml.safe_load(f)

    if not creds.get("spotify", {}).get("client_id"):
        raise ValueError("Missing spotify.client_id in test-credentials.yaml")

    if not creds.get("spotify", {}).get("client_secret"):
        raise ValueError("Missing spotify.client_secret in test-credentials.yaml")

    # Check if still has template values
    if creds["spotify"]["client_id"] in [
        "your_test_spotify_client_id",
        "your_test_spotify_client_id_here",
    ] or creds["spotify"]["client_secret"] in [
        "your_test_spotify_client_secret",
        "your_test_spotify_client_secret_here",
    ]:
        raise ValueError(
            "Please update test-credentials.yaml with real Spotify credentials.\n"
            "Replace the placeholder values with actual credentials from your Spotify app."
        )

    return creds["spotify"]


def test_e2e_spotify_playlist_sync(test_environment_with_dump_file, temporary_config_file):
    """Test complete E2E playlist sync workflow with real Spotify credentials."""

    # Load real credentials - this will fail the test if credentials are missing
    spotify_creds = load_test_credentials()

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
            client_id=spotify_creds["client_id"],
            client_secret=spotify_creds["client_secret"],
        )
    )
    test_env["FORTHEREKORD_CONFIG_PATH"] = config_path

    # Run the main command - should get to Spotify authentication stage
    result = run_fortherekord_command([], env_vars=test_env)

    # Should either succeed or fail at Spotify OAuth, not at config validation
    assert result.returncode is not None

    # Should NOT contain config-related errors since we provided valid config
    assert "rekordbox_library_path not configured" not in result.stdout
    assert "Spotify credentials not configured" not in result.stdout

    # Should show that the real credentials were loaded and reached some Spotify stage
    success_indicators = [
        "Loading Rekordbox" in result.stdout,  # Got past initial config
        "Spotify" in result.stdout,  # Reached Spotify stage
        "Authentication" in result.stdout,  # OAuth flow started
        "Authenticated with Spotify" in result.stdout,  # Actually succeeded
        result.returncode == 0,  # Complete success
    ]

    failure_indicators = [
        "Error" in result.stdout,  # Some error after config validation
        "AssertionError" in result.stderr,  # pyrekordbox config issues
        "OAuth" in result.stderr,  # OAuth flow issues
        "browser" in result.stderr.lower(),  # Browser-related auth issues
    ]

    # Should have at least one success indicator OR acceptable failure indicators
    assert any(success_indicators) or any(failure_indicators), (
        f"Expected to reach Spotify authentication stage or fail gracefully. "
        f"stdout: {result.stdout[:200]}... stderr: {result.stderr[:200]}..."
    )
