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
def sample_track():
    """Create a sample track for testing."""
    return create_sample_track()


@pytest.fixture
def sample_track_no_key():
    """Create a sample track without key for testing."""
    return create_sample_track(key=None)


def create_sample_track(
    track_id="1",
    title="Test Song",
    artist="Test Artist",
    key="Am",
):
    """Create a sample track with customizable parameters."""
    return Track(id=track_id, title=title, artist=artist, key=key)


@pytest.fixture
def sample_tracks():
    """Create a list of sample tracks for testing."""
    return [
        Track(
            id="1",
            title="Song 1",
            artist="Artist 1",
            key="Am",
        ),
        Track(id="2", title="Song 2", artist="Artist 2", key="Dm"),
        Track(id="3", title="Song 3", artist="Artist 3", key="Gm"),
    ]


@pytest.fixture
def sample_playlist(sample_tracks):
    """Create a sample playlist with tracks for testing."""
    return Playlist(id="playlist_1", name="Test Playlist", tracks=sample_tracks[:2])


@pytest.fixture
def sample_collection(sample_playlist):
    """Create a sample collection with playlists for testing."""
    return Collection(playlists=[sample_playlist])


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
    mock.should_ignore_playlist = Mock(return_value=False)
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


def create_mock_rekordbox_db():
    """
    Create a mock Rekordbox database with common setup.

    """
    mock_db = Mock()

    # Mock playlist structure that matches the expected API
    mock_playlist1 = Mock()
    mock_playlist1.ID = 1
    mock_playlist1.Name = "Test Playlist 1"
    mock_playlist1.Songs = []  # Empty list for songs
    mock_playlist1.Parent = None  # Top-level playlist
    mock_playlist1.Seq = 1

    # Mock song content for playlist 2
    mock_song = Mock()
    mock_content = Mock()
    mock_content.ID = 123
    mock_content.Title = "Test Song"
    mock_content.Key = "Am"
    mock_content.Length = 180.5  # Duration in seconds (this field is actually used)

    mock_artist = Mock()
    mock_artist.Name = "Test Artist"
    mock_content.Artist = mock_artist

    mock_song.Content = mock_content

    mock_playlist2 = Mock()
    mock_playlist2.ID = 2
    mock_playlist2.Name = "Test Playlist 2"
    mock_playlist2.Songs = [mock_song]  # List with one song
    mock_playlist2.Parent = None  # Top-level playlist
    mock_playlist2.Seq = 2

    # Configure mock database
    mock_db.get_playlist.return_value = [mock_playlist1, mock_playlist2]

    return mock_db


# Test Utilities


def silence_click_echo():
    """Context manager to silence click.echo calls in tests."""
    return patch("fortherekord.main.click.echo")


def silence_print():
    """Context manager to silence print calls in tests."""
    return patch("builtins.print")
