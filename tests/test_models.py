"""
Tests for data models.

Tests the core data structures including playlist hierarchy display.
"""

import io
from unittest.mock import patch

from fortherekord.models import Track, Playlist


class TestPlaylistDisplayTree:
    """Test playlist hierarchy display functionality."""

    def test_display_tree(self):
        """Test display_tree formats output correctly."""
        # Create children
        child1 = Playlist(
            id="child1",
            name="Child 1",
            tracks=[Track(id="1", title="Song 1", artist="Artist 1")],
        )
        
        child2 = Playlist(
            id="child2",
            name="Child 2",
            tracks=[],
        )
        
        # Create a simple hierarchy
        parent = Playlist(
            id="parent",
            name="Parent Playlist",
            tracks=[],
            children=[child1, child2]
        )
        
        # Capture stdout
        captured_output = io.StringIO()
        with patch('sys.stdout', captured_output):
            parent.display_tree()
        
        output = captured_output.getvalue()
        
        # Should format the entire hierarchy correctly
        expected = """- Parent Playlist
  - Child 1 (1 tracks)
  - Child 2
"""
        assert output == expected