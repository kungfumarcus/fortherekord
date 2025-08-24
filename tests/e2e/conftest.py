"""
E2E Test Configuration and Fixtures

Centralized configuration for end-to-end tests.
"""

import pytest
import subprocess
import sys
import os
import tempfile
from pathlib import Path


def pytest_configure(config):
    """Configure pytest for e2e tests."""
    # Set timeout for all e2e tests
    config.option.timeout = 30


# Configure E2E test timeout globally for this module
pytestmark = [pytest.mark.e2e, pytest.mark.timeout(30)]  # All E2E tests get 30 second timeout


def run_fortherekord_command(args: list[str], env_vars: dict = None) -> subprocess.CompletedProcess:
    """
    Helper function to run fortherekord CLI commands as a subprocess.

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

    print()
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent,  # Run from project root
            env=env,
            timeout=15,  # 15 second timeout for debugging
        )
    except subprocess.TimeoutExpired as e:
        print("=== E2E TEST TIMEOUT DEBUG INFO ===")
        print(f"Command: {' '.join(e.cmd)}")
        print(f"Timeout: 15 seconds")
        print("=== STDOUT BEFORE TIMEOUT ===")
        print(e.stdout or "(no stdout)")
        print("=== STDERR BEFORE TIMEOUT ===")
        print(e.stderr or "(no stderr)")
        print("=== END DEBUG INFO ===")
        pytest.fail(f"E2E test timed out after 15 seconds")
    
    # Print output for debugging while still capturing it
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    
    return result


def load_test_credentials():
    """Load Spotify credentials for testing."""
    import yaml
    
    # Load from test-credentials.yaml in the same directory as conftest.py
    credentials_path = Path(__file__).parent / "test-credentials.yaml"
    if not credentials_path.exists():
        raise FileNotFoundError(f"Test credentials file not found at {credentials_path}")
    
    with open(credentials_path, 'r') as f:
        config = yaml.safe_load(f)
    
    spotify_config = config.get("spotify", {})
    if not spotify_config.get("client_id") or not spotify_config.get("client_secret"):
        raise ValueError("Spotify credentials not found in test-credentials.yaml")
    
    return {
        "client_id": spotify_config.get("client_id"),
        "client_secret": spotify_config.get("client_secret")
    }


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
        spotify_creds = load_test_credentials()
        
        return {
            "rekordbox": {
                "library_path": "C:/Users/Marcus.Lund/AppData/Roaming/Pioneer/rekordbox/master.db"
            },
            "processor": {
                "add_key_to_title": True,
                "add_artist_to_title": True,
                "remove_artists_in_title": True
            },
            "spotify": {
                "enabled": True,
                "client_id": spotify_creds["client_id"],
                "client_secret": spotify_creds["client_secret"],
                "playlist_sync": {
                    "enabled": True
                }
            }
        }
    
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
                elif key in base_dict and isinstance(base_dict[key], dict) and isinstance(value, dict):
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
        """Verify that the JSON dump file was created and contains valid JSON."""
        dump_data = self.read_dump_json()
        if dump_data is not None:
            assert isinstance(dump_data, (dict, list)), "Dump should contain valid JSON structure"
        if expected:
            assert dump_data is not None, "No Rekordbox save detected"
        else:
            assert dump_data is None, "Unexpected Rekordbox save detected"  
    
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
            success: True if command should have succeeded (returncode 0), False if should have failed
        """
        if self._last_result is None:
            raise ValueError("Must call run() before using assertions")
            
        if expected:
            assert self._last_result.returncode == 0, f"Expected success but got returncode {self._last_result.returncode}"
        else:
            assert self._last_result.returncode != 0, f"Expected failure but got returncode {self._last_result.returncode}"
    
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
        
        if expected:
            if dry_run:
                assert "DRY RUN MODE" in stdout, f"Expected DRY RUN MODE message, but not found in output: {stdout}"
            assert "Processing playlist metadata" in stdout, f"Expected processor to run, but not found in output: {stdout}"
        else:
            assert "Skipping track processing" in stdout, f"Expected processor to be disabled, but not found in output: {stdout}"
    
    def assert_rekordbox_loaded(self, expected: bool):
        """
        Assert that Rekordbox library loaded successfully or failed as expected.
        
        Args:
            success: True if Rekordbox should have loaded successfully, False if should have failed
        """
        if self._last_result is None:
            raise ValueError("Must call run() before using assertions")
            
        stdout = self._last_result.stdout or ""
        
        if expected:
            assert "Loading Rekordbox library" in stdout, f"Expected Rekordbox to load successfully, but not found in output: {stdout}"
        else:
            assert "Error loading Rekordbox library" in stdout, f"Expected Rekordbox to fail loading, but not found in output: {stdout}"
    
    def assert_spotify_synced(self, expected: bool, dry_run: bool = False):
        """
        Assert that Spotify integration ran or failed as expected.
        
        Args:
            expected: True if Spotify should have succeeded, False if should have failed/been skipped
            dry_run: True if running in dry-run mode
        """
        if self._last_result is None:
            raise ValueError("Must call run() before using assertions")
            
        stdout = self._last_result.stdout or ""
        
        if expected:
            if dry_run:
                assert "DRY RUN MODE - Previewing changes without making them" in stdout, f"Expected Spotify dry run message, but not found in output: {stdout}"
            assert "Authenticated with Spotify as user:" in stdout, f"Expected Spotify authentication success, but not found in output: {stdout}"
        else:
            assert "Spotify credentials not configured" in stdout, f"Expected Spotify to be skipped/failed, but not found in output: {stdout}"
    
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



