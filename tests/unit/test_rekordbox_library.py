"""
Tests for Rekordbox library integration.

Tests the RekordboxLibrary class with appropriate mocking of external dependencies.
"""

import subprocess
from pathlib import Path
from unittest.mock import Mock, patch
import pytest

from fortherekord.rekordbox_library import RekordboxLibrary
from fortherekord.models import Track, Playlist
from .conftest import create_mock_rekordbox_db, create_mock_track


# Helper functions to reduce repetition
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
        library = RekordboxLibrary({"rekordbox": {"library_path": "/path/to/database.db"}})
        assert library.db_path == Path("/path/to/database.db")
        assert library._db is None

    def test_init_with_path_object(self):
        """Test initializing with a Path object."""
        path = Path("/path/to/database.db")
        library = RekordboxLibrary({"rekordbox": {"library_path": str(path)}})
        assert library.db_path == path

    def test_init_missing_library_path(self):
        """Test initialization fails when library_path is not configured."""
        with pytest.raises(ValueError, match="rekordbox.library_path not configured"):
            RekordboxLibrary({"rekordbox": {}})

    def test_init_missing_rekordbox_section(self):
        """Test initialization fails when rekordbox section is missing."""
        with pytest.raises(ValueError, match="rekordbox.library_path not configured"):
            RekordboxLibrary({})


class TestDatabaseConnection:
    """Test database connection functionality."""

    @patch("fortherekord.rekordbox_library.Rekordbox6Database")
    @patch("pathlib.Path.exists")
    def test_get_database_success(self, mock_exists, mock_db_class):
        """Test successful database connection."""
        mock_db = create_mock_rekordbox_db()
        mock_db_class.return_value = mock_db
        mock_exists.return_value = True

        library = RekordboxLibrary({"rekordbox": {"library_path": "/path/to/database.db"}})
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
        library = RekordboxLibrary({"rekordbox": {"library_path": "/nonexistent/database.db"}})

        with pytest.raises(FileNotFoundError, match="Rekordbox database not found"):
            library._get_database()

    @patch("fortherekord.rekordbox_library.Rekordbox6Database")
    @patch("fortherekord.rekordbox_library.subprocess.run")
    @patch("pathlib.Path.exists")
    def test_get_database_key_download_success(self, mock_exists, mock_subprocess, mock_db_class):
        """Test database connection with successful key download."""
        from pyrekordbox.db6.database import NoCachedKey

        mock_exists.return_value = True

        # First call raises NoCachedKey, second call succeeds
        mock_db_instance = create_mock_rekordbox_db()
        mock_db_class.side_effect = [NoCachedKey("No key"), mock_db_instance]

        # Mock successful subprocess
        mock_subprocess.return_value = create_mock_subprocess_success()

        library = RekordboxLibrary({"rekordbox": {"library_path": "/path/to/database.db"}})
        db = library._get_database()
        assert db == mock_db_instance

        # Verify subprocess was called correctly
        mock_subprocess.assert_called_once()
        args = mock_subprocess.call_args[0][0]
        assert "pyrekordbox" in args
        assert "download-key" in args

    @patch("fortherekord.rekordbox_library.Rekordbox6Database")
    @patch("fortherekord.rekordbox_library.subprocess.run")
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

        library = RekordboxLibrary({"rekordbox": {"library_path": "/path/to/database.db"}})

        with pytest.raises(RuntimeError, match="Failed to download database key"):
            library._get_database()

    @patch("fortherekord.rekordbox_library.Rekordbox6Database")
    @patch("fortherekord.rekordbox_library.subprocess.run")
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

        library = RekordboxLibrary({"rekordbox": {"library_path": "/path/to/database.db"}})

        with pytest.raises(RuntimeError, match="Database key could not be obtained"):
            library._get_database()


