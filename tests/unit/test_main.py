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
from .conftest import create_track, create_collection, silence_click_echo


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


def create_mock_playlist(name: str = "Test Playlist", tracks: list = None, children: list = None):
    """Helper function to create a mock playlist for main.py testing with display_tree method."""
    if tracks is None:
        tracks = []
    if children is None:
        children = []

    mock_playlist = Mock()
    mock_playlist.name = name
    mock_playlist.tracks = tracks
    mock_playlist.children = children
    mock_playlist.display_tree = Mock()
    return mock_playlist


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
        mock_load_config.return_value = {"rekordbox": {"library_path": "/test/db"}}
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
            mock_collection.get_all_tracks = Mock(return_value=[Mock()])
            mock_get_collection.return_value = mock_collection
            mock_init_processor.return_value = Mock()

            result = run_cli_command([])
            assert_successful_command(result)
            assert "Spotify credentials not configured" in result.output


class TestLoadConfig:
    """Test load_config function."""

    @patch("fortherekord.main.create_default_config")
    @patch("fortherekord.main.config_load_config")
    def test_load_config_missing_library_path(self, mock_load_config, mock_create):
        """Test load_config when rekordbox_library_path is missing."""
        mock_load_config.return_value = {}

        with patch("fortherekord.main.click.echo") as mock_echo:
            result = load_config()

        assert result is None
        mock_create.assert_called_once()
        assert mock_echo.call_count == 4  # 4 echo calls for error messages

    @patch("fortherekord.main.config_load_config")
    def test_load_config_valid(self, mock_load_config):
        """Test load_config with valid configuration."""
        expected_config = {"rekordbox": {"library_path": "/test/db.edb"}}
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

        config = {"rekordbox": {"library_path": "/test/db.edb"}}
        with patch("fortherekord.main.click.echo"):
            result = load_library(config)

        assert result == mock_rekordbox
        mock_rekordbox._get_database.assert_called_once()

    @patch("fortherekord.main.RekordboxLibrary")
    def test_load_library_rekordbox_running(self, mock_rekordbox_class):
        """Test library loading when Rekordbox is running."""
        mock_rekordbox = mock_rekordbox_class.return_value
        mock_rekordbox.is_rekordbox_running = True

        config = {"rekordbox": {"library_path": "/test/db.edb"}}
        with patch("fortherekord.main.click.echo") as mock_echo:
            with pytest.raises(RuntimeError, match="Rekordbox is currently running"):
                load_library(config)

        assert mock_echo.call_count == 4  # Loading + 3 error messages

    @patch("fortherekord.main.RekordboxLibrary")
    def test_load_library_rekordbox_running_dry_run(self, mock_rekordbox_class):
        """Test library loading when Rekordbox is running but in dry-run mode."""
        mock_rekordbox = mock_rekordbox_class.return_value
        mock_rekordbox.is_rekordbox_running = True

        config = {"rekordbox": {"library_path": "/test/db.edb"}}
        with patch("fortherekord.main.click.echo") as mock_echo:
            result = load_library(config, dry_run=True)

        assert result == mock_rekordbox
        mock_rekordbox._get_database.assert_called_once()
        # Should get loading message + warning about Rekordbox running
        assert mock_echo.call_count == 2
        assert "Note: Rekordbox is running, but continuing in dry-run mode" in str(
            mock_echo.call_args_list
        )


class TestInitializeProcessor:
    """Test initialize_processor function."""

    @patch("fortherekord.main.MusicLibraryProcessor")
    def test_initialize_processor(self, mock_processor_class):
        """Test processor initialization and original metadata extraction."""
        config = {"test": "config"}
        mock_processor = mock_processor_class.return_value
        # Mock processor with features enabled
        mock_processor.add_key_to_title = True
        mock_processor.add_artist_to_title = True
        mock_processor.remove_artists_in_title = True

        result = initialize_processor(config)

        assert result == mock_processor
        mock_processor_class.assert_called_once_with(config)
        # Note: extract_original_metadata was removed as original values are
        # set during track loading

    @patch("fortherekord.main.MusicLibraryProcessor")
    @patch("fortherekord.main.click.echo")
    def test_initialize_processor_disabled(self, mock_echo, mock_processor_class):
        """Test processor initialization when all features are disabled."""
        config = {"test": "config"}
        mock_processor = mock_processor_class.return_value
        # Mock processor with all features disabled
        mock_processor.add_key_to_title = False
        mock_processor.add_artist_to_title = False
        mock_processor.remove_artists_in_title = False

        result = initialize_processor(config)

        assert result is None
        mock_processor_class.assert_called_once_with(config)
        # Verify the disabled message is shown
        assert mock_echo.call_count == 1  # Should show single disabled message
        mock_processor.extract_original_metadata.assert_not_called()


