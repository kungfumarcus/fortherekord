"""
Tests for MusicLibrary base class utilities.

Tests the common utility functions provided by the MusicLibrary base class.
"""

from fortherekord.music_library import MusicLibrary
from fortherekord.models import Track, Playlist, Collection


class TestMusicLibrary:
    """Test MusicLibrary base class utilities."""

    def setup_method(self):
        """Set up test instance."""

        # Create a concrete subclass for testing
        class TestMusicLibraryImpl(MusicLibrary):
            def get_collection(self):
                return Collection(playlists=getattr(self, "_test_playlists", []), tracks={})

            def save_changes(self, tracks, dry_run=False):
                """Mock implementation of save_changes."""
                pass

        self.library = TestMusicLibraryImpl()
        self.library._test_playlists = []  # Mock playlists for testing

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

    def test_get_collection_filters_playlists(self):
        """Test that get_filtered_collection filters playlists by ignore_playlists."""
        playlist1 = Playlist(id="1", name="Keep This", tracks=[])
        playlist2 = Playlist(id="2", name="Ignore This", tracks=[])
        playlist3 = Playlist(id="3", name="Also Keep", tracks=[])

        # Set up the test implementation to return these playlists
        self.library._test_playlists = [playlist1, playlist2, playlist3]
        self.library.config = {"rekordbox": {"ignore_playlists": ["Ignore This"]}}

        collection = self.library.get_filtered_collection()

        assert len(collection.playlists) == 2
        assert collection.playlists[0] == playlist1
        assert collection.playlists[1] == playlist3

    def test_get_collection_no_filtering(self):
        """Test get_filtered_collection with no ignore list."""
        playlist1 = Playlist(id="1", name="Playlist 1", tracks=[])
        playlist2 = Playlist(id="2", name="Playlist 2", tracks=[])

        # Set up the test implementation to return these playlists
        self.library._test_playlists = [playlist1, playlist2]
        self.library.config = {"rekordbox": {"ignore_playlists": []}}

        collection = self.library.get_filtered_collection()

        assert len(collection.playlists) == 2
        assert collection.playlists == [playlist1, playlist2]

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