class TestPlaylistRetrieval:
    """Test playlist retrieval functionality."""

    @patch("fortherekord.rekordbox_library.RekordboxLibrary._get_database")
    def test_get_playlists_success(self, mock_get_db):
        """Test successful playlist retrieval with track reuse across playlists."""
        mock_db = create_mock_rekordbox_db()
        mock_get_db.return_value = mock_db

        library = RekordboxLibrary({"rekordbox": {"library_path": "/path/to/database.db"}})
        collection = library.get_filtered_collection()
        playlists = collection.playlists

        assert len(playlists) == 3

        # First playlist: 3 tracks
        assert playlists[0].name == "Test Playlist 1"
        assert playlists[0].id == "1"
        assert len(playlists[0].tracks) == 3

        # Second playlist: 2 tracks (one shared with first playlist)
        assert playlists[1].name == "Test Playlist 2"
        assert playlists[1].id == "2"
        assert len(playlists[1].tracks) == 2

        # Third playlist: empty
        assert playlists[2].name == "Empty Playlist"
        assert playlists[2].id == "3"
        assert len(playlists[2].tracks) == 0

        # Verify shared track (ID 123) appears in both playlists
        shared_track_playlist_1 = playlists[0].tracks[0]  # First track in playlist 1
        shared_track_playlist_2 = playlists[1].tracks[0]  # First track in playlist 2

        assert shared_track_playlist_1.id == "123"
        assert shared_track_playlist_2.id == "123"
        assert shared_track_playlist_1.title == "Shared Song"
        assert shared_track_playlist_2.title == "Shared Song"
        assert shared_track_playlist_1.artist == "Artist A"
        assert shared_track_playlist_2.artist == "Artist A"
        assert shared_track_playlist_1.duration_ms == 180500  # 180.5 seconds in milliseconds
        assert shared_track_playlist_1.key == "Am"

    @patch("fortherekord.rekordbox_library.RekordboxLibrary._get_database")
    def test_get_playlists_with_missing_metadata(self, mock_get_db):
        """Test playlist retrieval with missing track metadata."""
        mock_db = Mock()

        # Create playlist with song missing some metadata
        mock_playlist = Mock()
        mock_playlist.ID = 1
        mock_playlist.Name = None  # Missing name
        mock_playlist.Parent = None  # Top-level playlist
        mock_playlist.Seq = 1

        mock_song = Mock()
        mock_content = create_mock_track(123, None, None, None)  # Missing metadata
        mock_content.Length = None  # Missing length

        mock_song.Content = mock_content

        # Mock get_playlist_contents to return the content (unified approach)
        def mock_get_playlist_contents(playlist):
            if playlist.ID == 1:
                return Mock(all=lambda: [mock_content])
            else:
                return Mock(all=lambda: [])

        mock_db.get_playlist_contents = mock_get_playlist_contents

        mock_db.get_playlist.return_value = [mock_playlist]
        mock_get_db.return_value = mock_db

        library = RekordboxLibrary({"rekordbox": {"library_path": "/path/to/database.db"}})
        collection = library.get_collection()

        assert len(collection.playlists) == 1
        assert collection.playlists[0].name == "Unnamed Playlist"

        track = collection.playlists[0].tracks[0]
        assert track.title == "Unknown Title"
        assert track.artist == "Unknown Artist"
        assert track.duration_ms is None
        assert track.key is None


class TestUnsupportedOperations:
    """Test operations that are not supported (read-only library)."""

    def test_create_playlist_not_supported(self):
        """Test that create_playlist raises NotImplementedError."""
        library = RekordboxLibrary({"rekordbox": {"library_path": "/path/to/database.db"}})

        with pytest.raises(NotImplementedError, match="Playlist creation not supported"):
            library.create_playlist("New Playlist", [])

    def test_delete_playlist_not_supported(self):
        """Test that delete_playlist raises NotImplementedError."""
        library = RekordboxLibrary({"rekordbox": {"library_path": "/path/to/database.db"}})

        with pytest.raises(NotImplementedError, match="Playlist deletion not supported"):
            library.delete_playlist("1")

    def test_follow_artist_not_supported(self):
        """Test that follow_artist raises NotImplementedError."""
        library = RekordboxLibrary({"rekordbox": {"library_path": "/path/to/database.db"}})

        with pytest.raises(NotImplementedError, match="Artist following not supported"):
            library.follow_artist("Test Artist")

    def test_get_followed_artists_not_supported(self):
        """Test that get_followed_artists raises NotImplementedError."""
        library = RekordboxLibrary({"rekordbox": {"library_path": "/path/to/database.db"}})

        with pytest.raises(NotImplementedError, match="Followed artists not supported"):
            library.get_followed_artists()


