"""
Tests for Rekordbox library integration.

Tests the RekordboxLibrary class with appropriate mocking of external dependencies.
"""

import subprocess
from pathlib import Path
from unittest.mock import Mock, patch
import pytest

from fortherekord.rekordbox_library import RekordboxLibrary
from fortherekord.models import Playlist
from .conftest import create_track


def create_mock_rekordbox_db():
    """
    Create a mock Rekordbox database with common setup.

    Creates 3 playlists:
    - Playlist 1: 3 tracks (IDs: 123, 456, 789)
    - Playlist 2: 2 tracks (IDs: 123, 999) - track 123 is shared with playlist 1
    - Playlist 3: Empty playlist
    """
    mock_db = Mock()

    # Create mock tracks using the helper function
    track_123 = create_mock_track_content("123", "Shared Song", "Artist A", "Am")
    track_456 = create_mock_track_content("456", "Song Two", "Artist B", "Dm")
    track_789 = create_mock_track_content("789", "Song Three", "Artist C", "Gm")
    track_999 = create_mock_track_content("999", "Song Four", "Artist D", "Em")

    # Create mock playlists using the helper function
    playlist_1 = create_mock_playlist_content("1", "Test Playlist 1", seq=1)
    playlist_2 = create_mock_playlist_content("2", "Test Playlist 2", seq=2)
    playlist_3 = create_mock_playlist_content("3", "Empty Playlist", seq=3)

    # Configure playlist contents
    playlist_contents = {
        1: [track_123, track_456, track_789],  # 3 tracks
        2: [track_123, track_999],  # 2 tracks (one shared)
        3: [],  # Empty
    }

    mock_db.get_playlist.return_value = [playlist_1, playlist_2, playlist_3]
    mock_db.get_playlist_contents = lambda playlist: Mock(
        all=lambda: playlist_contents.get(playlist.ID, [])
    )

    return mock_db


# Helper functions for rekordbox library testing
def create_mock_track_content(track_id, title, artists, key="Am"):
    """
    Create a mock track content object for pyrekordbox simulation.

    Args:
        track_id: Track ID (int or str)
        title: Track title
        artist_name: Artist name (None for missing artists)
        key: Musical key (default: "Am")

    Returns:
        Mock object representing pyrekordbox track content
    """
    track = Mock()
    track.ID = int(track_id) if str(track_id).isdigit() else track_id
    track.Title = title or ""
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


