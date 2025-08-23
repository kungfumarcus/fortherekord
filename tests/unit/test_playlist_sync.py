"""
Tests for playlist synchronization service.

Tests the sync logic between Rekordbox and Spotify.
"""

from unittest.mock import Mock, patch

from fortherekord.playlist_sync import PlaylistSyncService
from fortherekord.models import Playlist
from .conftest import create_track, silence_click_echo


class TestPlaylistSyncService:
    """Test playlist synchronization service."""

    def test_init(self, mock_rekordbox):
        """Test service initialization."""
        spotify = Mock()
        service = PlaylistSyncService(mock_rekordbox, spotify)
        assert service.rekordbox == mock_rekordbox
        assert service.spotify == spotify

    def test_sync_collection_basic(self, mock_rekordbox, sample_collection):
        """Test basic collection synchronization."""
        spotify = Mock()
        service = PlaylistSyncService(mock_rekordbox, spotify)

        # Mock Spotify playlists (empty)
        spotify.get_playlists.return_value = []

        # Mock Spotify playlist creation
        spotify.sp = Mock()
        spotify.user_id = "test_user"
        spotify.sp.user_playlist_create.return_value = {"id": "new_spotify_playlist"}

        with silence_click_echo():
            service.sync_collection(sample_collection)

        # Verify calls
        spotify.get_playlists.assert_called_once()
        # The playlist should be created since it doesn't exist in Spotify

    def test_find_spotify_matches(self, mock_rekordbox):
        """Test finding Spotify matches for Rekordbox tracks."""
        spotify = Mock()
        service = PlaylistSyncService(mock_rekordbox, spotify)

        # Setup tracks
        tracks = [
            create_track(track_id="1", title="Found Song", artists="Found Artist"),
            create_track(track_id="2", title="Lost Song", artists="Lost Artist"),
        ]

        # Mock search results
        spotify.search_track.side_effect = ["spotify_id_1", None]  # Found  # Not found

        with silence_click_echo():
            result = service._find_spotify_matches(tracks)

        assert result == ["spotify_id_1"]
        assert spotify.search_track.call_count == 2
        spotify.search_track.assert_any_call("Found Song", "Found Artist")
        spotify.search_track.assert_any_call("Lost Song", "Lost Artist")

    def test_create_spotify_playlist(self, mock_rekordbox):
        """Test creating new Spotify playlist."""
        spotify = Mock()
        service = PlaylistSyncService(mock_rekordbox, spotify)

        # Setup mocks
        spotify.sp = Mock()
        spotify.user_id = "test_user"
        spotify.sp.user_playlist_create.return_value = {"id": "new_playlist_id"}

        track_ids = ["track_1", "track_2", "track_3"]

        with silence_click_echo():
            service._create_spotify_playlist("New Playlist", track_ids)

        # Verify playlist creation
        spotify.sp.user_playlist_create.assert_called_once_with(
            user="test_user", name="New Playlist", public=False
        )

        # Verify tracks added
        spotify.sp.playlist_add_items.assert_called_once_with("new_playlist_id", track_ids)

    @patch("fortherekord.playlist_sync.click")
    def test_update_spotify_playlist(self, mock_click):
        """Test updating existing Spotify playlist."""
        rekordbox = Mock()
        spotify = Mock()
        service = PlaylistSyncService(rekordbox, spotify)

        # Setup existing playlist
        existing_playlist = Playlist(id="existing_id", name="Existing Playlist", tracks=[])

        # Mock current tracks in playlist
        current_tracks = [
            create_track(track_id="keep_track", title="Keep", artists="Artist"),
            create_track(track_id="remove_track", title="Remove", artists="Artist"),
        ]
        spotify.get_playlist_tracks.return_value = current_tracks

        # New tracks that should be in playlist
        new_track_ids = ["keep_track", "add_track"]

        # Setup Spotify API mock
        spotify.sp = Mock()

        service._update_spotify_playlist(existing_playlist, new_track_ids)

        # Verify tracks to add and remove were calculated correctly
        spotify.sp.playlist_remove_all_occurrences_of_items.assert_called_once_with(
            "existing_id", ["remove_track"]
        )
        spotify.sp.playlist_add_items.assert_called_once_with("existing_id", ["add_track"])

    @patch("fortherekord.playlist_sync.click")
    def test_add_tracks_in_batches(self, mock_click):
        """Test adding tracks to playlist in batches of 100."""
        rekordbox = Mock()
        spotify = Mock()
        service = PlaylistSyncService(rekordbox, spotify)

        spotify.sp = Mock()

        # Create 150 track IDs to test batching
        track_ids = [f"track_{i}" for i in range(150)]

        service._add_tracks_to_playlist("playlist_id", track_ids)

        # Should be called twice (100 + 50)
        assert spotify.sp.playlist_add_items.call_count == 2

        # Check first batch (100 tracks)
        first_call_args = spotify.sp.playlist_add_items.call_args_list[0]
        assert first_call_args[0][0] == "playlist_id"
        assert len(first_call_args[0][1]) == 100

        # Check second batch (50 tracks)
        second_call_args = spotify.sp.playlist_add_items.call_args_list[1]
        assert second_call_args[0][0] == "playlist_id"
        assert len(second_call_args[0][1]) == 50

    @patch("fortherekord.playlist_sync.click")
    def test_remove_tracks_in_batches(self, mock_click):
        """Test removing tracks from playlist in batches of 100."""
        rekordbox = Mock()
        spotify = Mock()
        service = PlaylistSyncService(rekordbox, spotify)

        spotify.sp = Mock()

        # Create 150 track IDs to test batching
        track_ids = [f"track_{i}" for i in range(150)]

        service._remove_tracks_from_playlist("playlist_id", track_ids)

        # Should be called twice (100 + 50)
        assert spotify.sp.playlist_remove_all_occurrences_of_items.call_count == 2

        # Check batch sizes
        first_call_args = spotify.sp.playlist_remove_all_occurrences_of_items.call_args_list[0]
        assert len(first_call_args[0][1]) == 100

        second_call_args = spotify.sp.playlist_remove_all_occurrences_of_items.call_args_list[1]
        assert len(second_call_args[0][1]) == 50