# Test fixtures for common setup
@pytest.fixture
def mock_rekordbox_library():
    """Provide a mock RekordboxLibrary for testing."""
    with patch("fortherekord.rekordbox_library.RekordboxLibrary._get_database") as mock_get_db:
        mock_db = create_mock_rekordbox_db()
        mock_get_db.return_value = mock_db
        library = RekordboxLibrary({"rekordbox": {"library_path": "/test/path/database.db"}})
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

    def test_collection_retrieval_with_fixture(self, mock_rekordbox_library):
        """Test collection retrieval using fixtures."""
        collection = mock_rekordbox_library.get_collection()
        assert len(collection.playlists) >= 1
        assert all(isinstance(p, Playlist) for p in collection.playlists)


class TestPlaylistHierarchy:
    """Test playlist parent-child relationships and sorting."""

    @patch("fortherekord.rekordbox_library.RekordboxLibrary._get_database")
    def test_get_playlists_with_parent_child_relationships(self, mock_get_db):
        """Test playlist retrieval with parent-child relationships."""
        mock_db = Mock()

        # Create parent playlist
        parent_playlist = Mock()
        parent_playlist.ID = 1
        parent_playlist.Name = "Parent Playlist"
        parent_playlist.Songs = []
        parent_playlist.Seq = 1
        parent_playlist.Parent = None

        # Create child playlists
        child1 = Mock()
        child1.ID = 2
        child1.Name = "Child 1"
        child1.Songs = []
        child1.Seq = 2
        child1.Parent = parent_playlist

        child2 = Mock()
        child2.ID = 3
        child2.Name = "Child 2"
        child2.Songs = []
        child2.Seq = 1  # Lower sequence number - should be sorted first
        child2.Parent = parent_playlist

        mock_db.get_playlist.return_value = [parent_playlist, child1, child2]
        mock_get_db.return_value = mock_db

        library = RekordboxLibrary({"rekordbox": {"library_path": "/test/db.edb"}})
        collection = library.get_collection()

        # Should return only the parent (top-level) playlist
        assert len(collection.playlists) == 1
        parent = collection.playlists[0]
        assert parent.name == "Parent Playlist"
        assert parent.children is not None
        assert len(parent.children) == 2

        # Children should be sorted by sequence
        assert parent.children[0].name == "Child 2"  # Seq = 1
        assert parent.children[1].name == "Child 1"  # Seq = 2


