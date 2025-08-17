"""
Tests for Rekordbox library integration.

Tests the RekordboxLibrary class with appropriate mocking of external dependencies.
"""

import subprocess
from pathlib import Path
from unittest.mock import Mock, patch
import pytest

from fortherekord.rekordbox import RekordboxLibrary
from fortherekord.models import Track, Playlist


# Helper functions to reduce repetition
def create_mock_rekordbox_database():
    """Helper function to create a mock Rekordbox database."""
    mock_db = Mock()

    # Create mock playlist data
    mock_playlist1 = Mock()
    mock_playlist1.ID = 1
    mock_playlist1.Name = "Test Playlist 1"
    mock_playlist1.Songs = []

    mock_playlist2 = Mock()
    mock_playlist2.ID = 2
    mock_playlist2.Name = "Test Playlist 2"

    # Create mock song/track data
    mock_song = Mock()
    mock_content = Mock()
    mock_content.ID = 123
    mock_content.Title = "Test Song"
    mock_content.Length = 180.5  # 3 minutes 30 seconds
    mock_content.Key = "Am"
    mock_content.BPM = 120.0

    mock_artist = Mock()
    mock_artist.Name = "Test Artist"
    mock_content.Artist = mock_artist

    mock_song.Content = mock_content
    mock_playlist2.Songs = [mock_song]

    mock_db.get_playlist.return_value = [mock_playlist1, mock_playlist2]
    return mock_db


def create_mock_subprocess_success():
    """Helper function to create a successful subprocess mock."""
    mock_result = Mock()
    mock_result.returncode = 0
    mock_result.stdout = "Key downloaded successfully"
    mock_result.stderr = ""
    return mock_result


class TestRekordboxLibraryInit:
    """Test RekordboxLibrary initialization."""

    def test_init_with_valid_path(self):
        """Test initializing with a valid database path."""
        library = RekordboxLibrary("/path/to/database.db")
        assert library.db_path == Path("/path/to/database.db")
        assert library._db is None

    def test_init_with_path_object(self):
        """Test initializing with a Path object."""
        path = Path("/path/to/database.db")
        library = RekordboxLibrary(str(path))
        assert library.db_path == path


class TestDatabaseConnection:
    """Test database connection functionality."""

    @patch("fortherekord.rekordbox.Rekordbox6Database")
    @patch("pathlib.Path.exists")
    def test_get_database_success(self, mock_exists, mock_db_class):
        """Test successful database connection."""
        mock_db = create_mock_rekordbox_database()
        mock_db_class.return_value = mock_db
        mock_exists.return_value = True

        library = RekordboxLibrary("/path/to/database.db")
        db = library._get_database()
        assert db == mock_db
        # Check that the database was called with the correct path (accounting for Path conversion)
        mock_db_class.assert_called_once()
        called_path = mock_db_class.call_args[0][0]
        assert called_path.endswith("database.db")

    @patch("pathlib.Path.exists")
    def test_get_database_file_not_found(self, mock_exists):
        """Test database connection when file doesn't exist."""
        mock_exists.return_value = False
        library = RekordboxLibrary("/nonexistent/database.db")

        with pytest.raises(FileNotFoundError, match="Rekordbox database not found"):
            library._get_database()

    @patch("fortherekord.rekordbox.Rekordbox6Database")
    @patch("fortherekord.rekordbox.subprocess.run")
    @patch("pathlib.Path.exists")
    def test_get_database_key_download_success(self, mock_exists, mock_subprocess, mock_db_class):
        """Test database connection with successful key download."""
        from pyrekordbox.db6.database import NoCachedKey

        mock_exists.return_value = True

        # First call raises NoCachedKey, second call succeeds
        mock_db_instance = create_mock_rekordbox_database()
        mock_db_class.side_effect = [NoCachedKey("No key"), mock_db_instance]

        # Mock successful subprocess
        mock_subprocess.return_value = create_mock_subprocess_success()

        library = RekordboxLibrary("/path/to/database.db")
        db = library._get_database()
        assert db == mock_db_instance

        # Verify subprocess was called correctly
        mock_subprocess.assert_called_once()
        args = mock_subprocess.call_args[0][0]
        assert "pyrekordbox" in args
        assert "download-key" in args

    @patch("fortherekord.rekordbox.Rekordbox6Database")
    @patch("fortherekord.rekordbox.subprocess.run")
    @patch("pathlib.Path.exists")
    def test_get_database_key_download_fails(self, mock_exists, mock_subprocess, mock_db_class):
        """Test database connection when key download fails."""
        from pyrekordbox.db6.database import NoCachedKey

        mock_exists.return_value = True
        mock_db_class.side_effect = NoCachedKey("No key")

        # Mock failed subprocess
        mock_subprocess.side_effect = subprocess.CalledProcessError(
            1, "cmd", stderr="Download failed"
        )

        library = RekordboxLibrary("/path/to/database.db")

        with pytest.raises(RuntimeError, match="Failed to download database key"):
            library._get_database()

    @patch("fortherekord.rekordbox.Rekordbox6Database")
    @patch("fortherekord.rekordbox.subprocess.run")
    @patch("pathlib.Path.exists")
    def test_get_database_key_still_missing_after_download(
        self, mock_exists, mock_subprocess, mock_db_class
    ):
        """Test database connection when key is still missing after download."""
        from pyrekordbox.db6.database import NoCachedKey

        mock_exists.return_value = True

        # Both calls raise NoCachedKey
        mock_db_class.side_effect = [NoCachedKey("No key"), NoCachedKey("Still no key")]

        # Mock successful subprocess (but key still not available)
        mock_subprocess.return_value = create_mock_subprocess_success()

        library = RekordboxLibrary("/path/to/database.db")

        with pytest.raises(RuntimeError, match="Database key could not be obtained"):
            library._get_database()


