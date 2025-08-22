"""
Tests for MusicLibrary base class utilities.

Tests the common utility functions provided by the MusicLibrary base class.
"""

from fortherekord.music_library import MusicLibrary
from fortherekord.models import Track, Playlist


class TestMusicLibrary:
    """Test MusicLibrary base class utilities."""

    def setup_method(self):
        """Set up test instance."""

        # Create a concrete subclass for testing
        class TestMusicLibraryImpl(MusicLibrary):
            def _get_raw_playlists(self, ignore_playlists=None):
                return []

        self.library = TestMusicLibraryImpl()

    def test_deduplicate_tracks(self):
        """Test track deduplication."""
        track1 = Track(id="1", title="Song 1", artist="Artist 1")
        track2 = Track(id="2", title="Song 2", artist="Artist 2")
        track3 = Track(id="1", title="Song 1", artist="Artist 1")  # Duplicate

        tracks = [track1, track2, track3]
        result = self.library.deduplicate_tracks(tracks)

        assert len(result) == 2
        assert result[0] == track1
        assert result[1] == track2

    def test_filter_playlists_by_name(self):
        """Test playlist filtering by name."""
        playlist1 = Playlist(id="1", name="Keep This", tracks=[])
        playlist2 = Playlist(id="2", name="Ignore This", tracks=[])
        playlist3 = Playlist(id="3", name="Also Keep", tracks=[])

        playlists = [playlist1, playlist2, playlist3]
        ignore_list = ["Ignore This"]

        result = self.library.filter_playlists_by_name(playlists, ignore_list)

        assert len(result) == 2
        assert result[0] == playlist1
        assert result[1] == playlist3

    def test_filter_playlists_by_name_no_ignore_list(self):
        """Test playlist filtering with no ignore list."""
        playlist1 = Playlist(id="1", name="Playlist 1", tracks=[])
        playlist2 = Playlist(id="2", name="Playlist 2", tracks=[])

        playlists = [playlist1, playlist2]
        result = self.library.filter_playlists_by_name(playlists, None)

        assert result == playlists

    def test_filter_empty_playlists(self):
        """Test filtering out empty playlists."""
        track = Track(id="1", title="Song", artist="Artist")

        playlist_with_tracks = Playlist(id="1", name="Has Tracks", tracks=[track])
        empty_playlist = Playlist(id="2", name="Empty", tracks=[])

        playlists = [playlist_with_tracks, empty_playlist]
        result = self.library.filter_empty_playlists(playlists)

        assert len(result) == 1
        assert result[0] == playlist_with_tracks

    def test_get_all_tracks_from_playlists(self):
        """Test extracting all tracks from playlists with deduplication."""
        track1 = Track(id="1", title="Song 1", artist="Artist 1")
        track2 = Track(id="2", title="Song 2", artist="Artist 2")
        track3 = Track(id="1", title="Song 1", artist="Artist 1")  # Duplicate

        playlist1 = Playlist(id="1", name="Playlist 1", tracks=[track1, track2])
        playlist2 = Playlist(id="2", name="Playlist 2", tracks=[track3])

        playlists = [playlist1, playlist2]
        result = self.library.get_all_tracks_from_playlists(playlists)

        # Should deduplicate track1/track3
        assert len(result) == 2
        assert track1 in result
        assert track2 in result

    def test_get_collection_with_config(self):
        """Test get_collection with ignore_playlists config."""
        # Mock the _get_raw_playlists method
        playlist1 = Playlist(id="1", name="Keep", tracks=[])
        playlist2 = Playlist(id="2", name="Ignore", tracks=[])

        class TestMusicLibraryWithPlaylists(MusicLibrary):
            def _get_raw_playlists(self, ignore_playlists=None):
                playlists = [playlist1, playlist2]
                if ignore_playlists and "Ignore" in ignore_playlists:
                    return [playlist1]
                return playlists

        library = TestMusicLibraryWithPlaylists()
        config = {"ignore_playlists": ["Ignore"]}

        collection = library.get_collection(config)

        assert len(collection.playlists) == 1
        assert collection.playlists[0].name == "Keep"

    def test_get_collection_no_config(self):
        """Test get_collection with no config."""
        playlist1 = Playlist(id="1", name="Playlist 1", tracks=[])

        class TestMusicLibraryWithPlaylists(MusicLibrary):
            def _get_raw_playlists(self, ignore_playlists=None):
                return [playlist1]

        library = TestMusicLibraryWithPlaylists()
        collection = library.get_collection(None)

        assert len(collection.playlists) == 1
        assert collection.playlists[0] == playlist1
