"""
Tests for main CLI functionality.

Tests the individual functions and CLI components.
"""

import pytest
import click
from click.testing import CliRunner
from unittest.mock import patch, MagicMock, Mock

from fortherekord.main import cli, load_config, load_library, initialize_processor, get_tracks_to_process, process_tracks


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


class TestLoadConfig:
    """Test load_config function."""

    @patch("fortherekord.main.config_load_config")
    @patch("fortherekord.main.create_default_config")
    @patch("fortherekord.main.get_config_path")
    def test_load_config_missing_library_path(self, mock_get_path, mock_create, mock_load_config):
        """Test load_config when rekordbox_library_path is missing."""
        mock_load_config.return_value = {}
        mock_get_path.return_value = "/test/config.yaml"
        
        with patch("fortherekord.main.click.echo") as mock_echo:
            result = load_config()
            
        assert result is None
        mock_create.assert_called_once()
        assert mock_echo.call_count == 4  # 4 echo calls for error messages

    @patch("fortherekord.main.config_load_config")
    def test_load_config_valid(self, mock_load_config):
        """Test load_config with valid configuration."""
        expected_config = {"rekordbox_library_path": "/test/db.edb"}
        mock_load_config.return_value = expected_config
        
        result = load_config()
        
        assert result == expected_config


class TestLoadLibrary:
    """Test load_library function."""

    @patch("fortherekord.main.RekordboxLibrary")
    def test_load_library_success(self, mock_rekordbox_class):
        """Test successful library loading."""
        mock_rekordbox = mock_rekordbox_class.return_value
        mock_rekordbox.is_rekordbox_running = False
        
        with patch("fortherekord.main.click.echo"):
            result = load_library("/test/db.edb")
            
        assert result == mock_rekordbox
        mock_rekordbox._get_database.assert_called_once()

    @patch("fortherekord.main.RekordboxLibrary")
    def test_load_library_rekordbox_running(self, mock_rekordbox_class):
        """Test library loading when Rekordbox is running."""
        mock_rekordbox = mock_rekordbox_class.return_value
        mock_rekordbox.is_rekordbox_running = True
        
        with patch("fortherekord.main.click.echo") as mock_echo:
            with pytest.raises(RuntimeError, match="Rekordbox is currently running"):
                load_library("/test/db.edb")
                
        assert mock_echo.call_count == 4  # Loading + 3 error messages


class TestInitializeProcessor:
    """Test initialize_processor function."""

    @patch("fortherekord.main.RekordboxMetadataProcessor")
    def test_initialize_processor(self, mock_processor_class):
        """Test processor initialization."""
        config = {"test": "config"}
        mock_processor = mock_processor_class.return_value
        
        result = initialize_processor(config)
        
        assert result == mock_processor
        mock_processor_class.assert_called_once_with(config)


class TestGetTracksToProcess:
    """Test get_tracks_to_process function."""

    def test_get_tracks_all_tracks(self):
        """Test getting all tracks."""
        mock_rekordbox = MagicMock()
        mock_tracks = [MagicMock(), MagicMock()]
        mock_rekordbox.get_all_tracks.return_value = mock_tracks
        config = {}
        
        with patch("fortherekord.main.click.echo"):
            result = get_tracks_to_process(mock_rekordbox, config, all_tracks=True)
            
        assert result == mock_tracks
        mock_rekordbox.get_all_tracks.assert_called_once()

    def test_get_tracks_from_playlists(self):
        """Test getting tracks from playlists."""
        mock_rekordbox = MagicMock()
        mock_tracks = [MagicMock(), MagicMock()]
        mock_playlists = [MagicMock(), MagicMock()]
        
        mock_rekordbox.get_playlists.return_value = mock_playlists
        mock_rekordbox.get_tracks_from_playlists.return_value = mock_tracks
        config = {"ignore_playlists": ["test"]}
        
        with patch("fortherekord.main.click.echo"), patch("builtins.print"):
            result = get_tracks_to_process(mock_rekordbox, config, all_tracks=False)
            
        assert result == mock_tracks
        mock_rekordbox.get_playlists.assert_called_once_with(["test"])
        mock_rekordbox.get_tracks_from_playlists.assert_called_once_with(["test"])
        # Verify display_tree was called on each playlist
        for playlist in mock_playlists:
            playlist.display_tree.assert_called_once_with(1)