class TestPlaylistRetrieval:
    """Test playlist retrieval functionality."""

    @patch("fortherekord.rekordbox.RekordboxLibrary._get_database")
    def test_get_playlists_success(self, mock_get_db):
        """Test successful playlist retrieval."""
        mock_db = create_mock_rekordbox_database()
        mock_get_db.return_value = mock_db

        library = RekordboxLibrary("/path/to/database.db")
        playlists = library.get_playlists()

        assert len(playlists) == 2
        assert playlists[0].name == "Test Playlist 1"
        assert playlists[0].id == "1"
        assert len(playlists[0].tracks) == 0

        assert playlists[1].name == "Test Playlist 2"
        assert playlists[1].id == "2"
        assert len(playlists[1].tracks) == 1

        track = playlists[1].tracks[0]
        assert track.id == "123"
        assert track.title == "Test Song"
        assert track.artist == "Test Artist"
        assert track.duration_ms == 180500  # 180.5 seconds in milliseconds
        assert track.key == "Am"
        assert track.bpm == 120.0

    @patch("fortherekord.rekordbox.RekordboxLibrary._get_database")
    def test_get_playlists_with_missing_metadata(self, mock_get_db):
        """Test playlist retrieval with missing track metadata."""
        mock_db = Mock()

        # Create playlist with song missing some metadata
        mock_playlist = Mock()
        mock_playlist.ID = 1
        mock_playlist.Name = None  # Missing name

        mock_song = Mock()
        mock_content = Mock()
        mock_content.ID = 123
        mock_content.Title = None  # Missing title
        mock_content.Artist = None  # Missing artist
        mock_content.Length = None  # Missing length
        mock_content.Key = None
        mock_content.BPM = None

        mock_song.Content = mock_content
        mock_playlist.Songs = [mock_song]

        mock_db.get_playlist.return_value = [mock_playlist]
        mock_get_db.return_value = mock_db

        library = RekordboxLibrary("/path/to/database.db")
        playlists = library.get_playlists()

        assert len(playlists) == 1
        assert playlists[0].name == "Unnamed Playlist"

        track = playlists[0].tracks[0]
        assert track.title == "Unknown Title"
        assert track.artist == "Unknown Artist"
        assert track.duration_ms is None
        assert track.key is None
        assert track.bpm is None