class TestGetCollectionToProcess:
    """Test get_collection_to_process function."""

    def test_get_collection_with_tracks(self):
        """Test getting collection with tracks including nested playlists."""
        mock_rekordbox = MagicMock()
        mock_collection = MagicMock()
        mock_tracks = [MagicMock(), MagicMock()]

        # Create nested playlist structure to test recursive counting
        child_playlist = create_mock_playlist("Child Playlist", tracks=[MagicMock()])

        parent_playlist = create_mock_playlist(
            "Parent Playlist", tracks=[], children=[child_playlist]
        )

        regular_playlist = create_mock_playlist("Regular Playlist", tracks=[MagicMock()])

        mock_playlists = [parent_playlist, regular_playlist]

        mock_collection.playlists = mock_playlists
        mock_collection.get_all_tracks.return_value = mock_tracks
        mock_rekordbox.get_filtered_collection.return_value = mock_collection

        with patch("fortherekord.main.click.echo"), patch("builtins.print"):
            collection = get_collection_to_process(mock_rekordbox)

        assert collection == mock_collection
        mock_rekordbox.get_filtered_collection.assert_called_once_with()
        mock_collection.get_all_tracks.assert_called_once()
        # Verify display_tree was called on each playlist
        for playlist in mock_playlists:
            playlist.display_tree.assert_called_once_with(1)


class TestProcessTracks:
    """Test process_tracks function."""

    def test_process_tracks_success(self):
        """Test successful track processing."""
        # Create test tracks using utility
        original_track = create_track()

        # Setup mocks
        mock_rekordbox = MagicMock()
        mock_processor = MagicMock()

        mock_rekordbox.update_track_metadata.return_value = True
        mock_rekordbox.save_changes.return_value = 1  # Return count of saved tracks

        # Create a mock collection with the track
        mock_collection = create_collection(tracks=[original_track])

        with silence_click_echo():
            process_tracks(mock_collection, mock_rekordbox, mock_processor)

        # Verify calls
        mock_processor.process_track.assert_called()
        mock_rekordbox.save_changes.assert_called_once()
        # update_track_metadata should NOT be called from process_tracks anymore
        mock_rekordbox.update_track_metadata.assert_not_called()

    def test_process_tracks_no_changes(self):
        """Test track processing when no changes are needed."""

        # Setup mocks
        mock_rekordbox = MagicMock()
        mock_processor = MagicMock()

        mock_rekordbox.save_changes.return_value = 0  # No tracks were modified

        # Create a mock collection with no changed tracks
        mock_collection = create_collection(tracks=[create_track()])
        with silence_click_echo():
            process_tracks(mock_collection, mock_rekordbox, mock_processor)

        # Verify save_changes was called (but returned 0)
        mock_rekordbox.save_changes.assert_called_once()
        mock_rekordbox.update_track_metadata.assert_not_called()

    def test_process_tracks_update_failure(self):
        """Test track processing when update fails."""
        # enhanced_track not used since we're testing in-place modification

        # Setup mocks
        mock_rekordbox = MagicMock()
        mock_processor = MagicMock()

        mock_rekordbox.save_changes.return_value = 0  # No tracks saved due to failure

        # Create mock collection
        mock_collection = create_collection(tracks=[create_track()])

        with silence_click_echo():
            process_tracks(mock_collection, mock_rekordbox, mock_processor)

    def test_process_tracks_save_failure(self):
        """Test track processing when save fails."""

        # Setup mocks
        mock_rekordbox = MagicMock()
        mock_processor = MagicMock()

        mock_rekordbox.save_changes.return_value = 0  # Save returns 0 (no tracks saved)

        # Create mock collection
        mock_collection = create_collection(tracks=[create_track()])

        with silence_click_echo():
            process_tracks(mock_collection, mock_rekordbox, mock_processor)

    def test_process_tracks_dry_run_with_changes(self):
        """Test track processing in dry-run mode with changes."""

        # Setup mocks - in dry run mode, save_changes should NOT be called
        mock_rekordbox = Mock()
        mock_processor = Mock()

        # Create mock collection with tracks that have changes
        track_with_changes = create_track()
        mock_collection = create_collection(tracks=[track_with_changes])
        # Ensure get_changed_tracks returns the track (indicating it has changes)
        mock_collection.get_changed_tracks = Mock(return_value=[track_with_changes])

        with silence_click_echo():
            process_tracks(mock_collection, mock_rekordbox, mock_processor, dry_run=True)

        # Verify save_changes was NOT called in dry-run mode
        mock_rekordbox.save_changes.assert_not_called()

    def test_process_tracks_dry_run_no_changes(self):
        """Test track processing in dry-run mode when no changes are needed."""
        # Setup mocks
        mock_rekordbox = Mock()
        mock_processor = Mock()

        # Create a mock collection with no changed tracks
        mock_collection = create_collection(tracks=[create_track()])
        # Override get_changed_tracks to return empty list (no changes)
        mock_collection.get_changed_tracks = Mock(return_value=[])

        with silence_click_echo():
            process_tracks(mock_collection, mock_rekordbox, mock_processor, dry_run=True)

        # Verify save_changes was NOT called in dry-run mode
        mock_rekordbox.save_changes.assert_not_called()


