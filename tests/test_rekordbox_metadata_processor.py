"""
Tests for metadata processing functionality.

Tests the RekordboxMetadataProcessor class for title enhancement and processing.
"""

import pytest
from fortherekord.rekordbox_metadata_processor import RekordboxMetadataProcessor
from fortherekord.models import Track


class TestRekordboxMetadataProcessor:
    """Test metadata processing functionality."""

    def test_processor_initialization(self):
        """Test processor initializes with config."""
        config = {
            "replace_in_title": {" (Original Mix)": "", " (Extended Mix)": " (ext)"},
            "ignore_playlists": ["test playlist"]
        }
        processor = RekordboxMetadataProcessor(config)
        assert processor.replace_in_title == {" (Original Mix)": "", " (Extended Mix)": " (ext)"}
        assert processor.ignore_playlists == ["test playlist"]

    def test_processor_default_config(self):
        """Test processor works with empty config."""
        processor = RekordboxMetadataProcessor({})
        assert processor.replace_in_title == {}
        assert processor.ignore_playlists == []

    def test_enhance_track_title_basic(self):
        """Test basic title enhancement."""
        config = {}
        processor = RekordboxMetadataProcessor(config)
        
        track = Track(
            id="1",
            title="Test Song",
            artist="Test Artist",
            key="Am",
            bpm=120
        )
        
        enhanced = processor.enhance_track_title(track)
        assert enhanced.title == "Test Song - Test Artist [Am]"
        assert enhanced.artist == "Test Artist"

    def test_enhance_track_title_no_key(self):
        """Test title enhancement without key."""
        config = {}
        processor = RekordboxMetadataProcessor(config)
        
        track = Track(
            id="1",
            title="Test Song",
            artist="Test Artist",
            key=None,
            bpm=120
        )
        
        enhanced = processor.enhance_track_title(track)
        assert enhanced.title == "Test Song - Test Artist"
        assert enhanced.artist == "Test Artist"

    def test_enhance_track_title_extract_artist_from_title(self):
        """Test extracting artist from title when artist field is empty."""
        config = {}
        processor = RekordboxMetadataProcessor(config)
        
        track = Track(
            id="1",
            title="Test Song - Test Artist",
            artist="",
            key="Am",
            bpm=120
        )
        
        enhanced = processor.enhance_track_title(track)
        assert enhanced.title == "Test Song - Test Artist [Am]"
        assert enhanced.artist == "Test Artist"

    def test_enhance_track_title_with_text_replacements(self):
        """Test title enhancement with various text replacement scenarios."""
        config = {
            "replace_in_title": {
                " (Original Mix)": "",  # Remove completely
                " (Extended Mix)": " (ext)",  # Replace with shorter form
                "feat.": "ft.",  # Replace feat. with ft.
                "DJTester": "DJ Tester",  # Space out DJ names
                "remove_me": None  # None should remove text
            }
        }
        processor = RekordboxMetadataProcessor(config)
        
        # Test removal of original mix
        track1 = Track(id="1", title="Test Song (Original Mix)", artist="Test Artist", key="Am", bpm=120)
        result1 = processor.enhance_track_title(track1)
        assert result1.title == "Test Song - Test Artist [Am]"
        
        # Test replacement mapping
        track2 = Track(id="2", title="Test Song (Extended Mix)", artist="Test Artist", key="Am", bpm=120)
        result2 = processor.enhance_track_title(track2)
        assert result2.title == "Test Song (ext) - Test Artist [Am]"
        
        # Test replacement in both title and artist
        track3 = Track(id="3", title="Song feat. Someone", artist="Artist feat. Other", key="Dm", bpm=130)
        result3 = processor.enhance_track_title(track3)
        assert "ft." in result3.title and "ft." in result3.artist
        assert "feat." not in result3.title and "feat." not in result3.artist
        
        # Test null replacement (removal)
        track4 = Track(id="4", title="Song remove_me Test", artist="Test Artist", key="Am", bpm=120)
        result4 = processor.enhance_track_title(track4)
        assert "remove_me" not in result4.title
        assert "Song  Test - Test Artist [Am]" == result4.title
        
        # Test direct _apply_text_replacements method for artist replacement
        title, artist = processor._apply_text_replacements("Test Song", "DJTester")
        assert title == "Test Song"
        assert artist == "DJ Tester"

    def test_enhance_track_title_remove_existing_key(self):
        """Test removing existing key from title."""
        config = {}
        processor = RekordboxMetadataProcessor(config)
        
        track = Track(
            id="1",
            title="Test Song [Dm]",
            artist="Test Artist",
            key="Am",
            bpm=120
        )
        
        enhanced = processor.enhance_track_title(track)
        assert enhanced.title == "Test Song - Test Artist [Am]"

    def test_enhance_track_title_whitespace_cleanup(self):
        """Test whitespace cleanup in title and artist."""
        config = {}
        processor = RekordboxMetadataProcessor(config)
        
        track = Track(
            id="1",
            title="  Test   Song  ",
            artist="  Test   Artist  ",
            key="Am",
            bpm=120
        )
        
        enhanced = processor.enhance_track_title(track)
        assert enhanced.title == "Test Song - Test Artist [Am]"
        assert enhanced.artist == "Test Artist"

    def test_check_for_duplicates_none(self):
        """Test duplicate checking with no duplicates."""
        config = {}
        processor = RekordboxMetadataProcessor(config)
        
        tracks = [
            Track(id="1", title="Song 1", artist="Artist 1", key=None, bpm=120),
            Track(id="2", title="Song 2", artist="Artist 2", key=None, bpm=130)
        ]
        
        # Should not raise any warnings
        processor.check_for_duplicates(tracks)

    def test_check_for_duplicates_found(self, capsys):
        """Test duplicate checking with duplicates found."""
        config = {}
        processor = RekordboxMetadataProcessor(config)
        
        tracks = [
            Track(id="1", title="Same Song", artist="Artist 1", key=None, bpm=120),
            Track(id="2", title="Same Song", artist="Artist 1", key=None, bpm=120)
        ]
        
        processor.check_for_duplicates(tracks)
        captured = capsys.readouterr()
        assert "WARNING: Duplicate track found: Same Song" in captured.out

    def test_extract_original_metadata(self):
        """Test extracting original metadata from enhanced titles on track objects."""
        config = {}
        processor = RekordboxMetadataProcessor(config)
        
        # Create test tracks with enhanced titles
        track1 = Track(
            id="1", 
            title="Test Song - Test Artist [Am]", 
            artist="Test Artist",
            original_title=None,
            original_artist=None
        )
        track2 = Track(
            id="2", 
            title="Another Song - Another Artist", 
            artist="Another Artist",
            original_title=None,
            original_artist=None
        )
        track3 = Track(
            id="3", 
            title="Simple Song", 
            artist="Simple Artist",
            original_title=None,
            original_artist=None
        )
        track4 = Track(
            id="4", 
            title="Original Title - Artist One [Am] - Artist Two [Cm] - Artist Three [Gm]", 
            artist="Artist Three",
            original_title=None,
            original_artist=None
        )
        
        tracks = [track1, track2, track3, track4]
        
        # Process tracks
        processor.extract_original_metadata(tracks)
        
        # Check results
        assert track1.original_title == "Test Song"
        assert track1.original_artist == "Test Artist"
        
        assert track2.original_title == "Another Song"
        assert track2.original_artist == "Another Artist"
        
        # Track with no enhancement should use current values
        assert track3.original_title == "Simple Song"
        assert track3.original_artist == "Simple Artist"
        
        # Track with multiple artist/key instances should remove all of them
        assert track4.original_title == "Original Title"
        assert track4.original_artist == "Artist Three"

    def test_remove_duplicate_artists_empty_artist(self):
        """Test removing duplicates when artist is empty."""
        config = {}
        processor = RekordboxMetadataProcessor(config)
        
        result = processor._remove_duplicate_artists("Test Song", "")
        assert result == ""

    def test_remove_duplicate_artists_no_removal_when_no_retained(self):
        """Test no removal when all artists would be removed."""
        config = {}
        processor = RekordboxMetadataProcessor(config)
        
        # Artist appears in title, but no other artists to retain
        result = processor._remove_duplicate_artists("Test Song by Artist", "Artist")
        assert result == "Artist"  # Should keep original since no retained artists

    def test_remove_duplicate_artists_partial_removal(self):
        """Test partial removal when some artists are duplicated."""
        config = {}
        processor = RekordboxMetadataProcessor(config)
        
        # Mix of duplicated and unique artists
        result = processor._remove_duplicate_artists("Test Song by Artist1", "Artist1, Artist2")
        assert result == "Artist2"  # Should remove Artist1, keep Artist2

    def test_should_ignore_playlist(self):
        """Test playlist filtering."""
        config = {"ignore_playlists": ["ignored playlist", "test"]}
        processor = RekordboxMetadataProcessor(config)
        
        assert processor.should_ignore_playlist("ignored playlist") is True
        assert processor.should_ignore_playlist("test") is True
        assert processor.should_ignore_playlist("allowed playlist") is False

    def test_enhance_track_title_remove_artist_suffix(self):
        """Test removal of artist suffix when already present in title."""
        config = {}
        processor = RekordboxMetadataProcessor(config)
        
        # Track with title that already ends with " - Artist"
        track = Track(
            id="1",
            title="Song Title - Test Artist",
            artist="Test Artist",
            key="Cm",
            bpm=128
        )
        
        result = processor.enhance_track_title(track)
        
        # Should not duplicate the artist suffix
        assert result.title == "Song Title - Test Artist [Cm]"