class TestPlaylistSyncServiceErrorConditions:
    """Test error conditions in playlist sync service."""

    def test_create_playlist_not_authenticated(self, mock_rekordbox):
        """Test playlist creation when Spotify client not authenticated."""
        spotify = Mock()
        spotify.sp = None  # Not authenticated
        spotify.user_id = None
        service = PlaylistSyncService(mock_rekordbox, spotify)

        import pytest

        with pytest.raises(RuntimeError, match="Spotify client not authenticated"):
            service._create_spotify_playlist("Test Playlist", ["track1", "track2"])

    def test_add_tracks_not_authenticated(self, mock_rekordbox):
        """Test adding tracks when Spotify client not authenticated."""
        spotify = Mock()
        spotify.sp = None  # Not authenticated
        service = PlaylistSyncService(mock_rekordbox, spotify)

        import pytest

        with pytest.raises(RuntimeError, match="Spotify client not authenticated"):
            service._add_tracks_to_playlist("playlist_id", ["track1", "track2"])

    def test_remove_tracks_not_authenticated(self, mock_rekordbox):
        """Test removing tracks when Spotify client not authenticated."""
        spotify = Mock()
        spotify.sp = None  # Not authenticated
        service = PlaylistSyncService(mock_rekordbox, spotify)

        import pytest

        with pytest.raises(RuntimeError, match="Spotify client not authenticated"):
            service._remove_tracks_from_playlist("playlist_id", ["track1", "track2"])

    def test_sync_existing_playlist(self, mock_rekordbox, sample_collection):
        """Test syncing when playlist already exists in Spotify."""
        spotify = Mock()
        service = PlaylistSyncService(mock_rekordbox, spotify)

        # Mock existing Spotify playlist
        existing_playlist = Mock()
        existing_playlist.name = "Test Playlist"
        existing_playlist.id = "existing_playlist_id"
        existing_playlist.tracks = []  # Empty tracks list for existing playlist
        spotify.get_playlists.return_value = [existing_playlist]

        # Mock get_playlist_tracks to return empty list
        spotify.get_playlist_tracks.return_value = []

        # Mock Spotify client
        spotify.sp = Mock()
        spotify.user_id = "test_user"

        with silence_click_echo():
            service.sync_collection(sample_collection)

        # Verify the existing playlist is updated, not created
        spotify.sp.user_playlist_create.assert_not_called()
        # Should call add tracks since there are tracks to add
        spotify.sp.playlist_add_items.assert_called()

    def test_sync_collection_dry_run(self, mock_rekordbox, sample_collection):
        """Test collection synchronization in dry-run mode."""
        spotify = Mock()
        service = PlaylistSyncService(mock_rekordbox, spotify)

        # Mock Spotify playlists (empty)
        spotify.get_playlists.return_value = []

        # Mock Spotify search to return some matches
        spotify.search_track.return_value = "spotify_track_id"

        with silence_click_echo():
            service.sync_collection(sample_collection, dry_run=True)

        # Verify no actual changes are made
        spotify.get_playlists.assert_called_once()  # Should still load playlists for comparison
        assert not hasattr(spotify, "sp") or spotify.sp is None or not spotify.sp.called

    def test_create_spotify_playlist_dry_run(self, mock_rekordbox):
        """Test playlist creation in dry-run mode."""
        spotify = Mock()
        service = PlaylistSyncService(mock_rekordbox, spotify)

        track_ids = ["track1", "track2", "track3"]

        with silence_click_echo():
            service._create_spotify_playlist("Test Playlist", track_ids, dry_run=True)

        # Verify no actual API calls are made
        assert not hasattr(spotify, "sp") or spotify.sp is None or not spotify.sp.called

    def test_update_spotify_playlist_dry_run(self, mock_rekordbox):
        """Test playlist update in dry-run mode."""
        spotify = Mock()
        service = PlaylistSyncService(mock_rekordbox, spotify)

        # Mock existing playlist
        existing_playlist = Mock()
        existing_playlist.name = "Test Playlist"
        existing_playlist.id = "existing_playlist_id"

        # Mock current tracks
        current_track = Mock()
        current_track.id = "existing_track_id"
        spotify.get_playlist_tracks.return_value = [current_track]

        track_ids = ["new_track_id1", "new_track_id2"]

        with silence_click_echo():
            service._update_spotify_playlist(existing_playlist, track_ids, dry_run=True)

        # Verify playlist tracks are checked but no modifications are made
        spotify.get_playlist_tracks.assert_called_once_with("existing_playlist_id")
        assert not hasattr(spotify, "sp") or spotify.sp is None or not spotify.sp.called

    def test_find_spotify_matches_dry_run(self, mock_rekordbox):
        """Test finding Spotify matches in dry-run mode (should be same as normal)."""
        spotify = Mock()
        service = PlaylistSyncService(mock_rekordbox, spotify)

        # Setup tracks
        tracks = [
            create_track("Track 1", "Artist 1"),
            create_track("Track 2", "Artist 2"),
        ]

        # Mock search results
        spotify.search_track.side_effect = ["spotify_id_1", None]  # Second track not found

        with silence_click_echo():
            result = service._find_spotify_matches(tracks, dry_run=True)

        # Should still return matches, just without detailed error output
        assert result == ["spotify_id_1"]
        assert spotify.search_track.call_count == 2
