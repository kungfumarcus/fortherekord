"""
Tests for main CLI functionality.

Tests the individual functions and CLI components.
"""

import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock, Mock

from fortherekord.main import (
    cli,
    load_config,
    load_library,
    initialize_processor,
    get_collection_to_process,
    process_tracks,
)
from .conftest import create_sample_track, silence_click_echo


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

    def test_main_command_help(self):
        """Test main command help."""
        result = run_cli_command(["--help"])
        assert_successful_command(result)
        assert "ForTheRekord - Process Rekordbox track metadata" in result.output

    @patch("fortherekord.main.load_config")
    def test_main_command_no_config(self, mock_load_config):
        """Test main command with no configuration."""
        mock_load_config.return_value = None

        result = run_cli_command([])
        assert_successful_command(result)  # Should exit gracefully

    @patch("fortherekord.main.load_library")
    @patch("fortherekord.main.load_config")
    def test_main_command_missing_credentials(self, mock_load_config, mock_load_library):
        """Test main command with missing Spotify credentials."""
        mock_load_config.return_value = {"rekordbox_library_path": "/test/db"}
        # Mock successful library loading so we get to the Spotify credentials check
        mock_rekordbox = Mock()
        mock_load_library.return_value = mock_rekordbox

        # Mock the functions that would be called during processing
        with (
            patch("fortherekord.main.get_collection_to_process") as mock_get_collection,
            patch("fortherekord.main.initialize_processor") as mock_init_processor,
            patch("fortherekord.main.process_tracks"),
        ):
            mock_collection = Mock()
            mock_tracks = [Mock()]
            mock_get_collection.return_value = (mock_collection, mock_tracks)
            mock_init_processor.return_value = Mock()

            result = run_cli_command([])
            assert_successful_command(result)
            assert "Spotify credentials not configured" in result.output


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
        """Test processor initialization and original metadata extraction."""
        config = {"test": "config"}
        mock_processor = mock_processor_class.return_value
        tracks = [Mock(title="Song - Artist [Am]"), Mock(title="Another Song")]

        result = initialize_processor(config, tracks)

        assert result == mock_processor
        mock_processor_class.assert_called_once_with(config)
        mock_processor.extract_original_metadata.assert_called_once_with(tracks)


class TestGetCollectionToProcess:
    """Test get_collection_to_process function."""

    def test_get_collection_with_tracks(self):
        """Test getting collection with tracks."""
        mock_rekordbox = MagicMock()
        mock_collection = MagicMock()
        mock_tracks = [MagicMock(), MagicMock()]
        mock_playlists = [MagicMock(), MagicMock()]

        mock_collection.playlists = mock_playlists
        mock_collection.get_all_tracks.return_value = mock_tracks
        mock_rekordbox.get_collection.return_value = mock_collection

        config = {"ignore_playlists": ["test"]}

        with patch("fortherekord.main.click.echo"), patch("builtins.print"):
            collection, tracks = get_collection_to_process(mock_rekordbox, config)

        assert collection == mock_collection
        assert tracks == mock_tracks
        mock_rekordbox.get_collection.assert_called_once_with({"ignore_playlists": ["test"]})
        mock_collection.get_all_tracks.assert_called_once()
        # Verify display_tree was called on each playlist
        for playlist in mock_playlists:
            playlist.display_tree.assert_called_once_with(1)


