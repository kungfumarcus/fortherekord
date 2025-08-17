"""
Tests for main CLI functionality.

Tests the basic CLI shell with help and version commands.
"""

import pytest
import click
from click.testing import CliRunner
from unittest.mock import patch, MagicMock

from fortherekord.main import cli


# Helper functions to reduce repetition
def run_cli_command(args: list[str]) -> object:
    """Helper function to run CLI commands and return result."""
    runner = CliRunner()
    return runner.invoke(cli, args)


def assert_successful_command(result) -> None:
    """Helper function to assert command executed successfully."""
    assert result.exit_code == 0
    assert result.output is not None


def assert_failed_command(result, expected_exit_code: int = 1) -> None:
    """Helper function to assert command failed with expected exit code."""
    assert result.exit_code == expected_exit_code


class TestCLIBasics:
    """Test basic CLI functionality."""

    def test_cli_help(self):
        """Test that help command works."""
        result = run_cli_command(["--help"])
        assert_successful_command(result)
        assert "ForTheRekord" in result.output

    def test_cli_version(self):
        """Test that version command works."""
        result = run_cli_command(["--version"])
        assert_successful_command(result)

    def test_main_command_no_config(self):
        """Test that main command creates config when none exists."""
        with patch("fortherekord.main.load_config") as mock_load_config:
            with patch("fortherekord.main.create_default_config") as mock_create_config:
                with patch("fortherekord.main.get_config_path") as mock_get_path:
                    # Mock load_config to return empty config (no rekordbox_library_path)
                    mock_load_config.return_value = {}
                    mock_get_path.return_value = "/test/config.yaml"
                    
                    result = run_cli_command([])
                    assert_successful_command(result)
                    # Should handle missing config gracefully
                    assert "Error: rekordbox_library_path not configured" in result.output
                    assert "Creating default config file..." in result.output

    @patch("fortherekord.main.load_config")
    @patch("fortherekord.main.create_default_config")
    @patch("fortherekord.main.get_config_path")
    def test_main_command_missing_library_path(self, mock_get_path, mock_create, mock_load_config):
        """Test main command when config exists but library path is missing."""
        mock_load_config.return_value = {}  # Config without rekordbox_library_path
        mock_get_path.return_value = "/test/config.yaml"
        mock_create.return_value = None

        result = run_cli_command([])
        assert_successful_command(result)
        assert "Error: rekordbox_library_path not configured" in result.output
        assert "Creating default config file..." in result.output
        assert "Config created at: /test/config.yaml" in result.output
        assert "Please verify the database path and run again" in result.output

    @patch("fortherekord.main.load_config")
    @patch("fortherekord.main.RekordboxLibrary")
    @patch("fortherekord.main.RekordboxMetadataProcessor")
    def test_main_command_all_tracks_success(self, mock_processor_class, mock_rekordbox_class, mock_load_config):
        """Test main command with --all-tracks flag."""
        # Setup mocks
        mock_load_config.return_value = {"rekordbox_library_path": "/test/db.edb"}
        mock_rekordbox = mock_rekordbox_class.return_value
        mock_processor = mock_processor_class.return_value
        
        # Mock tracks
        from fortherekord.models import Track
        original_track = Track(id="1", title="Test Song", artist="Test Artist", key="Am", bpm=120)
        enhanced_track = Track(id="1", title="Test Song - Test Artist [Am]", artist="Test Artist", key="Am", bpm=120)
        
        mock_rekordbox.get_all_tracks.return_value = [original_track]
        mock_processor.enhance_track_title.return_value = enhanced_track
        mock_rekordbox.update_track_metadata.return_value = True
        mock_rekordbox.save_changes.return_value = True
        
        result = run_cli_command(["--all-tracks"])
        assert_successful_command(result)
        assert "Processing all tracks in collection..." in result.output
        assert "Successfully updated 1 tracks" in result.output

    @patch("fortherekord.main.load_config")
    @patch("fortherekord.main.RekordboxLibrary")
    @patch("fortherekord.main.RekordboxMetadataProcessor")
    def test_main_command_playlists_success(self, mock_processor_class, mock_rekordbox_class, mock_load_config):
        """Test main command processing tracks from playlists."""
        # Setup mocks
        mock_load_config.return_value = {
            "rekordbox_library_path": "/test/db.edb",
            "ignore_playlists": ["ignored"]
        }
        mock_rekordbox = mock_rekordbox_class.return_value
        mock_processor = mock_processor_class.return_value
        
        # Mock tracks
        from fortherekord.models import Track
        original_track = Track(id="1", title="Test Song", artist="Test Artist", key="Am", bpm=120)
        enhanced_track = Track(id="1", title="Test Song - Test Artist [Am]", artist="Test Artist", key="Am", bpm=120)
        
        mock_rekordbox.get_tracks_from_playlists.return_value = [original_track]
        mock_processor.enhance_track_title.return_value = enhanced_track
        mock_rekordbox.update_track_metadata.return_value = True
        mock_rekordbox.save_changes.return_value = True
        
        result = run_cli_command([])
        assert_successful_command(result)
        assert "Processing tracks from playlists..." in result.output
        assert "Successfully updated 1 tracks" in result.output

    @patch("fortherekord.main.load_config")
    @patch("fortherekord.main.RekordboxLibrary")
    @patch("fortherekord.main.RekordboxMetadataProcessor")
    def test_main_command_no_tracks_found(self, mock_processor_class, mock_rekordbox_class, mock_load_config):
        """Test main command when no tracks are found."""
        # Setup mocks
        mock_load_config.return_value = {"rekordbox_library_path": "/test/db.edb"}
        mock_rekordbox = mock_rekordbox_class.return_value
        mock_rekordbox.get_tracks_from_playlists.return_value = []
        
        result = run_cli_command([])
        assert_successful_command(result)
        assert "No tracks found to process" in result.output

    @patch("fortherekord.main.load_config")
    @patch("fortherekord.main.RekordboxLibrary")
    @patch("fortherekord.main.RekordboxMetadataProcessor")
    def test_main_command_no_changes_needed(self, mock_processor_class, mock_rekordbox_class, mock_load_config):
        """Test main command when no tracks need updating."""
        # Setup mocks
        mock_load_config.return_value = {"rekordbox_library_path": "/test/db.edb"}
        mock_rekordbox = mock_rekordbox_class.return_value
        mock_processor = mock_processor_class.return_value
        
        # Mock track that doesn't need enhancement
        from fortherekord.models import Track
        track = Track(id="1", title="Test Song - Test Artist [Am]", artist="Test Artist", key="Am", bpm=120)
        
        mock_rekordbox.get_tracks_from_playlists.return_value = [track]
        mock_processor.enhance_track_title.return_value = track  # Same track returned
        
        result = run_cli_command([])
        assert_successful_command(result)
        assert "No changes needed" in result.output

    @patch("fortherekord.main.load_config")
    @patch("fortherekord.main.RekordboxLibrary")
    @patch("fortherekord.main.RekordboxMetadataProcessor")
    def test_main_command_update_failure(self, mock_processor_class, mock_rekordbox_class, mock_load_config):
        """Test main command when track update fails."""
        # Setup mocks
        mock_load_config.return_value = {"rekordbox_library_path": "/test/db.edb"}
        mock_rekordbox = mock_rekordbox_class.return_value
        mock_processor = mock_processor_class.return_value
        
        # Mock tracks
        from fortherekord.models import Track
        original_track = Track(id="1", title="Test Song", artist="Test Artist", key="Am", bpm=120)
        enhanced_track = Track(id="1", title="Test Song - Test Artist [Am]", artist="Test Artist", key="Am", bpm=120)
        
        mock_rekordbox.get_tracks_from_playlists.return_value = [original_track]
        mock_processor.enhance_track_title.return_value = enhanced_track
        mock_rekordbox.update_track_metadata.return_value = False  # Simulate failure
        
        result = run_cli_command([])
        assert_successful_command(result)
        assert "Failed to update track: Test Song" in result.output

    @patch("fortherekord.main.load_config")
    @patch("fortherekord.main.RekordboxLibrary")
    @patch("fortherekord.main.RekordboxMetadataProcessor")
    def test_main_command_save_failure(self, mock_processor_class, mock_rekordbox_class, mock_load_config):
        """Test main command when saving changes fails."""
        # Setup mocks
        mock_load_config.return_value = {"rekordbox_library_path": "/test/db.edb"}
        mock_rekordbox = mock_rekordbox_class.return_value
        mock_processor = mock_processor_class.return_value
        
        # Mock tracks
        from fortherekord.models import Track
        original_track = Track(id="1", title="Test Song", artist="Test Artist", key="Am", bpm=120)
        enhanced_track = Track(id="1", title="Test Song - Test Artist [Am]", artist="Test Artist", key="Am", bpm=120)
        
        mock_rekordbox.get_tracks_from_playlists.return_value = [original_track]
        mock_processor.enhance_track_title.return_value = enhanced_track
        mock_rekordbox.update_track_metadata.return_value = True
        mock_rekordbox.save_changes.return_value = False  # Simulate save failure
        
        result = run_cli_command([])
        assert_successful_command(result)
        assert "Error: Failed to save changes" in result.output

    @patch("fortherekord.main.load_config")
    @patch("fortherekord.main.RekordboxLibrary")
    def test_main_command_file_not_found(self, mock_rekordbox_class, mock_load_config):
        """Test main command when database file doesn't exist."""
        mock_load_config.return_value = {"rekordbox_library_path": "/nonexistent/path.db"}
        mock_rekordbox_class.side_effect = FileNotFoundError("Database not found")

        result = run_cli_command([])
        assert_successful_command(result)
        assert "Error: Rekordbox database not found" in result.output

    @patch("fortherekord.main.load_config")
    @patch("fortherekord.main.RekordboxLibrary")
    def test_main_command_library_error(self, mock_rekordbox, mock_load_config):
        """Test main command when library loading fails."""
        mock_load_config.return_value = {"rekordbox_library_path": "/test/path.db"}
        mock_rekordbox.side_effect = ValueError("Invalid database format")

        result = run_cli_command([])
        assert_successful_command(result)
        assert "Error loading Rekordbox library: Invalid database format" in result.output


class TestCLIErrors:
    """Test CLI error handling."""

    def test_invalid_command(self):
        """Test that invalid commands show help."""
        result = run_cli_command(["invalid"])
        assert_failed_command(result, 2)  # Click returns 2 for usage errors
        assert "Usage:" in result.output


# Test fixtures for common setup
@pytest.fixture
def cli_runner():
    """Provide a Click CLI runner for tests."""
    return CliRunner()


# Example of how to use fixtures to reduce repetition
class TestCLIWithFixtures:
    """Example of using fixtures to reduce test repetition."""

    def test_help_with_fixture(self, cli_runner):
        """Test help command using fixture."""
        result = cli_runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "ForTheRekord" in result.output