class TestProcessTracks:
    """Test process_tracks function."""

    def test_process_tracks_success(self):
        """Test successful track processing."""
        from fortherekord.models import Track
        
        # Create test tracks
        original_track = Track(id="1", title="Test Song", artist="Test Artist", key="Am", bpm=120)
        enhanced_track = Track(id="1", title="Test Song - Test Artist [Am]", artist="Test Artist", key="Am", bpm=120)
        
        # Setup mocks
        mock_rekordbox = MagicMock()
        mock_processor = MagicMock()
        
        mock_processor.enhance_track_title.return_value = enhanced_track
        mock_rekordbox.update_track_metadata.return_value = True
        mock_rekordbox.save_changes.return_value = True
        
        with patch("fortherekord.main.click.echo") as mock_echo:
            process_tracks([original_track], mock_rekordbox, mock_processor)
            
        # Verify calls
        mock_processor.enhance_track_title.assert_called()
        mock_rekordbox.update_track_metadata.assert_called_once_with("1", enhanced_track.title, enhanced_track.artist)
        mock_rekordbox.save_changes.assert_called_once()
        
        # Check that success message was printed
        echo_calls = [str(call) for call in mock_echo.call_args_list]
        assert any("Successfully updated 1 tracks" in call for call in echo_calls)

    def test_process_tracks_no_changes(self):
        """Test track processing when no changes are needed."""
        from fortherekord.models import Track
        
        # Track that doesn't need enhancement
        track = Track(id="1", title="Test Song - Test Artist [Am]", artist="Test Artist", key="Am", bpm=120)
        
        # Setup mocks
        mock_rekordbox = MagicMock()
        mock_processor = MagicMock()
        
        mock_processor.enhance_track_title.return_value = track  # Same track returned
        
        with patch("fortherekord.main.click.echo") as mock_echo:
            process_tracks([track], mock_rekordbox, mock_processor)
            
        # Verify no update was attempted
        mock_rekordbox.update_track_metadata.assert_not_called()
        mock_rekordbox.save_changes.assert_not_called()
        
        # Check that "No changes needed" message was printed
        echo_calls = [str(call) for call in mock_echo.call_args_list]
        assert any("No changes needed" in call for call in echo_calls)

    def test_process_tracks_update_failure(self):
        """Test track processing when update fails."""
        from fortherekord.models import Track
        
        original_track = Track(id="1", title="Test Song", artist="Test Artist", key="Am", bpm=120)
        enhanced_track = Track(id="1", title="Test Song - Test Artist [Am]", artist="Test Artist", key="Am", bpm=120)
        
        # Setup mocks
        mock_rekordbox = MagicMock()
        mock_processor = MagicMock()
        
        mock_processor.enhance_track_title.return_value = enhanced_track
        mock_rekordbox.update_track_metadata.return_value = False  # Simulate failure
        
        with patch("fortherekord.main.click.echo") as mock_echo:
            process_tracks([original_track], mock_rekordbox, mock_processor)
            
        # Check that failure message was printed
        echo_calls = [str(call) for call in mock_echo.call_args_list]
        assert any("Failed to update track: Test Song" in call for call in echo_calls)

    def test_process_tracks_save_failure(self):
        """Test track processing when save fails."""
        from fortherekord.models import Track
        
        original_track = Track(id="1", title="Test Song", artist="Test Artist", key="Am", bpm=120)
        enhanced_track = Track(id="1", title="Test Song - Test Artist [Am]", artist="Test Artist", key="Am", bpm=120)
        
        # Setup mocks
        mock_rekordbox = MagicMock()
        mock_processor = MagicMock()
        
        mock_processor.enhance_track_title.return_value = enhanced_track
        mock_rekordbox.update_track_metadata.return_value = True
        mock_rekordbox.save_changes.return_value = False  # Simulate save failure
        
        with patch("fortherekord.main.click.echo") as mock_echo:
            process_tracks([original_track], mock_rekordbox, mock_processor)
            
        # Check that save failure message was printed
        echo_calls = [str(call) for call in mock_echo.call_args_list]
        assert any("Error: Failed to save changes" in call for call in echo_calls)