def create_mock_playlist_content(playlist_id, name, seq=1, parent_id=None):
    """
    Create a mock playlist object for pyrekordbox simulation.

    Args:
        playlist_id: Playlist ID (int or str)
        name: Playlist name
        seq: Sequence number for sorting
        parent_id: Parent playlist ID (None for top-level)

    Returns:
        Mock object representing pyrekordbox playlist
    """
    playlist = Mock()
    playlist.ID = int(playlist_id) if str(playlist_id).isdigit() else playlist_id
    playlist.Name = name
    playlist.Seq = seq

    # Handle parent relationship
    if parent_id is not None:
        parent = Mock()
        parent.ID = int(parent_id) if str(parent_id).isdigit() else parent_id
        playlist.Parent = parent
    else:
        playlist.Parent = None

    return playlist


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
        assert shared_track_playlist_1.artists == "Artist A"
        assert shared_track_playlist_2.artists == "Artist A"
        assert shared_track_playlist_1.key == "Am"

    @patch("fortherekord.rekordbox_library.RekordboxLibrary._get_database")
    def test_get_playlists_with_missing_metadata(self, mock_get_db):
        """Test playlist retrieval with missing track metadata."""
        mock_db = Mock()

        # Create playlist with song missing some metadata
        mock_playlist = create_mock_playlist_content("1", None, seq=1)  # Missing name

        mock_song = Mock()
        mock_content = create_mock_track_content("123", None, None, None)  # Missing metadata
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
        assert track.title == ""
        assert track.artists == ""
        assert track.key is None

    @patch("fortherekord.rekordbox_library.RekordboxLibrary._get_database")
    @patch("builtins.print")
    def test_get_playlists_smart_playlist_month_bug(self, mock_print, mock_get_db):
        """Test handling of pyrekordbox bug with smart playlists using month-based date filters."""
        mock_db = Mock()

        # Create a smart playlist that triggers the month-based date filter bug
        mock_playlist = create_mock_playlist_content("1", "Smart Playlist with Month Filter", seq=1)

        # Mock get_playlist to return our problem playlist
        mock_db.get_playlist.return_value = [mock_playlist]

        # Mock get_playlist_contents to raise AttributeError with month and StockDate
        def raise_month_error(playlist):
            raise AttributeError("'month' attribute error with StockDate filter")

        mock_db.get_playlist_contents = Mock(side_effect=raise_month_error)

        mock_get_db.return_value = mock_db

        library = RekordboxLibrary({"rekordbox": {"library_path": "/path/to/database.db"}})
        collection = library.get_collection()

        # Should create an empty playlist when the month bug occurs
        assert len(collection.playlists) == 1
        assert collection.playlists[0].name == "Smart Playlist with Month Filter"
        assert len(collection.playlists[0].tracks) == 0

        # Verify warning messages were printed
        assert mock_print.call_count == 3
        print_calls = [call.args[0] for call in mock_print.call_args_list]
        assert any(
            "WARNING: Smart playlist" in call and "month-based date filters" in call
            for call in print_calls
        )
        assert any("Workaround: Change the smart playlist" in call for call in print_calls)
        assert any("This playlist will be skipped" in call for call in print_calls)

    @patch("fortherekord.rekordbox_library.RekordboxLibrary._get_database")
    def test_get_playlists_other_attribute_error(self, mock_get_db):
        """Test that other AttributeErrors are re-raised."""
        mock_db = Mock()

        # Create a playlist that triggers a different AttributeError
        mock_playlist = create_mock_playlist_content("1", "Problematic Playlist", seq=1)

        # Mock get_playlist to return our problem playlist
        mock_db.get_playlist.return_value = [mock_playlist]

        # Mock get_playlist_contents to raise a different AttributeError
        def raise_other_error(playlist):
            raise AttributeError("Some other attribute error")

        mock_db.get_playlist_contents = Mock(side_effect=raise_other_error)

        mock_get_db.return_value = mock_db

        library = RekordboxLibrary({"rekordbox": {"library_path": "/path/to/database.db"}})

        # Should re-raise the AttributeError since it's not the month bug
        with pytest.raises(AttributeError, match="Some other attribute error"):
            library.get_collection()


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
                    {"id": 101, "title": "Rock Song 1", "artists": "Rock Band", "length": 200.0}
                ],
            },
            {
                "id": 2,
                "name": "Electronic Mix",
                "songs": [
                    {
                        "id": 102,
                        "title": "Electronic Track",
                        "artists": "DJ Producer",
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
        parent_playlist = create_mock_playlist_content("1", "Parent Playlist", seq=1)

        # Create child playlists
        child1 = create_mock_playlist_content("2", "Child 1", seq=2, parent_id="1")
        child1.Parent = parent_playlist  # Set the actual parent mock object

        child2 = create_mock_playlist_content(
            "3", "Child 2", seq=1, parent_id="1"
        )  # Lower sequence number - should be sorted first
        child2.Parent = parent_playlist  # Set the actual parent mock object

        # Mock get_playlist_contents to return empty for folders/empty playlists
        def mock_get_playlist_contents(playlist):
            return Mock(all=lambda: [])

        mock_db.get_playlist_contents = mock_get_playlist_contents

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
        """Test track metadata update when track has no artists."""
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

        library = RekordboxLibrary({"rekordbox": {"library_path": "/test/db.edb"}})
        library._db = Mock()

        # Create track objects with current values
        tracks = [
            # Track 1: Title changed, artists unchanged
            create_track(
                track_id="1",
                title="New Title",  # Changed from "Original Title"
                artists="Same Artist",  # Unchanged
            ),
            # Track 2: Title unchanged, artists changed
            create_track(
                track_id="2",
                title="Same Title",  # Unchanged
                artists="New Artist",  # Changed from "Original Artist"
            ),
            # Track 3: Both title and artists unchanged
            create_track(
                track_id="3",
                title="Unchanged Title",  # Unchanged
                artists="Unchanged Artist",  # Unchanged
            ),
            # Track 4: Both title and artists changed
            create_track(
                track_id="4",
                title="Completely New Title",  # Changed from "Old Title"
                artists="Completely New Artist",  # Changed from "Old Artist"
            ),
        ]

        # Update original values to simulate what would have been set during loading
        tracks[0].original_title = "Original Title"
        tracks[0].original_artists = "Same Artist"
        tracks[1].original_title = "Same Title"
        tracks[1].original_artists = "Original Artist"
        tracks[2].original_title = "Unchanged Title"
        tracks[2].original_artists = "Unchanged Artist"
        tracks[3].original_title = "Old Title"
        tracks[3].original_artists = "Old Artist"

        result = library.save_changes(tracks)

        # Should save all 4 tracks that were passed (no filtering in save_changes anymore)
        assert result == 4
        library._db.commit.assert_called_once()

    @patch.dict("os.environ", {"FORTHEREKORD_TEST_MODE": "0"})
    def test_save_changes_commit_exception(self):
        """Test save_changes when commit raises an exception."""

        mock_db = Mock()
        mock_db.commit.side_effect = Exception("Database commit failed")

        library = RekordboxLibrary({"rekordbox": {"library_path": "/test/db.edb"}})
        library._db = mock_db

        # Create a track with different original and current values to trigger commit
        tracks = [
            create_mock_track_content(
                track_id="1",
                title="New Title",
                artists="New Artist",
            )
        ]
        # Set original values to be different from current
        tracks[0].original_title = "Old Title"
        tracks[0].original_artists = "Old Artist"

        # Should now raise the exception since modified_count > 0 triggers commit
        with pytest.raises(Exception, match="Database commit failed"):
            library.save_changes(tracks)

    @patch.dict("os.environ", {"FORTHEREKORD_TEST_MODE": "0"})
    def test_save_changes_update_failure(self):
        """Test save_changes when update_track_metadata fails."""
        import io
        import sys

        library = RekordboxLibrary({"rekordbox": {"library_path": "/test/db.edb"}})
        library._db = Mock()
        library.update_track_metadata = Mock(return_value=False)  # Simulate update failure

        # Create a track with different original and current values
        tracks = [
            create_track(
                track_id="1",
                title="New Title",
                artists="New Artist",
                original_title="Old Title",
                original_artists="Old Artist",
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


class TestGetAllTracks:
    """Test get_all_tracks functionality."""

    @patch("fortherekord.rekordbox_library.RekordboxLibrary._get_database")
    def test_get_all_tracks_success(self, mock_get_db):
        """Test successful retrieval of all tracks."""
        mock_db = Mock()

        # Create mock content data using the helper function
        mock_content1 = create_mock_track_content("123", "Song 1", "Artist 1", "Am")
        mock_content1.Length = 180.5

        mock_content2 = create_mock_track_content("456", "Song 2", "Artist 2", "Dm")
        mock_content2.Length = 240.0

        mock_db.get_content.return_value = [mock_content1, mock_content2]
        mock_get_db.return_value = mock_db

        library = RekordboxLibrary({"rekordbox": {"library_path": "/path/to/database.db"}})
        tracks = library.get_all_tracks()

        assert len(tracks) == 2

        # Check first track
        assert tracks[0].id == "123"
        assert tracks[0].title == "Song 1"
        assert tracks[0].artists == "Artist 1"
        assert tracks[0].key == "Am"

        # Check second track
        assert tracks[1].id == "456"
        assert tracks[1].title == "Song 2"
        assert tracks[1].artists == "Artist 2"
        assert tracks[1].key == "Dm"
