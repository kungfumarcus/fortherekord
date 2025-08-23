"""
Test Configuration and Fixtures

Centralized configuration and fixtures for all tests.
"""

import os
import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from fortherekord.models import Track, Playlist, Collection


def cleanup_test_dump_file():
    """
    Clean up the test dump file created by save_changes() in test mode.

    This should be called in finally blocks of tests that call save_changes()
    without overriding the FORTHEREKORD_TEST_DUMP_FILE environment variable.
    """
    dump_file = os.getenv("FORTHEREKORD_TEST_DUMP_FILE", "test_changes_dump.json")
    if Path(dump_file).exists():
        try:
            Path(dump_file).unlink()
        except OSError:
            pass  # File might be in use or already deleted


@pytest.fixture
def temp_test_file():
    """
    Create a temporary test file that gets cleaned up automatically.

    Returns:
        Path: Path to a temporary file that will be cleaned up
    """
    import tempfile

    # Create a temporary file
    fd, path = tempfile.mkstemp(suffix=".test")
    os.close(fd)

    yield Path(path)

    # Clean up
    try:
        Path(path).unlink()
    except OSError:
        pass


# Common Test Data Fixtures


@pytest.fixture
def default_processor_config():
    """Create default processor configuration for tests with Spotify credentials."""
    return {
        "add_key_to_title": True,
        "add_artist_to_title": True,
        "remove_artists_in_title": True,
        "replace_in_title": [],
        "ignore_playlists": [],
    }


@pytest.fixture
def sample_track():
    """Create a sample track for testing."""
    return create_track()


@pytest.fixture
def sample_track_no_key():
    """Create a sample track without key for testing."""
    return create_track(key=None)


def create_track(
    track_id="1",
    title="Test Song",
    artists="Test Artist",
    key="Am",
    as_mock=False,
    original_title=None,
    original_artists=None,
):
    """
    Create a track for testing.

    Args:
        track_id: Track ID (str)
        title: Track title
        artists: Artist name (None for missing artists)
        key: Musical key (default: "Am")
        as_mock: If True, returns Mock object for pyrekordbox simulation.
                If False, returns actual Track model object.
        original_title: Original title (defaults to title if not specified)
        original_artists: Original artists (defaults to artists if not specified)

    Returns:
        Track model object or Mock object representing a Rekordbox track
    """
    if as_mock:
        # Create mock object for pyrekordbox database simulation
        track = Mock()
        track.ID = int(track_id) if track_id.isdigit() else track_id
        track.Title = title
        track.Key = key
        track.Length = 180.5

        # Only create artists mock if artists is not None
        if artists is not None:
            artist_mock = Mock()
            artist_mock.Name = artists
            track.Artist = artist_mock
        else:
            track.Artist = None

        return track
    else:
        # Create actual Track model object
        track = Track(
            id=track_id,
            title=title,
            artists=artists,
            original_title=original_title or title,
            original_artists=original_artists or artists,
            key=key,
        )
        return track


def create_playlist(
    playlist_id="1",
    name="Test Playlist",
    tracks=None,
    parent_id=None,
    seq=1,
    as_mock=False,
):
    """
    Create a playlist for testing.

    Args:
        playlist_id: Playlist ID (str)
        name: Playlist name
        tracks: List of tracks (will create empty list if None)
        parent_id: Parent playlist ID (None for top-level)
        seq: Sequence number for sorting
        as_mock: If True, returns Mock object for pyrekordbox simulation.
                If False, returns actual Playlist model object.

    Returns:
        Playlist model object or Mock object representing a Rekordbox playlist
    """
    if tracks is None:
        tracks = []

    if as_mock:
        # Create mock object for pyrekordbox database simulation
        playlist = Mock()
        playlist.ID = int(playlist_id) if playlist_id.isdigit() else playlist_id
        playlist.Name = name
        playlist.Seq = seq

        # Handle parent relationship
        if parent_id is not None:
            parent = Mock()
            parent.ID = int(parent_id) if parent_id.isdigit() else parent_id
            playlist.Parent = parent
        else:
            playlist.Parent = None

        return playlist
    else:
        # Create actual Playlist model object
        from fortherekord.models import Playlist

        playlist = Playlist(
            id=playlist_id,
            name=name,
            tracks=tracks,
            parent_id=parent_id,
        )
        return playlist


def create_collection(playlists: list = None, tracks: list = None):
    """Helper function to create a mock collection from playlists."""
    from fortherekord.models import Collection

    if playlists is None:
        if not (tracks is None):
            playlists = [create_playlist(tracks=tracks)]
        else:
            playlists = []

    # Extract all tracks from playlists and create tracks dictionary for efficient lookup
    tracks_dict = {}
    for playlist in playlists:
        for track in playlist.tracks:
            tracks_dict[track.id] = track

    return Collection(playlists=playlists, tracks=tracks_dict)


@pytest.fixture
def sample_tracks():
    """Create a list of sample tracks for testing."""
    return [
        create_track(
            track_id="1",
            title="Song 1",
            artists="Artist 1",
            key="Am",
        ),
        create_track(track_id="2", title="Song 2", artists="Artist 2", key="Dm"),
        create_track(track_id="3", title="Song 3", artists="Artist 3", key="Gm"),
    ]


@pytest.fixture
def sample_playlist(sample_tracks):
    """Create a sample playlist with tracks for testing."""
    return Playlist(id="playlist_1", name="Test Playlist", tracks=sample_tracks[:2])


@pytest.fixture
def sample_collection(sample_playlist):
    """Create a sample collection with playlists for testing."""
    return Collection(playlists=[sample_playlist], tracks={})


# Mock Fixtures


@pytest.fixture
def mock_rekordbox():
    """Create a mock Rekordbox library for testing."""
    mock = Mock()
    mock_collection = Mock()
    mock_collection.get_all_tracks.return_value = []
    mock_collection.playlists = []
    mock.get_collection.return_value = mock_collection
    return mock


@pytest.fixture
def mock_spotify_client():
    """Create a mock Spotify client for testing."""
    with (
        patch("fortherekord.spotify_library.spotipy.Spotify") as mock_spotify_class,
        patch("fortherekord.spotify_library.SpotifyOAuth"),
    ):

        mock_sp = Mock()
        mock_spotify_class.return_value = mock_sp
        mock_sp.current_user.return_value = {"id": "test_user"}

        from fortherekord.spotify_library import SpotifyLibrary

        client = SpotifyLibrary("client_id", "client_secret")

        return client, mock_sp


@pytest.fixture
def mock_metadata_processor():
    """Create a mock metadata processor for testing."""
    mock = Mock()
    mock.enhance_track_title = Mock(side_effect=lambda track: track)
    return mock


# Common Mock Patterns


def create_mock_spotify_search_results(tracks_found=True):
    """
    Create mock Spotify search results.

    Args:
        tracks_found: If True, returns mock track IDs. If False, returns None.

    Returns:
        List of track IDs or None values based on tracks_found
    """
    if tracks_found:
        return ["spotify_track_1", "spotify_track_2", "spotify_track_3"]
    else:
        return [None, None, None]


# Test Utilities


def silence_click_echo():
    """Context manager to silence click.echo calls in tests."""
    return patch("fortherekord.main.click.echo")


def silence_print():
    """Context manager to silence print calls in tests."""
    return patch("builtins.print")
