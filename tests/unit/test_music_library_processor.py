"""
Tests for music library processing functionality.

Tests the MusicLibraryProcessor class for title enhancement and processing.
"""

from fortherekord.music_library_processor import MusicLibraryProcessor
from fortherekord.models import Track
from .conftest import create_sample_track


class TestMusicLibraryProcessor:
    """Test music library processing functionality."""

    def test_processor_initialization(self):
        """Test processor initializes with config."""
        config = {
            "replace_in_title": {" (Original Mix)": "", " (Extended Mix)": " (ext)"},
            "ignore_playlists": ["test playlist"],
        }
        processor = MusicLibraryProcessor(config)
        assert processor.replace_in_title == {" (Original Mix)": "", " (Extended Mix)": " (ext)"}
        assert processor.ignore_playlists == ["test playlist"]

    def test_processor_default_config(self, default_processor_config):
        """Test processor works with empty config."""
        processor = MusicLibraryProcessor(default_processor_config)
        assert processor.replace_in_title == {}
        assert processor.ignore_playlists == []

    def test_process_track_basic(self, sample_track, default_processor_config, capsys):
        """Test basic title enhancement with output capture."""
        processor = MusicLibraryProcessor(default_processor_config)
        processor.process_track(sample_track)
        assert sample_track.title == "Test Song - Test Artist [Am]"
        assert sample_track.artist == "Test Artist"

        # Capture printed output
        captured = capsys.readouterr()
        assert "Updating title 'Test Song' to 'Test Song - Test Artist [Am]'" in captured.out

    def test_process_track_no_key(self, sample_track_no_key, default_processor_config):
        """Test title enhancement without key."""
        processor = MusicLibraryProcessor(default_processor_config)
        processor.process_track(sample_track_no_key)
        assert sample_track_no_key.title == "Test Song - Test Artist"
        assert sample_track_no_key.artist == "Test Artist"

    def test_process_track_extract_artist_from_title(self, default_processor_config):
        """Test extracting artist from title when artist field is empty."""
        processor = MusicLibraryProcessor(default_processor_config)
        track = create_sample_track(title="Test Song - Test Artist", artist="")
        processor.process_track(track)
        assert track.title == "Test Song - Test Artist [Am]"
        assert track.artist == "Test Artist"

    def test_process_track_with_text_replacements(self, default_processor_config):
        """Test title enhancement with various text replacement scenarios."""
        # Start with default config and add text replacements
        config = default_processor_config
        config["replace_in_title"] = {
            " (Original Mix)": "",  # Remove completely
            " (Extended Mix)": " (ext)",  # Replace with shorter form
            "feat.": "ft.",  # Replace feat. with ft.
            "DJTester": "DJ Tester",  # Space out DJ names
            "remove_me": None,  # None should remove text
        }
        processor = MusicLibraryProcessor(config)

        # Test removal of original mix
        track1 = create_sample_track(title="Test Song (Original Mix)")
        processor.process_track(track1)
        assert track1.title == "Test Song - Test Artist [Am]"

        # Test replacement mapping
        track2 = create_sample_track(title="Test Song (Extended Mix)")
        processor.process_track(track2)
        assert track2.title == "Test Song (ext) - Test Artist [Am]"

        # Test replacement in both title and artist
        track3 = create_sample_track(
            title="Song feat. Someone", artist="Artist feat. Other", key="Dm"
        )
        processor.process_track(track3)
        assert "ft." in track3.title and "ft." in track3.artist
        assert "feat." not in track3.title and "feat." not in track3.artist

        # Test null replacement (removal)
        track4 = create_sample_track(title="Song remove_me Test")
        processor.process_track(track4)
        assert "remove_me" not in track4.title
        assert "Song  Test - Test Artist [Am]" == track4.title

        # Test direct _apply_text_replacements method for artist replacement
        title, artist = processor._apply_text_replacements("Test Song", "DJTester")
        assert title == "Test Song"
        assert artist == "DJ Tester"

    def test_process_track_remove_existing_key(self, default_processor_config):
        """Test removing existing key from title."""
        processor = MusicLibraryProcessor(default_processor_config)
        track = create_sample_track(title="Test Song [Dm]")
        processor.process_track(track)
        assert track.title == "Test Song - Test Artist [Am]"

    def test_process_track_whitespace_cleanup(self, default_processor_config):
        """Test whitespace cleanup in title and artist."""
        processor = MusicLibraryProcessor(default_processor_config)

        track = Track(id="1", title="  Test   Song  ", artist="  Test   Artist  ", key="Am")

        processor.process_track(track)
        assert track.title == "Test Song - Test Artist [Am]"
        assert track.artist == "Test Artist"

    def test_check_for_duplicates_none(self):
        """Test duplicate checking with no duplicates."""
        config = {}
        processor = MusicLibraryProcessor(config)

        tracks = [
            create_sample_track(track_id="1", title="Song 1", artist="Artist 1", key=None),
            create_sample_track(track_id="2", title="Song 2", artist="Artist 2", key=None),
        ]

        # Should not raise any warnings
        processor.check_for_duplicates(tracks)

    def test_check_for_duplicates_found(self, default_processor_config, capsys):
        """Test duplicate checking with duplicates found."""
        processor = MusicLibraryProcessor(default_processor_config)

        tracks = [
            create_sample_track(track_id="1", title="Same Song", artist="Artist 1", key=None),
            create_sample_track(track_id="2", title="Same Song", artist="Artist 1", key=None),
        ]

        processor.check_for_duplicates(tracks)
        captured = capsys.readouterr()
        assert "WARNING: Duplicate track found: Same Song" in captured.out

    def test_extract_original_metadata(self, default_processor_config):
        """Test extracting original metadata from enhanced titles on track objects."""
        processor = MusicLibraryProcessor(default_processor_config)

        # Create test tracks with enhanced titles
        track1 = Track(
            id="1",
            title="Test Song - Test Artist [Am]",
            artist="Test Artist",
            original_title=None,
            original_artist=None,
        )
        track2 = Track(
            id="2",
            title="Another Song - Another Artist",
            artist="Another Artist",
            original_title=None,
            original_artist=None,
        )
        track3 = Track(
            id="3",
            title="Simple Song",
            artist="Simple Artist",
            original_title=None,
            original_artist=None,
        )
        track4 = Track(
            id="4",
            title="Original Title - Artist One [Am] - Artist Two [Cm] - Artist Three [Gm]",
            artist="Artist Three",
            original_title=None,
            original_artist=None,
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

    def test_remove_duplicate_artists_empty_artist(self, default_processor_config):
        """Test removing duplicates when artist is empty."""
        processor = MusicLibraryProcessor(default_processor_config)

        result = processor._remove_duplicate_artists("Test Song", "")
        assert result == ""

    def test_remove_duplicate_artists_no_removal_when_no_retained(self, default_processor_config):
        """Test no removal when all artists would be removed."""
        config = {}
        processor = MusicLibraryProcessor(config)

        # Artist appears in title, but no other artists to retain
        result = processor._remove_duplicate_artists("Test Song by Artist", "Artist")
        assert result == "Artist"  # Should keep original since no retained artists

    def test_remove_duplicate_artists_partial_removal(self, default_processor_config):
        """Test partial removal when some artists are duplicated."""
        config = {}
        processor = MusicLibraryProcessor(config)

        # Mix of duplicated and unique artists
        result = processor._remove_duplicate_artists("Test Song by Artist1", "Artist1, Artist2")
        assert result == "Artist2"  # Should remove Artist1, keep Artist2

    def test_should_ignore_playlist(self, default_processor_config):
        """Test playlist filtering."""
        config = default_processor_config
        config["ignore_playlists"] = ["ignored playlist", "test"]
        processor = MusicLibraryProcessor(config)

        assert processor.should_ignore_playlist("ignored playlist") is True
        assert processor.should_ignore_playlist("test") is True
        assert processor.should_ignore_playlist("allowed playlist") is False

    def test_process_track_remove_artist_suffix(self, default_processor_config):
        """Test removal of artist suffix when already present in title."""
        processor = MusicLibraryProcessor(default_processor_config)

        # Track with title that already ends with " - Artist"
        track = Track(id="1", title="Song Title - Test Artist", artist="Test Artist", key="Cm")

        processor.process_track(track)

        # Should not duplicate the artist suffix
        assert track.title == "Song Title - Test Artist [Cm]"

    def test_process_track_output_both_changes(self, default_processor_config, capsys):
        """Test output when both title and artist change."""
        config = default_processor_config
        config["replace_in_title"] = {"Old Artist": "New Artist"}
        processor = MusicLibraryProcessor(config)
        track = Track(id="1", title="Song Title", artist="Old Artist", key="Cm")

        processor.process_track(track)

        captured = capsys.readouterr()
        assert (
            "Updating title 'Song Title' to 'Song Title - New Artist [Cm]' "
            "and artist 'Old Artist' to 'New Artist'" in captured.out
        )

    def test_process_track_output_no_changes(self, default_processor_config, capsys):
        """Test no output when no changes are made."""
        processor = MusicLibraryProcessor(default_processor_config)
        track = Track(id="1", title="Song Title - Test Artist [Cm]", artist="Test Artist", key="Cm")

        processor.process_track(track)

        captured = capsys.readouterr()
        assert captured.out == ""  # No output when no changes

    def test_processor_early_abort_all_disabled(self, sample_track):
        """Test that when all enhancement features are False, tracks are returned unchanged."""
        config = {
            "add_key_to_title": False,
            "add_artist_to_title": False,
            "remove_artists_in_title": False,
        }
        processor = MusicLibraryProcessor(config)
        original_title = sample_track.title
        original_artist = sample_track.artist

        processor.process_track(sample_track)

        # Track should be returned unchanged
        assert sample_track.title == original_title
        assert sample_track.artist == original_artist

    def test_add_key_to_title_flag(self, sample_track):
        """Test add_key_to_title flag controls whether keys are added."""
        # Test with key enabled
        config_enabled = {
            "add_key_to_title": True,
            "add_artist_to_title": True,
            "remove_artists_in_title": True,
        }
        processor_enabled = MusicLibraryProcessor(config_enabled)
        processor_enabled.process_track(sample_track)
        assert "[Am]" in sample_track.title

        # Test with key disabled
        config_disabled = {
            "add_key_to_title": False,
            "add_artist_to_title": True,
            "remove_artists_in_title": True,
        }
        processor_disabled = MusicLibraryProcessor(config_disabled)
        sample_track_disabled = create_sample_track()
        processor_disabled.process_track(sample_track_disabled)
        assert "[Am]" not in sample_track_disabled.title

    def test_add_artist_to_title_flag(self):
        """Test add_artist_to_title flag controls whether artists are added."""
        # Test with artist enabled
        config_enabled = {
            "add_key_to_title": True,
            "add_artist_to_title": True,
            "remove_artists_in_title": True,
        }
        processor_enabled = MusicLibraryProcessor(config_enabled)
        sample_track_enabled = create_sample_track()
        processor_enabled.process_track(sample_track_enabled)
        assert "- Test Artist" in sample_track_enabled.title

        # Test with artist disabled
        config_disabled = {
            "add_key_to_title": True,
            "add_artist_to_title": False,
            "remove_artists_in_title": True,
        }
        processor_disabled = MusicLibraryProcessor(config_disabled)
        sample_track_disabled = create_sample_track()
        processor_disabled.process_track(sample_track_disabled)
        assert "- Test Artist" not in sample_track_disabled.title

    def test_remove_artists_in_title_flag(self):
        """Test remove_artists_in_title flag controls whether duplicate artists are removed."""
        # Create a track where artist appears in title
        track = Track(
            id="test_id",
            title="Party (Subsonic mix) - Dazza, Subsonic",
            artist="Dazza, Subsonic",
            key="Am",
        )

        # Test with remove_artists_in_title enabled
        config_enabled = {
            "add_key_to_title": True,
            "add_artist_to_title": True,
            "remove_artists_in_title": True,
        }
        processor_enabled = MusicLibraryProcessor(config_enabled)
        processor_enabled.process_track(track)
        # Should remove "Subsonic" from artist list since it's in title content
        assert "Dazza" in track.artist
        assert "Subsonic" not in track.artist

        # Test with remove_artists_in_title disabled
        config_disabled = {
            "add_key_to_title": True,
            "add_artist_to_title": True,
            "remove_artists_in_title": False,
        }
        processor_disabled = MusicLibraryProcessor(config_disabled)
        track_disabled = Track(
            id="test_id",
            title="Party (Subsonic mix) - Dazza, Subsonic",
            artist="Dazza, Subsonic",
            key="Am",
        )
        processor_disabled.process_track(track_disabled)
        # Should keep all artists
        assert "Dazza" in track_disabled.artist
        assert "Subsonic" in track_disabled.artist
