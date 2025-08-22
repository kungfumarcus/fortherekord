"""
Tests for data models.

Tests the core data structures including playlist hierarchy display.
"""

import io
from unittest.mock import patch

from fortherekord.models import Collection, Playlist, Track


class TestPlaylistDisplayTree:
    """Test playlist hierarchy display functionality."""

    def test_display_tree(self, sample_tracks):
        """Test display_tree formats output correctly."""
        # Create children using sample tracks
        child1 = Playlist(
            id="child1",
            name="Child 1",
            tracks=[sample_tracks[0]],  # Use first sample track
        )

        child2 = Playlist(
            id="child2",
            name="Child 2",
            tracks=[],
        )

        # Create a simple hierarchy
        parent = Playlist(id="parent", name="Parent Playlist", tracks=[], children=[child1, child2])

        # Capture stdout
        captured_output = io.StringIO()
        with patch("sys.stdout", captured_output):
            parent.display_tree()

        output = captured_output.getvalue()

        # Should format the entire hierarchy correctly
        expected = """- Parent Playlist
  - Child 1 (1 tracks)
  - Child 2
"""
        assert output == expected


class TestCollection:
    """Test Collection functionality."""

    def test_get_all_tracks_unique(self, sample_tracks):
        """Test get_all_tracks returns unique tracks across playlists."""
        # Create tracks for testing
        track1 = sample_tracks[0]
        track2 = sample_tracks[1] if len(sample_tracks) > 1 else Track(
            id="track2", title="Song 2", artist="Artist 2"
        )
        track3 = Track(id="track3", title="Song 3", artist="Artist 3")

        # Create playlists with overlapping tracks
        playlist1 = Playlist(
            id="playlist1",
            name="Playlist 1", 
            tracks=[track1, track2]
        )
        playlist2 = Playlist(
            id="playlist2",
            name="Playlist 2",
            tracks=[track2, track3]  # track2 is duplicated
        )

        collection = Collection(playlists=[playlist1, playlist2])
        all_tracks = collection.get_all_tracks()

        # Should return unique tracks only
        assert len(all_tracks) == 3
        track_ids = [t.id for t in all_tracks]
        assert track1.id in track_ids
        assert track2.id in track_ids
        assert track3.id in track_ids
        
        # Verify no duplicates
        assert len(set(track_ids)) == len(track_ids)

    def test_get_all_tracks_empty(self):
        """Test get_all_tracks with empty collection."""
        collection = Collection(playlists=[])
        all_tracks = collection.get_all_tracks()
        assert all_tracks == []

    def test_get_all_tracks_empty_playlists(self):
        """Test get_all_tracks with playlists containing no tracks."""
        playlist1 = Playlist(id="playlist1", name="Empty 1", tracks=[])
        playlist2 = Playlist(id="playlist2", name="Empty 2", tracks=[])
        
        collection = Collection(playlists=[playlist1, playlist2])
        all_tracks = collection.get_all_tracks()
        assert all_tracks == []
