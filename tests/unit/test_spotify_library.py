"""
Tests for Spotify library integration.

Tests basic Spotify API operations and authentication.
"""

import pytest
from unittest.mock import Mock, patch

from fortherekord.spotify_library import SpotifyLibrary
from .conftest import create_track


class TestSpotifyLibrary:
    """Test Spotify library functionality."""

    @pytest.fixture
    def mock_spotify_client(self):
        """Create a mock Spotify client for testing."""
        with (
            patch("fortherekord.spotify_library.spotipy.Spotify") as mock_spotify_class,
            patch("fortherekord.spotify_library.SpotifyOAuth"),
        ):

            # Setup authentication mocks
            mock_sp = Mock()
            mock_spotify_class.return_value = mock_sp
            mock_sp.current_user.return_value = {"id": "test_user"}

            # Create client
            client = SpotifyLibrary("test_id", "test_secret")

            return client, mock_sp

    @patch("fortherekord.spotify_library.spotipy.Spotify")
    @patch("fortherekord.spotify_library.SpotifyOAuth")
    def test_init_and_auth(self, mock_oauth, mock_spotify):
        """Test Spotify client initialization and authentication."""
        # Setup mocks
        mock_auth_manager = Mock()
        mock_oauth.return_value = mock_auth_manager

        mock_sp = Mock()
        mock_spotify.return_value = mock_sp
        mock_sp.current_user.return_value = {"id": "test_user"}

        # Create client
        client = SpotifyLibrary("test_client_id", "test_client_secret")

        # Verify OAuth setup
        mock_oauth.assert_called_once_with(
            client_id="test_client_id",
            client_secret="test_client_secret",
            redirect_uri="http://127.0.0.1:8888/callback",
            scope=(
                "playlist-read-private playlist-modify-public "
                "playlist-modify-private user-library-read"
            ),
            cache_path=".spotify_cache",
        )

        # Verify Spotify client setup
        mock_spotify.assert_called_once_with(auth_manager=mock_auth_manager)
        mock_sp.current_user.assert_called_once()

        assert client.user_id == "test_user"
        assert client.sp == mock_sp

    def test_search_track_found(self, mock_spotify_client):
        """Test track search with results."""
        client, mock_sp = mock_spotify_client

        # Mock search response
        mock_sp.search.return_value = {"tracks": {"items": [{"id": "spotify_track_id_123"}]}}

        result = client.search_track("Test Song", "Test Artist")

        assert result == "spotify_track_id_123"
        mock_sp.search.assert_called_once_with(
            q="track:Test Song artist:Test Artist", type="track", limit=1
        )

    def test_search_track_not_found(self, mock_spotify_client):
        """Test track search with no results."""
        client, mock_sp = mock_spotify_client

        # Mock empty search response
        mock_sp.search.return_value = {"tracks": {"items": []}}

        result = client.search_track("Nonexistent Song", "Unknown Artist")

        assert result is None
        mock_sp.search.assert_called_once()

    def test_get_playlists(self, mock_spotify_client):
        """Test getting user playlists."""
        client, mock_sp = mock_spotify_client

        # Mock playlists response
        mock_sp.current_user_playlists.return_value = {
            "items": [
                {"id": "playlist_1", "name": "My Playlist", "owner": {"id": "test_user"}},
                {
                    "id": "playlist_2",
                    "name": "Other Playlist",
                    "owner": {"id": "other_user"},  # Not owned by current user
                },
            ],
            "next": None,
        }

        playlists = client.get_playlists()

        # Should only return playlists owned by current user
        assert len(playlists) == 1
        assert playlists[0].id == "playlist_1"
        assert playlists[0].name == "My Playlist"

    def test_get_playlists_with_ignore_list(self, mock_spotify_client):
        """Test getting playlists with ignore list."""
        client, mock_sp = mock_spotify_client

        # Mock playlists response
        mock_sp.current_user_playlists.return_value = {
            "items": [
                {"id": "playlist_1", "name": "Keep This", "owner": {"id": "test_user"}},
                {"id": "playlist_2", "name": "Ignore This", "owner": {"id": "test_user"}},
            ],
            "next": None,
        }

        playlists = client.get_playlists(ignore_playlists=["Ignore This"])

        assert len(playlists) == 1
        assert playlists[0].name == "Keep This"

    def test_get_playlist_tracks(self, mock_spotify_client):
        """Test getting tracks from a playlist."""
        client, mock_sp = mock_spotify_client

        # Mock playlist tracks response
        mock_sp.playlist_tracks.return_value = {
            "items": [
                {
                    "track": {
                        "id": "track_1",
                        "name": "Song 1",
                        "type": "track",
                        "artists": [{"name": "Artist 1"}],
                    }
                },
                {
                    "track": {
                        "id": "track_2",
                        "name": "Song 2",
                        "type": "track",
                        "artists": [{"name": "Artist 2"}],
                    }
                },
            ],
            "next": None,
        }

        tracks = client.get_playlist_tracks("playlist_123")

        assert len(tracks) == 2
        assert tracks[0].id == "track_1"
        assert tracks[0].title == "Song 1"
        assert tracks[0].artist == "Artist 1"
        assert tracks[1].id == "track_2"
        assert tracks[1].title == "Song 2"
        assert tracks[1].artist == "Artist 2"

    def test_create_playlist(self, mock_spotify_client):
        """Test creating a new playlist with tracks."""
        client, mock_sp = mock_spotify_client

        # Mock playlist creation response
        mock_sp.user_playlist_create.return_value = {"id": "new_playlist_id"}

        # Mock search for tracks
        mock_sp.search.side_effect = [
            {"tracks": {"items": [{"id": "spotify_track_1"}]}},
            {"tracks": {"items": [{"id": "spotify_track_2"}]}},
        ]

        tracks = [
            create_track(track_id="1", title="Song 1", artist="Artist 1"),
            create_track(track_id="2", title="Song 2", artist="Artist 2"),
        ]

        playlist_id = client.create_playlist("New Playlist", tracks)

        assert playlist_id == "new_playlist_id"

        # Verify playlist creation
        mock_sp.user_playlist_create.assert_called_once_with(
            user="test_user", name="New Playlist", public=False
        )

        # Verify tracks were searched and added
        assert mock_sp.search.call_count == 2
        mock_sp.playlist_add_items.assert_called_once_with(
            "new_playlist_id", ["spotify_track_1", "spotify_track_2"]
        )

    def test_delete_playlist(self, mock_spotify_client):
        """Test deleting a playlist."""
        client, mock_sp = mock_spotify_client

        client.delete_playlist("playlist_to_delete")

        mock_sp.current_user_unfollow_playlist.assert_called_once_with("playlist_to_delete")

    def test_unsupported_operations(self, mock_spotify_client):
        """Test that unsupported operations raise NotImplementedError."""
        client, mock_sp = mock_spotify_client

        with pytest.raises(NotImplementedError):
            client.follow_artist("Artist Name")

        with pytest.raises(NotImplementedError):
            client.get_followed_artists()

        with pytest.raises(NotImplementedError):
            client.get_all_tracks()

        with pytest.raises(NotImplementedError):
            client.update_track_metadata("track_id", "new_title", "new_artist")

        with pytest.raises(NotImplementedError):
            client.save_changes([])