class TestCLIIntegration:
    """Test CLI integration with error handling."""

    @patch("fortherekord.main.config_load_config")
    def test_cli_no_config(self, mock_load_config):
        """Test CLI when config is missing."""
        mock_load_config.return_value = {}
        
        result = run_cli_command([])
        assert_successful_command(result)
        assert "Error: rekordbox_library_path not configured" in result.output

    @patch("fortherekord.main.load_config")
    @patch("fortherekord.main.load_library")
    def test_cli_rekordbox_running(self, mock_load_library, mock_load_config):
        """Test CLI when Rekordbox is running."""
        mock_load_config.return_value = {"rekordbox_library_path": "/test/db.edb"}
        mock_load_library.side_effect = RuntimeError("Rekordbox is currently running")
        
        result = run_cli_command([])
        assert_successful_command(result)  # CLI handles the error gracefully

    @patch("fortherekord.main.load_config")
    @patch("fortherekord.main.load_library")
    def test_cli_file_not_found(self, mock_load_library, mock_load_config):
        """Test CLI when database file doesn't exist."""
        mock_load_config.return_value = {"rekordbox_library_path": "/test/db.edb"}
        mock_load_library.side_effect = FileNotFoundError()
        
        result = run_cli_command([])
        assert_successful_command(result)
        assert "Error: Rekordbox database not found" in result.output

    @patch("fortherekord.main.load_config")
    def test_cli_file_not_found_direct(self, mock_load_config):
        """Test CLI when database file doesn't exist - direct path test."""
        # Set up config to point to a non-existent database file
        mock_load_config.return_value = {"rekordbox_library_path": "/nonexistent/path/db.edb"}
        
        result = run_cli_command([])
        assert result.exit_code == 0  # CLI handles the error gracefully
        assert "Error: Rekordbox database not found" in result.output

    @patch("fortherekord.main.process_tracks")
    @patch("fortherekord.main.get_tracks_to_process")
    @patch("fortherekord.main.initialize_processor")
    @patch("fortherekord.main.load_library")
    @patch("fortherekord.main.load_config")
    def test_cli_no_tracks_found(self, mock_load_config, mock_load_library, mock_init_processor, mock_get_tracks, mock_process_tracks):
        """Test CLI when no tracks are found to process."""
        mock_load_config.return_value = {"rekordbox_library_path": "/test/db.edb"}
        mock_load_library.return_value = Mock()
        mock_init_processor.return_value = Mock()
        mock_get_tracks.return_value = []  # No tracks found
        
        result = run_cli_command([])
        assert result.exit_code == 0
        assert "No tracks found to process" in result.output
        mock_process_tracks.assert_not_called()  # Should not be called when no tracks

    @patch("fortherekord.main.process_tracks")
    @patch("fortherekord.main.get_tracks_to_process")
    @patch("fortherekord.main.initialize_processor")
    @patch("fortherekord.main.load_library")
    @patch("fortherekord.main.load_config")
    def test_cli_successful_processing(self, mock_load_config, mock_load_library, mock_init_processor, mock_get_tracks, mock_process_tracks):
        """Test CLI when tracks are successfully processed."""
        mock_load_config.return_value = {"rekordbox_library_path": "/test/db.edb"}
        mock_rekordbox = Mock()
        mock_processor = Mock()
        mock_tracks = [Mock(), Mock()]  # Some tracks to process
        
        mock_load_library.return_value = mock_rekordbox
        mock_init_processor.return_value = mock_processor
        mock_get_tracks.return_value = mock_tracks
        
        result = run_cli_command([])
        assert result.exit_code == 0
        mock_process_tracks.assert_called_once_with(mock_tracks, mock_rekordbox, mock_processor)

    @patch("fortherekord.main.load_config")
    @patch("fortherekord.main.load_library") 
    def test_cli_os_error(self, mock_load_library, mock_load_config):
        """Test CLI when OS error occurs."""
        mock_load_config.return_value = {"rekordbox_library_path": "/test/db.edb"}
        mock_load_library.side_effect = OSError("Permission denied")
        
        result = run_cli_command([])
        assert_successful_command(result)
        assert "Error loading Rekordbox library: Permission denied" in result.output
