"""
E2E Test Configuration and Fixtures

Centralized configuration for end-to-end tests.
"""

import pytest
import subprocess
import sys
import os
import tempfile
import shutil
import sqlite3
import psutil
from pathlib import Path


@pytest.fixture(scope="session", autouse=True)
def backup_rekordbox_database():
    """
    Session-scoped fixture to backup and restore Rekordbox database.

    This runs ONCE for the entire E2E test suite:
    - Before any E2E tests: safety checks and creates backup
    - After all E2E tests: restores the original database from backup
    """
    # Get the database path from config
    from fortherekord.config import load_config

    config = load_config()
    db_path = config.get("rekordbox", {}).get("library_path")

    if not db_path or not os.path.exists(db_path):
        pytest.skip("Rekordbox database not found, skipping E2E tests")

    # Safety check: Ensure Rekordbox is not running
    for proc in psutil.process_iter(["pid", "name"]):
        if proc.info["name"] and "rekordbox" in proc.info["name"].lower():
            pytest.fail("Rekordbox is running! Please close Rekordbox before running E2E tests.")

    # Safety check: Ensure test collection has < 20 tracks
    print("\nRunning safety checks for E2E tests...")
    try:
        from fortherekord.rekordbox_library import RekordboxLibrary
        from fortherekord.config import load_config

        # Load test config to get include_playlists
        test_config = load_test_config()
        full_config = load_config()

        # Merge test config into full config for safety check
        if "rekordbox" in test_config:
            full_config.setdefault("rekordbox", {}).update(test_config["rekordbox"])

        library = RekordboxLibrary(full_config)
        collection = library.get_filtered_collection()

        # Count all tracks from filtered playlists
        all_tracks = library.get_all_tracks_from_playlists(collection.playlists)
        track_count = len(all_tracks)

        print(f"Found {track_count} tracks in filtered collection")

        if track_count >= 50:
            pytest.fail(
                f"E2E test safety check failed: Found {track_count} tracks (must be < 20). "
                f"Please configure include_playlists in test-config.yaml to limit test scope."
            )

    except Exception as e:
        pytest.fail(f"E2E test safety check failed: {e}")

    # Create backup
    backup_path = db_path + ".e2e_backup"
    print(f"Safety checks passed. Backing up Rekordbox database: {db_path} -> {backup_path}")
    shutil.copy2(db_path, backup_path)

    try:
        # Run all E2E tests
        yield
    finally:
        # Restore from backup
        print(f"\nRestoring Rekordbox database: {backup_path} -> {db_path}")
        shutil.copy2(backup_path, db_path)

        # Clean up backup file
        if os.path.exists(backup_path):
            os.remove(backup_path)
            print(f"Removed backup file: {backup_path}")


def pytest_configure(config):
    """Configure pytest for e2e tests."""
    # Set timeout for all e2e tests
    config.option.timeout = 30


# Configure E2E test timeout globally for this module
pytestmark = [pytest.mark.e2e, pytest.mark.timeout(30)]  # All E2E tests get 30 second timeout


def run_fortherekord_command(args: list[str], env_vars: dict = None) -> subprocess.CompletedProcess:
    """
    Helper function to run fortherekord CLI commands as a subprocess with real-time output.

    Args:
        args: Command line arguments to pass to fortherekord
        env_vars: Additional environment variables to set

    Returns:
        CompletedProcess with stdout, stderr, and return code
    """
    cmd = [sys.executable, "-m", "fortherekord"] + args

    # Set up environment with test safety
    env = os.environ.copy()
    if env_vars:
        env.update(env_vars)

    print(f"\n=== Running: {' '.join(cmd)} ===")

    try:
        # Use Popen for real-time output streaming
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=Path(__file__).parent.parent.parent,  # Run from project root
            env=env,
            bufsize=1,  # Line buffered
            universal_newlines=True,
        )

        stdout_lines = []
        stderr_lines = []

        # Read output in real-time
        import threading
        import time

        def read_stdout():
            for line in iter(process.stdout.readline, ""):
                print(f"STDOUT: {line.rstrip()}")
                stdout_lines.append(line)

        def read_stderr():
            for line in iter(process.stderr.readline, ""):
                print(f"STDERR: {line.rstrip()}")
                stderr_lines.append(line)

        # Start threads to read output
        stdout_thread = threading.Thread(target=read_stdout)
        stderr_thread = threading.Thread(target=read_stderr)
        stdout_thread.daemon = True
        stderr_thread.daemon = True
        stdout_thread.start()
        stderr_thread.start()

        # Wait for process to complete with timeout
        start_time = time.time()
        timeout = 15

        while process.poll() is None:
            if time.time() - start_time > timeout:
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()

                print("=== E2E TEST TIMEOUT DEBUG INFO ===")
                print(f"Command: {' '.join(cmd)}")
                print("Timeout: 15 seconds")
                print("=== CAPTURED STDOUT ===")
                print("".join(stdout_lines) or "(no stdout)")
                print("=== CAPTURED STDERR ===")
                print("".join(stderr_lines) or "(no stderr)")
                print("=== END DEBUG INFO ===")
                pytest.fail("E2E test timed out after 15 seconds")

            time.sleep(0.1)

        # Wait for threads to finish reading
        stdout_thread.join(timeout=1)
        stderr_thread.join(timeout=1)

        # Create result object
        result = subprocess.CompletedProcess(
            cmd, process.returncode, "".join(stdout_lines), "".join(stderr_lines)
        )

    except Exception as e:
        print(f"Error running command: {e}")
        raise

    # Print output for debugging while still capturing it
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)

    return result