class TestPlaylistTrackRetrieval:
    """Test individual playlist track retrieval."""

    @patch("fortherekord.rekordbox.RekordboxLibrary._get_database")
    def test_get_playlist_tracks_success(self, mock_get_db):
        """Test successful retrieval of tracks for specific playlist."""
        mock_db = create_mock_rekordbox_database()
        mock_get_db.return_value = mock_db

        library = RekordboxLibrary("/path/to/database.db")
        tracks = library.get_playlist_tracks("2")

        assert len(tracks) == 1
        track = tracks[0]
        assert track.id == "123"
        assert track.title == "Test Song"
        assert track.artist == "Test Artist"

    @patch("fortherekord.rekordbox.RekordboxLibrary._get_database")
    def test_get_playlist_tracks_not_found(self, mock_get_db):
        """Test retrieval of tracks for non-existent playlist."""
        mock_db = create_mock_rekordbox_database()
        mock_get_db.return_value = mock_db

        library = RekordboxLibrary("/path/to/database.db")

        with pytest.raises(ValueError, match="Playlist not found: 999"):
            library.get_playlist_tracks("999")


class TestUnsupportedOperations:
    """Test operations that are not supported (read-only library)."""

    def test_create_playlist_not_supported(self):
        """Test that create_playlist raises NotImplementedError."""
        library = RekordboxLibrary("/path/to/database.db")

        with pytest.raises(NotImplementedError, match="Playlist creation not supported"):
            library.create_playlist("New Playlist", [])

    def test_delete_playlist_not_supported(self):
        """Test that delete_playlist raises NotImplementedError."""
        library = RekordboxLibrary("/path/to/database.db")

        with pytest.raises(NotImplementedError, match="Playlist deletion not supported"):
            library.delete_playlist("1")

    def test_follow_artist_not_supported(self):
        """Test that follow_artist raises NotImplementedError."""
        library = RekordboxLibrary("/path/to/database.db")

        with pytest.raises(NotImplementedError, match="Artist following not supported"):
            library.follow_artist("Test Artist")

    def test_get_followed_artists_not_supported(self):
        """Test that get_followed_artists raises NotImplementedError."""
        library = RekordboxLibrary("/path/to/database.db")

        with pytest.raises(NotImplementedError, match="Followed artists not supported"):
            library.get_followed_artists()


# Test fixtures for common setup
@pytest.fixture
def mock_rekordbox_library():
    """Provide a mock RekordboxLibrary for testing."""
    with patch("fortherekord.rekordbox.RekordboxLibrary._get_database") as mock_get_db:
        mock_db = create_mock_rekordbox_database()
        mock_get_db.return_value = mock_db
        library = RekordboxLibrary("/test/path/database.db")
        yield library


@pytest.fixture
def sample_rekordbox_data():
    """Provide sample Rekordbox data for testing."""
    return {
        "playlists": [
            {
                "id": 1,
                "name": "Rock Collection",
                "songs": [
                    {"id": 101, "title": "Rock Song 1", "artist": "Rock Band", "length": 200.0}
                ],
            },
            {
                "id": 2,
                "name": "Electronic Mix",
                "songs": [
                    {
                        "id": 102,
                        "title": "Electronic Track",
                        "artist": "DJ Producer",
                        "length": 300.5,
                    }
                ],
            },
        ]
    }


# Example of using fixtures to reduce repetition
class TestRekordboxWithFixtures:
    """Example of using fixtures for Rekordbox tests."""

    def test_playlist_retrieval_with_fixture(self, mock_rekordbox_library):
        """Test playlist retrieval using fixtures."""
        playlists = mock_rekordbox_library.get_playlists()
        assert len(playlists) >= 1
        assert all(isinstance(p, Playlist) for p in playlists)

    def test_track_retrieval_with_fixture(self, mock_rekordbox_library):
        """Test track retrieval using fixtures."""
        # Assume playlist "2" exists with tracks
        tracks = mock_rekordbox_library.get_playlist_tracks("2")
        assert len(tracks) >= 1
        assert all(isinstance(t, Track) for t in tracks)