class TestProcessTracks:
    """Test process_tracks function."""

    def test_process_tracks_success(self):
        """Test successful track processing."""
        # Create test tracks using utility
        original_track = create_sample_track()
        enhanced_track = create_sample_track(title="Test Song - Test Artist [Am]")

        # Setup mocks
        mock_rekordbox = MagicMock()
        mock_processor = MagicMock()

        mock_processor.enhance_track_title.return_value = enhanced_track
        mock_rekordbox.update_track_metadata.return_value = True
        mock_rekordbox.save_changes.return_value = 1  # Return count of saved tracks

        with silence_click_echo() as mock_echo:
            process_tracks([original_track], mock_rekordbox, mock_processor)

        # Verify calls
        mock_processor.enhance_track_title.assert_called()
        mock_rekordbox.save_changes.assert_called_once()
        # update_track_metadata should NOT be called from process_tracks anymore
        mock_rekordbox.update_track_metadata.assert_not_called()

        # Check that success message was printed
        echo_calls = [str(call) for call in mock_echo.call_args_list]
        assert any("Successfully updated 1 tracks" in call for call in echo_calls)

    def test_process_tracks_no_changes(self):
        """Test track processing when no changes are needed."""
        # Track that doesn't need enhancement - both title and artist unchanged
        track = create_sample_track(title="Test Song - Test Artist [Am]")

        # Setup mocks
        mock_rekordbox = MagicMock()
        mock_processor = MagicMock()

        mock_processor.enhance_track_title.return_value = track  # Same track returned (no changes)
        mock_rekordbox.save_changes.return_value = 0  # No tracks were modified

        with patch("fortherekord.main.click.echo") as mock_echo:
            process_tracks([track], mock_rekordbox, mock_processor)

        # Verify save_changes was called (but returned 0)
        mock_rekordbox.save_changes.assert_called_once()
        mock_rekordbox.update_track_metadata.assert_not_called()

        # Check that "No changes needed" message was printed
        echo_calls = [str(call) for call in mock_echo.call_args_list]
        assert any("No changes needed" in call for call in echo_calls)

    def test_process_tracks_update_failure(self):
        """Test track processing when update fails."""
        from fortherekord.models import Track

        original_track = Track(id="1", title="Test Song", artist="Test Artist", key="Am")
        enhanced_track = Track(
            id="1", title="Test Song - Test Artist [Am]", artist="Test Artist", key="Am"
        )

        # Setup mocks
        mock_rekordbox = MagicMock()
        mock_processor = MagicMock()

        mock_processor.enhance_track_title.return_value = enhanced_track
        mock_rekordbox.save_changes.return_value = 0  # No tracks saved due to failure

        with patch("fortherekord.main.click.echo") as mock_echo:
            process_tracks([original_track], mock_rekordbox, mock_processor)

        # Check that "No changes needed" message was printed (since save_changes returned 0)
        echo_calls = [str(call) for call in mock_echo.call_args_list]
        assert any("No changes needed" in call for call in echo_calls)

    def test_process_tracks_save_failure(self):
        """Test track processing when save fails."""
        from fortherekord.models import Track

        original_track = Track(id="1", title="Test Song", artist="Test Artist", key="Am")
        enhanced_track = Track(
            id="1", title="Test Song - Test Artist [Am]", artist="Test Artist", key="Am"
        )

        # Setup mocks
        mock_rekordbox = MagicMock()
        mock_processor = MagicMock()

        mock_processor.enhance_track_title.return_value = enhanced_track
        mock_rekordbox.save_changes.return_value = 0  # Save returns 0 (no tracks saved)

        with patch("fortherekord.main.click.echo") as mock_echo:
            process_tracks([original_track], mock_rekordbox, mock_processor)

        # Check that "No changes needed" message was printed (since save_changes returned 0)
        echo_calls = [str(call) for call in mock_echo.call_args_list]
        assert any("No changes needed" in call for call in echo_calls)


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
    @patch("fortherekord.main.get_collection_to_process")
    @patch("fortherekord.main.initialize_processor")
    @patch("fortherekord.main.load_library")
    @patch("fortherekord.main.load_config")
    def test_cli_no_tracks_found(
        self,
        mock_load_config,
        mock_load_library,
        mock_init_processor,
        mock_get_collection,
        mock_process_tracks,
    ):
        """Test CLI when no tracks are found to process."""
        mock_load_config.return_value = {"rekordbox_library_path": "/test/db.edb"}
        mock_load_library.return_value = Mock()
        mock_init_processor.return_value = Mock()
        mock_get_collection.return_value = (Mock(), [])  # No tracks found

        result = run_cli_command([])
        assert result.exit_code == 0
        assert "No tracks found to process" in result.output
        mock_process_tracks.assert_not_called()  # Should not be called when no tracks

    @patch("fortherekord.main.process_tracks")
    @patch("fortherekord.main.get_collection_to_process")
    @patch("fortherekord.main.initialize_processor")
    @patch("fortherekord.main.load_library")
    @patch("fortherekord.main.load_config")
    def test_cli_successful_processing(
        self,
        mock_load_config,
        mock_load_library,
        mock_init_processor,
        mock_get_collection,
        mock_process_tracks,
    ):
        """Test CLI when tracks are successfully processed."""
        mock_load_config.return_value = {"rekordbox_library_path": "/test/db.edb"}
        mock_rekordbox = Mock()
        mock_processor = Mock()
        mock_tracks = [Mock(), Mock()]  # Some tracks to process
        mock_collection = Mock()

        mock_load_library.return_value = mock_rekordbox
        mock_init_processor.return_value = mock_processor
        mock_get_collection.return_value = (mock_collection, mock_tracks)

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

    @patch("fortherekord.main.load_config")
    @patch("fortherekord.main.load_library")
    @patch("fortherekord.main.SpotifyLibrary")
    @patch("fortherekord.playlist_sync.PlaylistSyncService")
    @patch("fortherekord.main.initialize_processor")
    @patch("fortherekord.main.process_tracks")
    def test_cli_successful_spotify_sync(
        self,
        mock_process_tracks,
        mock_initialize_processor,
        mock_sync_service_class,
        mock_spotify_class,
        mock_load_library,
        mock_load_config,
    ):
        """Test CLI with successful Spotify sync workflow."""
        # Mock config with Spotify credentials
        mock_load_config.return_value = {
            "rekordbox_library_path": "/test/db.edb",
            "spotify_client_id": "test_client_id",
            "spotify_client_secret": "test_client_secret",
        }

        # Mock successful library loading
        mock_rekordbox = Mock()

        # Create mock playlists with proper attributes
        mock_playlist1 = Mock()
        mock_playlist1.name = "Test Playlist 1"
        mock_playlist1.tracks = []
        mock_playlist1.display_tree = Mock()  # Mock the display_tree method

        # Create a sample track for the second playlist
        from fortherekord.models import Track

        sample_track = Track(id="1", title="Test Song", artist="Test Artist", key="Am")

        mock_playlist2 = Mock()
        mock_playlist2.name = "Test Playlist 2"
        mock_playlist2.tracks = [sample_track]  # Add a track so there are tracks to process
        mock_playlist2.display_tree = Mock()  # Mock the display_tree method

        # Create actual Collection object instead of Mock
        from fortherekord.models import Collection

        mock_collection = Collection(playlists=[mock_playlist1, mock_playlist2])

        mock_rekordbox.get_collection.return_value = mock_collection

        # Mock empty tracks list so metadata processing is skipped
        mock_rekordbox.get_all_tracks.return_value = []
        mock_load_library.return_value = mock_rekordbox

        # Mock successful Spotify authentication
        mock_spotify = Mock()
        mock_spotify.user_id = "test_user"
        mock_spotify.get_playlists.return_value = []  # Return empty list
        mock_spotify_class.return_value = mock_spotify

        # Mock sync service
        mock_sync_service = Mock()
        mock_sync_service_class.return_value = mock_sync_service

        result = run_cli_command([])
        assert_successful_command(result)

        # Verify the workflow
        mock_spotify_class.assert_called_once_with("test_client_id", "test_client_secret")
        mock_sync_service_class.assert_called_once_with(mock_rekordbox, mock_spotify)
        mock_sync_service.sync_collection.assert_called_once_with(mock_collection)

        # Check output messages
        assert "Authenticated with Spotify as user: test_user" in result.output
        assert "Found 2 Rekordbox playlists to sync" in result.output
        assert "Spotify playlist sync complete" in result.output

    @patch("fortherekord.main.load_config")
    @patch("fortherekord.main.load_library")
    @patch("fortherekord.main.SpotifyLibrary")
    @patch("fortherekord.main.initialize_processor")
    @patch("fortherekord.main.process_tracks")
    def test_cli_spotify_auth_failure(
        self,
        mock_process_tracks,
        mock_initialize_processor,
        mock_spotify_class,
        mock_load_library,
        mock_load_config,
    ):
        """Test CLI when Spotify authentication fails."""
        # Mock config with Spotify credentials
        mock_load_config.return_value = {
            "rekordbox_library_path": "/test/db.edb",
            "spotify_client_id": "test_client_id",
            "spotify_client_secret": "test_client_secret",
        }

        # Mock successful library loading
        mock_rekordbox = Mock()

        # Create a sample track so Spotify sync is attempted
        from fortherekord.models import Track, Collection

        sample_track = Track(id="1", title="Test Song", artist="Test Artist", key="Am")

        mock_playlist = Mock()
        mock_playlist.name = "Test Playlist"
        mock_playlist.tracks = [sample_track]
        mock_playlist.display_tree = Mock()

        mock_collection = Collection(playlists=[mock_playlist])
        mock_rekordbox.get_collection.return_value = mock_collection

        # Mock empty tracks so metadata processing is skipped
        mock_rekordbox.get_all_tracks.return_value = []
        mock_load_library.return_value = mock_rekordbox

        # Mock Spotify authentication failure
        mock_spotify_class.side_effect = ValueError("Invalid credentials")

        result = run_cli_command([])
        assert result.exit_code == 0  # Should handle error gracefully

        # Check error handling
        assert "Failed to authenticate with Spotify: Invalid credentials" in result.output