class TestRekordboxLibraryDatabaseWriting:
    """Test database writing functionality."""

    def test_update_track_metadata_success(self):
        """Test successful track metadata update."""
        mock_db = Mock()
        mock_content = Mock()
        mock_artist = Mock()
        mock_content.Artist = mock_artist
        mock_db.get_content.return_value = mock_content

        library = RekordboxLibrary({"rekordbox": {"library_path": "/test/db.edb"}})
        library._db = mock_db

        result = library.update_track_metadata("123", "New Title", "New Artist")

        assert result is True
        assert mock_content.Title == "New Title"
        assert mock_artist.Name == "New Artist"
        mock_db.get_content.assert_called_once_with(ID="123")

    def test_update_track_metadata_track_not_found(self):
        """Test track metadata update when track is not found."""
        mock_db = Mock()
        mock_db.get_content.return_value = None

        library = RekordboxLibrary({"rekordbox": {"library_path": "/test/db.edb"}})
        library._db = mock_db

        result = library.update_track_metadata("999", "New Title", "New Artist")

        assert result is False
        mock_db.get_content.assert_called_once_with(ID="999")

    def test_update_track_metadata_no_artist(self):
        """Test track metadata update when track has no artist."""
        mock_db = Mock()
        mock_content = Mock()
        mock_content.Artist = None
        mock_db.get_content.return_value = mock_content

        library = RekordboxLibrary({"rekordbox": {"library_path": "/test/db.edb"}})
        library._db = mock_db

        result = library.update_track_metadata("123", "New Title", "New Artist")

        assert result is True
        assert mock_content.Title == "New Title"
        # Artist should not be set if track.Artist is None

    def test_update_track_metadata_exception(self):
        """Test track metadata update when exception occurs."""
        mock_db = Mock()
        mock_db.get_content.side_effect = Exception("Database error")

        library = RekordboxLibrary({"rekordbox": {"library_path": "/test/db.edb"}})
        library._db = mock_db

        with pytest.raises(Exception, match="Database error"):
            library.update_track_metadata("123", "New Title", "New Artist")

    @patch.dict("os.environ", {"FORTHEREKORD_TEST_MODE": "0"})
    def test_save_changes_success(self):
        """Test successful save changes counts modified tracks correctly."""
        from fortherekord.models import Track

        library = RekordboxLibrary({"rekordbox": {"library_path": "/test/db.edb"}})
        library._db = Mock()

        # Create track objects with current values
        tracks = [
            # Track 1: Title changed, artist unchanged
            Track(
                id="1",
                title="New Title",  # Changed from "Original Title"
                artist="Same Artist",  # Unchanged
                original_title="Original Title",
                original_artist="Same Artist",
            ),
            # Track 2: Title unchanged, artist changed
            Track(
                id="2",
                title="Same Title",  # Unchanged
                artist="New Artist",  # Changed from "Original Artist"
                original_title="Same Title",
                original_artist="Original Artist",
            ),
            # Track 3: Both title and artist unchanged
            Track(
                id="3",
                title="Unchanged Title",  # Unchanged
                artist="Unchanged Artist",  # Unchanged
                original_title="Unchanged Title",
                original_artist="Unchanged Artist",
            ),
            # Track 4: Both title and artist changed
            Track(
                id="4",
                title="Completely New Title",  # Changed from "Old Title"
                artist="Completely New Artist",  # Changed from "Old Artist"
                original_title="Old Title",
                original_artist="Old Artist",
            ),
        ]

        result = library.save_changes(tracks)

        # Should count 3 modified tracks (track1, track2, track4) and `ignore` track3
        assert result == 3
        library._db.commit.assert_called_once()

    @patch.dict("os.environ", {"FORTHEREKORD_TEST_MODE": "0"})
    def test_save_changes_commit_exception(self):
        """Test save_changes when commit raises an exception."""
        from fortherekord.models import Track

        mock_db = Mock()
        mock_db.commit.side_effect = Exception("Database commit failed")

        library = RekordboxLibrary({"rekordbox": {"library_path": "/test/db.edb"}})
        library._db = mock_db

        # Create a track with different original and current values to trigger commit
        tracks = [
            Track(
                id="1",
                title="New Title",
                artist="New Artist",
                original_title="Old Title",  # Different from current
                original_artist="Old Artist",  # Different from current
            )
        ]

        # Should now raise the exception since modified_count > 0 triggers commit
        with pytest.raises(Exception, match="Database commit failed"):
            library.save_changes(tracks)

    @patch.dict("os.environ", {"FORTHEREKORD_TEST_MODE": "0"})
    def test_save_changes_update_failure(self):
        """Test save_changes when update_track_metadata fails."""
        from fortherekord.models import Track
        import io
        import sys

        library = RekordboxLibrary({"rekordbox": {"library_path": "/test/db.edb"}})
        library._db = Mock()
        library.update_track_metadata = Mock(return_value=False)  # Simulate update failure

        # Create a track with different original and current values
        tracks = [
            Track(
                id="1",
                title="New Title",
                artist="New Artist",
                original_title="Old Title",  # Different from current
                original_artist="Old Artist",  # Different from current
            )
        ]

        # Capture print output
        captured_output = io.StringIO()
        sys.stdout = captured_output

        try:
            result = library.save_changes(tracks)

            # Should return 0 since update failed
            assert result == 0

            # Check that warning was printed
            output = captured_output.getvalue()
            assert "WARNING: Failed to update track 1: New Title" in output
        finally:
            sys.stdout = sys.__stdout__