class TestCLIIntegration:
    """Test CLI integration with error handling."""

    @patch("fortherekord.main.create_default_config")
    @patch("fortherekord.main.config_load_config")
    def test_cli_no_config(self, mock_load_config, mock_create_default):
        """Test CLI when config is missing."""
        mock_load_config.return_value = {}

        result = run_cli_command([])
        assert_successful_command(result)
        assert "Error: rekordbox library_path not configured" in result.output
        mock_create_default.assert_called_once()

    @patch("fortherekord.main.load_config")
    @patch("fortherekord.main.load_library")
    def test_cli_rekordbox_running(self, mock_load_library, mock_load_config):
        """Test CLI when Rekordbox is running."""
        mock_load_config.return_value = {"rekordbox": {"library_path": "/test/db.edb"}}
        mock_load_library.side_effect = RuntimeError("Rekordbox is currently running")

        result = run_cli_command([])
        assert_successful_command(result)  # CLI handles the error gracefully

    @patch("fortherekord.main.load_config")
    @patch("fortherekord.main.load_library")
    def test_cli_file_not_found(self, mock_load_library, mock_load_config):
        """Test CLI when database file doesn't exist."""
        mock_load_config.return_value = {"rekordbox": {"library_path": "/test/db.edb"}}
        mock_load_library.side_effect = FileNotFoundError()

        result = run_cli_command([])
        assert_successful_command(result)
        assert "Error: Rekordbox database not found" in result.output

    @patch("fortherekord.main.load_config")
    def test_cli_file_not_found_direct(self, mock_load_config):
        """Test CLI when database file doesn't exist - direct path test."""
        # Set up config to point to a non-existent database file
        mock_load_config.return_value = {"rekordbox": {"library_path": "/nonexistent/path/db.edb"}}

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
        mock_load_config.return_value = {"rekordbox": {"library_path": "/test/db.edb"}}
        mock_load_library.return_value = Mock()
        mock_init_processor.return_value = Mock()
        mock_collection = Mock()
        mock_collection.get_all_tracks = Mock(return_value=[])  # No tracks found
        mock_get_collection.return_value = mock_collection

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
        mock_load_config.return_value = {
            "rekordbox": {"library_path": "/test/db.edb"},
            "processor": {"add_key_to_title": True}  # Add processor config so it gets called
        }
        mock_rekordbox = Mock()
        mock_processor = Mock()
        mock_tracks = [Mock(), Mock()]  # Some tracks to process
        mock_collection = Mock()
        mock_collection.get_all_tracks = Mock(return_value=mock_tracks)

        mock_load_library.return_value = mock_rekordbox
        mock_init_processor.return_value = mock_processor
        mock_get_collection.return_value = mock_collection

        result = run_cli_command([])
        assert result.exit_code == 0
        mock_process_tracks.assert_called_once_with(
            mock_collection, mock_rekordbox, mock_processor, False
        )

    @patch("fortherekord.main.load_config")
    @patch("fortherekord.main.load_library")
    def test_cli_os_error(self, mock_load_library, mock_load_config):
        """Test CLI when OS error occurs."""
        mock_load_config.return_value = {"rekordbox": {"library_path": "/test/db.edb"}}
        mock_load_library.side_effect = OSError("Permission denied")

        result = run_cli_command([])
        assert_successful_command(result)
        assert "Error loading Rekordbox library: Permission denied" in result.output

    @patch("fortherekord.main.load_config")
    @patch("fortherekord.main.load_library")
    @patch("fortherekord.main.SpotifyLibrary")
    @patch("fortherekord.main.PlaylistSyncService")
    @patch("fortherekord.main.get_collection_to_process")
    @patch("fortherekord.main.initialize_processor")
    @patch("fortherekord.main.process_tracks")
    def test_cli_successful_spotify_sync(
        self,
        mock_process_tracks,
        mock_initialize_processor,
        mock_get_collection,
        mock_sync_service_class,
        mock_spotify_class,
        mock_load_library,
        mock_load_config,
    ):
        """Test CLI with successful Spotify sync workflow."""
        # Mock config with Spotify credentials and processor config
        mock_load_config.return_value = {
            "rekordbox": {"library_path": "/test/db.edb"},
            "processor": {"add_key_to_title": True},  # Add processor config so it gets called
            "spotify": {
                "client_id": "test_client_id",
                "client_secret": "test_client_secret",
            },
        }

        # Mock successful library loading
        mock_rekordbox = Mock()

        # Create mock playlists with proper attributes
        sample_track = create_track()
        mock_playlist1 = create_mock_playlist("Test Playlist 1", [])
        mock_playlist2 = create_mock_playlist("Test Playlist 2", [sample_track])
        mock_collection = create_collection(playlists=[mock_playlist1, mock_playlist2])

        # Need to provide tracks for the CLI to continue to Spotify sync
        mock_get_collection.return_value = mock_collection

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
        mock_sync_service.sync_collection.assert_called_once_with(mock_collection, dry_run=False)

        # Verify process_tracks was called with dry_run=False
        mock_process_tracks.assert_called_once_with(
            mock_collection, mock_rekordbox, mock_initialize_processor.return_value, False
        )

        # Check output messages
        assert "Authenticated with Spotify as user: test_user" in result.output
        assert "Found 2 Rekordbox playlists to sync" in result.output
        assert "Spotify playlist sync complete" in result.output

    @patch("fortherekord.main.load_config")
    @patch("fortherekord.main.load_library")
    @patch("fortherekord.main.SpotifyLibrary")
    @patch("fortherekord.main.get_collection_to_process")
    @patch("fortherekord.main.initialize_processor")
    @patch("fortherekord.main.process_tracks")
    def test_cli_spotify_auth_failure(
        self,
        mock_process_tracks,
        mock_initialize_processor,
        mock_get_collection,
        mock_spotify_class,
        mock_load_library,
        mock_load_config,
    ):
        """Test CLI when Spotify authentication fails."""
        # Mock config with Spotify credentials
        mock_load_config.return_value = {
            "rekordbox": {"library_path": "/test/db.edb"},
            "spotify": {
                "client_id": "test_client_id",
                "client_secret": "test_client_secret",
            },
        }

        # Mock successful library loading
        mock_rekordbox = Mock()
        mock_load_library.return_value = mock_rekordbox

        # Create a sample track so Spotify sync is attempted
        sample_track = create_track()
        mock_playlist = create_mock_playlist("Test Playlist", [sample_track])
        mock_collection = create_collection(playlists=[mock_playlist])

        # Mock get_collection_to_process to return collection
        mock_get_collection.return_value = mock_collection

        # Mock Spotify authentication failure
        mock_spotify_class.side_effect = ValueError("Invalid credentials")

        result = run_cli_command([])
        assert result.exit_code == 0  # Should handle error gracefully

        # Check error handling
        assert "Failed to authenticate with Spotify: Invalid credentials" in result.output

    @patch("fortherekord.main.load_config")
    @patch("fortherekord.main.load_library")
    @patch("fortherekord.main.SpotifyLibrary")
    @patch("fortherekord.main.PlaylistSyncService")
    @patch("fortherekord.main.get_collection_to_process")
    @patch("fortherekord.main.initialize_processor")
    @patch("fortherekord.main.process_tracks")
    def test_cli_dry_run_mode(
        self,
        mock_process_tracks,
        mock_initialize_processor,
        mock_get_collection,
        mock_sync_service_class,
        mock_spotify_class,
        mock_load_library,
        mock_load_config,
    ):
        """Test CLI with --dry-run flag passes dry_run=True to relevant functions."""
        # Mock config with Spotify credentials and processor config
        mock_load_config.return_value = {
            "rekordbox": {"library_path": "/test/db.edb"},
            "processor": {"add_key_to_title": True},  # Add processor config so it gets called
            "spotify": {
                "client_id": "test_client_id",
                "client_secret": "test_client_secret",
            },
        }

        # Setup mocks
        mock_rekordbox = Mock()
        mock_load_library.return_value = mock_rekordbox

        # Mock collection and tracks
        sample_track = create_track()
        mock_playlist = create_mock_playlist("Test Playlist", [sample_track])
        mock_collection = create_collection(playlists=[mock_playlist])
        mock_get_collection.return_value = mock_collection

        # Mock Spotify
        mock_spotify = Mock()
        mock_spotify.user_id = "test_user"
        mock_spotify_class.return_value = mock_spotify

        # Mock sync service
        mock_sync_service = Mock()
        mock_sync_service_class.return_value = mock_sync_service

        # Run with --dry-run flag
        result = run_cli_command(["--dry-run"])
        assert_successful_command(result)

        # Verify dry_run=True was passed to the right functions
        mock_process_tracks.assert_called_once_with(
            mock_collection, mock_rekordbox, mock_initialize_processor.return_value, True
        )
        mock_sync_service.sync_collection.assert_called_once_with(mock_collection, dry_run=True)

        # The output will show the normal workflow - the key test is that
        # dry_run=True was passed correctly
        assert "Spotify playlist sync complete" in result.output

    @patch("fortherekord.main.PlaylistSyncService")
    @patch("fortherekord.main.SpotifyLibrary")
    @patch("fortherekord.main.process_tracks")
    @patch("fortherekord.main.initialize_processor")
    @patch("fortherekord.main.get_collection_to_process")
    @patch("fortherekord.main.load_library")
    @patch("fortherekord.main.load_config")
    def test_cli_processor_disabled_continues_to_spotify(
        self,
        mock_load_config,
        mock_load_library,
        mock_get_collection,
        mock_initialize_processor,
        mock_process_tracks,
        mock_spotify_class,
        mock_sync_service_class,
    ):
        """Test CLI when processor is disabled but continues to Spotify sync."""
        # Mock basic setup
        mock_load_config.return_value = {
            "rekordbox": {"library_path": "/test/db.edb"},
            "spotify": {
                "client_id": "test_id",
                "client_secret": "test_secret",
            },
        }
        mock_rekordbox = Mock()
        mock_load_library.return_value = mock_rekordbox

        # Mock collection with tracks
        sample_track = create_track()
        mock_playlist = create_mock_playlist("Test Playlist", [sample_track])
        mock_collection = create_collection(playlists=[mock_playlist])
        mock_get_collection.return_value = mock_collection

        # Mock processor as disabled (returns None)
        mock_initialize_processor.return_value = None

        # Mock Spotify
        mock_spotify = Mock()
        mock_spotify.user_id = "test_user"
        mock_spotify_class.return_value = mock_spotify

        # Mock sync service
        mock_sync_service = Mock()
        mock_sync_service_class.return_value = mock_sync_service

        result = run_cli_command([])
        assert_successful_command(result)

        # Verify process_tracks was NOT called (processor disabled)
        mock_process_tracks.assert_not_called()

        # Verify Spotify sync still happened
        mock_sync_service.sync_collection.assert_called_once_with(mock_collection, dry_run=False)

        assert "Skipping track processing (processor is disabled)" in result.output
        assert "Spotify playlist sync complete" in result.output