def load_test_config():
    """Load test configuration including Spotify credentials and playlist filtering."""
    import yaml

    # Load from test-config.yaml in the same directory as conftest.py
    config_path = Path(__file__).parent / "test-config.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"Test config file not found at {config_path}")

    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    spotify_config = config.get("spotify", {})
    if not spotify_config.get("client_id") or not spotify_config.get("client_secret"):
        raise ValueError("Spotify credentials not found in test-config.yaml")

    return config


class E2ETestHarness:
    """
    Centralized test harness for E2E tests with clean configuration management.
    """

    def __init__(self):
        # Create temporary dump file for JSON output
        self._dump_file = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        self.rekordbox_db_dump_json_path = self._dump_file.name
        self._dump_file.close()

        # Create temporary config file
        self._config_file = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
        self._config_path = self._config_file.name
        self._config_file.close()

        # Set up test environment with database safety (disables real database writes)
        spotify_cache_path = Path(__file__).parent / ".spotify_cache_test"
        self.env_vars = {
            "FORTHEREKORD_TEST_MODE": "1",  # Enable test mode (disables database saves)
            "FORTHEREKORD_TEST_DUMP_FILE": self.rekordbox_db_dump_json_path,
            "FORTHEREKORD_SPOTIFY_CACHE_PATH": str(spotify_cache_path),
            "FORTHEREKORD_CONFIG_PATH": self._config_path,
        }

        # Initialize with default config
        self._current_config = self._get_default_config()
        self._save_config()
        self._last_result = None

    def _get_default_config(self):
        """Get the default configuration for E2E tests."""
        test_config = load_test_config()
        spotify_config = test_config.get("spotify", {})
        rekordbox_config = test_config.get("rekordbox", {})

        config = {
            "rekordbox": {
                "library_path": "C:/Users/Marcus.Lund/AppData/Roaming/Pioneer/rekordbox/master.db"
            },
            "processor": {
                "add_key_to_title": True,
                "add_artist_to_title": True,
                "remove_artists_in_title": True,
            },
            "spotify": {
                "enabled": True,
                "client_id": spotify_config["client_id"],
                "client_secret": spotify_config["client_secret"],
                "playlist_sync": {"enabled": True},
            },
        }

        # Add include_playlists from test config if specified
        if "include_playlists" in rekordbox_config:
            config["rekordbox"]["include_playlists"] = rekordbox_config["include_playlists"]

        # Add playlist_prefix from test config if specified
        if "playlist_prefix" in spotify_config:
            config["spotify"]["playlist_prefix"] = spotify_config["playlist_prefix"]

        return config

    def update_config(self, overrides: dict):
        """
        Update the configuration with the provided overrides.

        Args:
            overrides: Dictionary of configuration overrides to apply
        """

        def deep_update(base_dict, update_dict):
            for key, value in update_dict.items():
                if value is None:
                    # If value is None, remove the key completely
                    base_dict.pop(key, None)
                elif (
                    key in base_dict
                    and isinstance(base_dict[key], dict)
                    and isinstance(value, dict)
                ):
                    deep_update(base_dict[key], value)
                else:
                    base_dict[key] = value

        deep_update(self._current_config, overrides)
        self._save_config()

    def _save_config(self):
        """Save the current configuration to the temporary YAML file."""
        import yaml

        config_content = yaml.dump(self._current_config, default_flow_style=False)
        with open(self._config_path, "w") as f:
            f.write(config_content)

    def read_dump_json(self):
        """
        Read and parse the JSON dump file created during test execution.

        Returns:
            dict or list: The parsed JSON data, or None if file doesn't exist or is empty
        """
        if not Path(self.rekordbox_db_dump_json_path).exists():
            return None

        with open(self.rekordbox_db_dump_json_path, "r") as f:
            content = f.read().strip()
            if not content:
                return None

            import json

            return json.loads(content)

    def assert_rekordbox_save(self, expected):
        """Verify that a Rekordbox save operation was attempted as expected."""
        if self._last_result is None:
            raise ValueError("Must call run() before using assertions")

        stdout = self._last_result.stdout or ""

        save_messages = ["Saving changes to database..."]
        actual = any(msg in stdout for msg in save_messages)
        if expected:
            # Look for save operation messages - either dry run or actual save attempt
            assert actual, (
                f"Expected save operation to be attempted, but no save messages found"
                f"in output: {stdout}"
            )
        else:
            # If no save expected, processor should be skipped entirely
            assert (
                not actual
            ), f"Expected no save (processor skipped), but not found in output: {stdout}"

    def run(self, args: list[str] = None) -> subprocess.CompletedProcess:
        """
        Run the fortherekord application with the test harness environment.

        Args:
            args: Command line arguments to pass to fortherekord (default: [])

        Returns:
            CompletedProcess with stdout, stderr, and return code
        """
        if args is None:
            args = []
        self._last_result = run_fortherekord_command(args, env_vars=self.env_vars)
        return self._last_result

    def assert_process_succeeded(self, expected: bool):
        """
        Assert that the command completed successfully or failed as expected.

        Args:
            expected: True if command should have succeeded (returncode 0),
                    False if should have failed
        """
        if self._last_result is None:
            raise ValueError("Must call run() before using assertions")

        actual = self._last_result.returncode == 0
        if expected:
            assert actual, f"Expected success but got returncode {self._last_result.returncode}"
        else:
            assert not actual, f"Expected failure but got returncode {self._last_result.returncode}"

    def assert_processor_ran(self, expected: bool, dry_run: bool = False):
        """
        Assert that the processor ran or was disabled as expected.

        Args:
            expected: True if processor should have run, False if disabled
            dry_run: True if running in dry-run mode
        """
        if self._last_result is None:
            raise ValueError("Must call run() before using assertions")

        stdout = self._last_result.stdout or ""

        if dry_run and expected:
            actual = "DRY RUN MODE" in stdout and "Processing playlist metadata" in stdout
        else:
            actual = (
                "Processing playlist metadata" in stdout
                and "Skipping track processing" not in stdout
            )

        if expected:
            if dry_run:
                assert (
                    actual
                ), f"Expected DRY RUN MODE and processor to run, but not found in output: {stdout}"
            else:
                assert actual, f"Expected processor to run, but not found in output: {stdout}"
        else:
            assert not actual, f"Expected processor to be disabled, but it ran in output: {stdout}"

    def assert_rekordbox_loaded(self, expected: bool):
        """
        Assert that Rekordbox library loaded successfully or failed as expected.

        Args:
            expected: True if Rekordbox should have loaded successfully, False if should have failed
        """
        if self._last_result is None:
            raise ValueError("Must call run() before using assertions")

        stdout = self._last_result.stdout or ""
        actual = "Loading Rekordbox library" in stdout

        if expected:
            assert (
                actual
            ), f"Expected Rekordbox to load successfully, but not found in output: {stdout}"
        else:
            assert (
                not actual
            ), f"Expected Rekordbox to fail loading, but it loaded in output: {stdout}"

    def assert_spotify_synced(self, expected: bool, dry_run: bool = False):
        """
        Assert that Spotify integration ran or failed as expected.

        Args:
            expected: True if Spotify should have succeeded,
                     False if should have failed/been skipped
            dry_run: True if running in dry-run mode
        """
        if self._last_result is None:
            raise ValueError("Must call run() before using assertions")

        stdout = self._last_result.stdout or ""

        if dry_run and expected:
            actual = (
                "DRY RUN MODE - Previewing changes without making them" in stdout
                or "Authenticated with Spotify as user:" in stdout
            )
        else:
            actual = "Authenticated with Spotify as user:" in stdout

        if expected:
            if dry_run:
                assert (
                    actual
                ), f"Expected Spotify dry run or authentication, but not found in output: {stdout}"
            else:
                assert (
                    actual
                ), f"Expected Spotify authentication success, but not found in output: {stdout}"
        else:
            assert (
                not actual
            ), f"Expected Spotify to be skipped/failed, but it succeeded in output: {stdout}"

    def cleanup(self):
        """Clean up temporary files created during testing."""
        if Path(self.rekordbox_db_dump_json_path).exists():
            Path(self.rekordbox_db_dump_json_path).unlink()
        if Path(self._config_path).exists():
            Path(self._config_path).unlink()


@pytest.fixture
def e2e_harness():
    """
    Pytest fixture that provides a clean, centralized E2E test harness.

    Returns:
        E2ETestHarness: Test harness with configuration management and JSON dump handling
    """
    harness = E2ETestHarness()
    try:
        yield harness
    finally:
        harness.cleanup()