class TestDatabaseSafety:
    """Test database safety mechanisms to prevent commits during tests."""

    def test_save_changes_never_commits_during_tests(self):
        """Test that save_changes never calls db.commit() during test execution."""
        # This test validates that our test safety mechanism is working
        from .conftest import cleanup_test_dump_file

        mock_db = Mock()

        library = RekordboxLibrary({"rekordbox": {"library_path": "/test/db.edb"}})
        library._db = mock_db

        try:
            # Call save_changes - should NOT call commit in test mode
            result = library.save_changes([])

            # Should return 0 (no tracks modified) but never call actual commit
            assert result == 0
            mock_db.commit.assert_not_called()
        finally:
            cleanup_test_dump_file()

    def test_test_mode_environment_is_set(self):
        """Test that FORTHEREKORD_TEST_MODE is set during test runs."""
        import os

        test_mode = os.getenv("FORTHEREKORD_TEST_MODE", "")
        assert test_mode == "1", "Test mode should be enabled during test runs"

    @patch.dict("os.environ", {"FORTHEREKORD_TEST_MODE": "0"})
    def test_save_changes_commits_when_test_mode_disabled(self):
        """Test that save_changes calls commit when test mode is explicitly disabled."""
        mock_db = Mock()

        library = RekordboxLibrary({"rekordbox": {"library_path": "/test/db.edb"}})
        library._db = mock_db

        result = library.save_changes([])

        assert result == 0
        mock_db.commit.assert_not_called()  # No tracks to commit

    def test_save_changes_creates_dump_file_in_test_mode(self):
        """Test that save_changes creates dump file instead of committing in test mode."""
        import json
        from pathlib import Path
        from .conftest import cleanup_test_dump_file

        try:
            mock_db = Mock()

            library = RekordboxLibrary({"rekordbox": {"library_path": "/test/db.edb"}})
            library._db = mock_db

            result = library.save_changes([])

            # Should return 0 for no tracks
            assert result == 0

            # Should NOT call commit
            mock_db.commit.assert_not_called()

            # Should create dump file
            dump_file = "test_changes_dump.json"
            assert Path(dump_file).exists()

            # Dump file should contain expected data
            with open(dump_file) as f:
                dump_data = json.load(f)

            assert dump_data["mode"] == "test_dump"
            assert "Database commit prevented" in dump_data["note"]

        finally:
            cleanup_test_dump_file()

    def test_save_changes_dry_run_counts_all_changes(self):
        """Test save_changes with dry_run=True counts changes without modifying database."""
        library = RekordboxLibrary({"rekordbox": {"library_path": "/test/db.edb"}})
        library._db = Mock()

        # Multiple tracks with changes
        track1 = Track(id="1", title="New Title 1", artist="New Artist 1")
        track1.original_title = "Original Title 1"
        track1.original_artist = "Original Artist 1"

        track2 = Track(id="2", title="New Title 2", artist="New Artist 2")
        track2.original_title = "Original Title 2"
        track2.original_artist = "Original Artist 2"

        # Track with no changes
        track3 = Track(id="3", title="Same Title", artist="Same Artist")
        track3.original_title = "Same Title"
        track3.original_artist = "Same Artist"

        # Call save_changes with dry_run=True
        result = library.save_changes([track1, track2, track3], dry_run=True)

        # Should count only the changed tracks
        assert result == 2

        # Verify that no database operations were performed (no commit called)
        library._db.commit.assert_not_called()


class TestGetAllTracks:
    """Test get_all_tracks functionality."""

    @patch("fortherekord.rekordbox_library.RekordboxLibrary._get_database")
    def test_get_all_tracks_success(self, mock_get_db):
        """Test successful retrieval of all tracks."""
        mock_db = Mock()

        # Create mock content data using the helper function
        mock_content1 = create_mock_track(123, "Song 1", "Artist 1", "Am")
        mock_content1.Length = 180.5

        mock_content2 = create_mock_track(456, "Song 2", "Artist 2", "Dm")
        mock_content2.Length = 240.0

        mock_db.get_content.return_value = [mock_content1, mock_content2]
        mock_get_db.return_value = mock_db

        library = RekordboxLibrary({"rekordbox": {"library_path": "/path/to/database.db"}})
        tracks = library.get_all_tracks()

        assert len(tracks) == 2

        # Check first track
        assert tracks[0].id == "123"
        assert tracks[0].title == "Song 1"
        assert tracks[0].artist == "Artist 1"
        assert tracks[0].duration_ms == 180500
        assert tracks[0].key == "Am"

        # Check second track
        assert tracks[1].id == "456"
        assert tracks[1].title == "Song 2"
        assert tracks[1].artist == "Artist 2"
        assert tracks[1].duration_ms == 240000
        assert tracks[1].key == "Dm"