class TestSpotifyLibraryErrorConditions:
    """Test error conditions in Spotify library."""

    @patch("fortherekord.spotify_library.SpotifyLibrary._authenticate")
    def test_search_track_not_authenticated(self, mock_authenticate):
        """Test searching track when not authenticated."""
        client = SpotifyLibrary("client_id", "client_secret")
        client.sp = None  # Not authenticated

        with pytest.raises(RuntimeError, match="Spotify client not authenticated"):
            client.search_track("Test Song", "Test Artist")

    @patch("fortherekord.spotify_library.SpotifyLibrary._authenticate")
    def test_get_playlists_not_authenticated(self, mock_authenticate):
        """Test getting playlists when not authenticated."""
        client = SpotifyLibrary("client_id", "client_secret")
        client.sp = None  # Not authenticated

        with pytest.raises(RuntimeError, match="Spotify client not authenticated"):
            client.get_playlists()

    def test_get_playlists_with_pagination(self, mock_spotify_client):
        """Test getting playlists with pagination."""
        client, mock_sp = mock_spotify_client

        # Mock pagination: first call returns results with 'next', second call returns final results
        first_page_results = {
            "items": [{"id": "playlist1", "name": "First Playlist", "owner": {"id": "test_user"}}],
            "next": "next_page_url",
        }

        second_page_results = {
            "items": [{"id": "playlist2", "name": "Second Playlist", "owner": {"id": "test_user"}}],
            "next": None,  # No more pages
        }

        # Configure mock to return different results for each call
        mock_sp.current_user_playlists.return_value = first_page_results
        mock_sp.next.return_value = second_page_results

        playlists = client.get_playlists()

        # Should have called pagination
        mock_sp.current_user_playlists.assert_called_once()
        mock_sp.next.assert_called_once_with(first_page_results)

        # Should return playlists from both pages
        assert len(playlists) == 2
        assert playlists[0].name == "First Playlist"
        assert playlists[1].name == "Second Playlist"

    def test_get_playlist_tracks_with_pagination(self, mock_spotify_client):
        """Test getting playlist tracks with pagination."""
        client, mock_sp = mock_spotify_client

        # Mock pagination for playlist tracks
        first_page_results = {
            "items": [
                {
                    "track": {
                        "id": "track1",
                        "name": "Song 1",
                        "type": "track",
                        "artists": [{"name": "Artist 1"}],
                    }
                }
            ],
            "next": "next_page_url",
        }

        second_page_results = {
            "items": [
                {
                    "track": {
                        "id": "track2",
                        "name": "Song 2",
                        "type": "track",
                        "artists": [{"name": "Artist 2"}],
                    }
                }
            ],
            "next": None,  # No more pages
        }

        # Configure mock to return different results for each call
        mock_sp.playlist_tracks.return_value = first_page_results
        mock_sp.next.return_value = second_page_results

        tracks = client.get_playlist_tracks("playlist_id")

        # Should have called pagination
        mock_sp.playlist_tracks.assert_called_once_with("playlist_id")
        mock_sp.next.assert_called_once_with(first_page_results)

        # Should return tracks from both pages
        assert len(tracks) == 2
        assert tracks[0].title == "Song 1"
        assert tracks[1].title == "Song 2"

    def test_get_playlists_pagination_with_client_none(self, mock_spotify_client):
        """Test pagination handling when client becomes None."""
        client, mock_sp = mock_spotify_client

        # Mock pagination where client becomes None during iteration
        first_page_results = {
            "items": [{"id": "playlist1", "name": "First Playlist", "owner": {"id": "test_user"}}],
            "next": "next_page_url",
        }

        mock_sp.current_user_playlists.return_value = first_page_results

        # Simulate client becoming None after first call
        def side_effect_next(results):
            client.sp = None  # Client becomes None
            return None

        mock_sp.next.side_effect = side_effect_next

        playlists = client.get_playlists()

        # Should handle the case where client becomes None
        assert len(playlists) == 1
        assert playlists[0].name == "First Playlist"

    @patch("fortherekord.spotify_library.SpotifyLibrary._authenticate")
    def test_get_playlist_tracks_not_authenticated(self, mock_authenticate):
        """Test getting playlist tracks when not authenticated."""
        client = SpotifyLibrary("client_id", "client_secret")
        client.sp = None  # Not authenticated

        with pytest.raises(RuntimeError, match="Spotify client not authenticated"):
            client.get_playlist_tracks("playlist_id")

    @patch("fortherekord.spotify_library.SpotifyLibrary._authenticate")
    def test_create_playlist_not_authenticated(self, mock_authenticate):
        """Test creating playlist when not authenticated."""
        client = SpotifyLibrary("client_id", "client_secret")
        client.sp = None  # Not authenticated

        with pytest.raises(RuntimeError, match="Spotify client not authenticated"):
            client.create_playlist("Test Playlist", [])

    @patch("fortherekord.spotify_library.SpotifyLibrary._authenticate")
    def test_delete_playlist_not_authenticated(self, mock_authenticate):
        """Test deleting playlist when not authenticated."""
        client = SpotifyLibrary("client_id", "client_secret")
        client.sp = None  # Not authenticated

        with pytest.raises(RuntimeError, match="Spotify client not authenticated"):
            client.delete_playlist("playlist_id")

    def test_get_tracks_from_playlists(self, mock_spotify_client):
        """Test getting all tracks from all playlists."""
        client, mock_sp = mock_spotify_client

        # Mock playlists
        mock_playlist = Mock()
        mock_playlist.id = "playlist1"
        mock_playlist.name = "Test Playlist"
        client.get_playlists = Mock(return_value=[mock_playlist])

        # Mock tracks from playlist
        mock_track = create_track(
            track_id="track1", title="Test Song", artist="Test Artist", key="Am"
        )
        client.get_playlist_tracks = Mock(return_value=[mock_track])

        tracks = client.get_tracks_from_playlists()

        assert len(tracks) == 1
        assert tracks[0].title == "Test Song"

    @patch("fortherekord.spotify_library.SpotifyLibrary._authenticate")
    def test_update_track_metadata_not_implemented(self, mock_authenticate):
        """Test that update_track_metadata raises NotImplementedError."""
        client = SpotifyLibrary("client_id", "client_secret")

        with pytest.raises(NotImplementedError, match="Track metadata updates not supported"):
            client.update_track_metadata("track_id", "new_title", "new_artist")
