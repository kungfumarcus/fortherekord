"""
Tests for music library processing functionality.

Tests the MusicLibraryProcessor class for title enhancement and processing.
"""

from fortherekord.music_library_processor import MusicLibraryProcessor
from .conftest import create_track


class TestMusicLibraryProcessor:
    """Test music library processing functionality."""

    def test_processor_initialization(self):
        """Test processor initializes with config."""
        config = {
            "replace_in_title": [
                {"from": " (Original Mix)", "to": ""},
                {"from": " (Extended Mix)", "to": " (ext)"},
            ],
            "ignore_playlists": ["test playlist"],
        }
        processor = MusicLibraryProcessor(config)
        assert processor.replace_in_title == [
            {"from": " (Original Mix)", "to": ""},
            {"from": " (Extended Mix)", "to": " (ext)"},
        ]

    def test_processor_default_config(self, default_processor_config):
        """Test processor works with empty config."""
        processor = MusicLibraryProcessor(default_processor_config)
        assert processor.replace_in_title == []

    def test_process_track_basic(self, sample_track, default_processor_config, capsys):
        """Test basic title enhancement with output capture."""
        processor = MusicLibraryProcessor(default_processor_config)
        processor.process_track(sample_track)
        assert sample_track.title == "Test Song - Test Artist [Am]"
        assert sample_track.artists == "Test Artist"

        # Capture printed output
        captured = capsys.readouterr()
        assert "Updating title 'Test Song' to 'Test Song - Test Artist [Am]'" in captured.out

    def test_process_track_no_key(self, sample_track_no_key, default_processor_config):
        """Test title enhancement without key."""
        processor = MusicLibraryProcessor(default_processor_config)
        processor.process_track(sample_track_no_key)
        assert sample_track_no_key.title == "Test Song - Test Artist"
        assert sample_track_no_key.artists == "Test Artist"

    def test_process_track_extract_artist_from_title(self, default_processor_config):
        """Test extracting artists from title when artists field is empty."""
        processor = MusicLibraryProcessor(default_processor_config)
        track = create_track(title="Test Song - Test Artist", artists="")
        processor.process_track(track)
        assert track.title == "Test Song - Test Artist [Am]"
        assert track.artists == "Test Artist"

    def test_process_track_with_text_replacements(self, default_processor_config):
        """Test title enhancement with various text replacement scenarios."""
        # Start with default config and add text replacements
        config = default_processor_config
        config["replace_in_title"] = [
            {"from": " (Original Mix)", "to": ""},  # Remove completely
            {"from": " (Extended Mix)", "to": " (ext)"},  # Replace with shorter form
            {"from": "feat.", "to": "ft."},  # Replace feat. with ft.
            {"from": "DJTester", "to": "DJ Tester"},  # Space out DJ names
            {"from": "remove_me", "to": ""},  # Empty string should remove text
        ]
        processor = MusicLibraryProcessor(config)

        # Test removal of original mix
        track1 = create_track(title="Test Song (Original Mix)")
        processor.process_track(track1)
        assert track1.title == "Test Song - Test Artist [Am]"

        # Test replacement mapping
        track2 = create_track(title="Test Song (Extended Mix)")
        processor.process_track(track2)
        assert track2.title == "Test Song (ext) - Test Artist [Am]"

        # Test replacement in both title and artists
        track3 = create_track(title="Song feat. Someone", artists="Artist feat. Other", key="Dm")
        processor.process_track(track3)
        assert "ft." in track3.title and "ft." in track3.artists
        assert "feat." not in track3.title and "feat." not in track3.artists

        # Test null replacement (removal)
        track4 = create_track(title="Song remove_me Test")
        processor.process_track(track4)
        assert "remove_me" not in track4.title
        assert "Song  Test - Test Artist [Am]" == track4.title

        # Test direct _apply_text_replacements method for artists replacement
        title, artists = processor._apply_text_replacements("Test Song", "DJTester")
        assert title == "Test Song"
        assert artists == "DJ Tester"

    def test_process_track_remove_existing_key(self, default_processor_config):
        """Test removing existing key from title."""
        processor = MusicLibraryProcessor(default_processor_config)
        track = create_track(title="Test Song [Dm]")
        processor.process_track(track)
        assert track.title == "Test Song - Test Artist [Am]"

    def test_process_track_whitespace_cleanup(self, default_processor_config):
        """Test whitespace cleanup in title and artists."""
        processor = MusicLibraryProcessor(default_processor_config)

        track = create_track(
            track_id="1", title="  Test   Song  ", artists="  Test   Artist  ", key="Am"
        )

        processor.process_track(track)
        assert track.title == "Test Song - Test Artist [Am]"
        assert track.artists == "Test Artist"

    def test_check_for_duplicates_none(self):
        """Test duplicate checking with no duplicates."""
        config = {}
        processor = MusicLibraryProcessor(config)

        tracks = [
            create_track(track_id="1", title="Song 1", artists="Artist 1", key=None),
            create_track(track_id="2", title="Song 2", artists="Artist 2", key=None),
        ]

        # Should not raise any warnings
        processor.check_for_duplicates(tracks)

    def test_check_for_duplicates_found(self, default_processor_config, capsys):
        """Test duplicate checking with duplicates found."""
        processor = MusicLibraryProcessor(default_processor_config)

        tracks = [
            create_track(track_id="1", title="Same Song", artists="Artist 1", key=None),
            create_track(track_id="2", title="Same Song", artists="Artist 1", key=None),
        ]

        processor.check_for_duplicates(tracks)
        captured = capsys.readouterr()
        assert "WARNING: Duplicate track found: Same Song" in captured.out

    def test_split_artists_by_title_empty_artist(self, default_processor_config):
        """Test splitting artists when artists is empty."""
        processor = MusicLibraryProcessor(default_processor_config)

        not_in_title, in_title = processor._split_artists_by_title("Test Song", "")
        assert not_in_title == ""
        assert in_title == ""

    def test_split_artists_by_title_no_removal_when_no_retained(self, default_processor_config):
        """Test no removal when all artists would be removed."""
        config = {}
        processor = MusicLibraryProcessor(config)

        # Artist appears in title, but no other artists to retain
        not_in_title, in_title = processor._split_artists_by_title("Test Song by Artist", "Artist")
        assert not_in_title == "Artist"  # Should keep original since no retained artists
        assert in_title == "Artist"

    def test_split_artists_by_title_partial_removal(self, default_processor_config):
        """Test partial removal when some artists are duplicated."""
        config = {}
        processor = MusicLibraryProcessor(config)

        # Mix of duplicated and unique artists
        not_in_title, in_title = processor._split_artists_by_title("Test Song by Artist1", "Artist1, Artist2")
        assert not_in_title == "Artist2"  # Should remove Artist1, keep Artist2
        assert in_title == "Artist1"

    def test_process_track_remove_artist_suffix(self, default_processor_config):
        """Test removal of artists suffix when already present in title."""
        processor = MusicLibraryProcessor(default_processor_config)

        # Track with title that already ends with " - Artist"
        track = create_track(
            track_id="1", title="Song Title - Test Artist", artists="Test Artist", key="Cm"
        )

        processor.process_track(track)

        # Should not duplicate the artists suffix
        assert track.title == "Song Title - Test Artist [Cm]"

    def test_process_track_output_both_changes(self, default_processor_config, capsys):
        """Test output when both title and artists change."""
        config = default_processor_config
        config["replace_in_title"] = [{"from": "Old Artist", "to": "New Artist"}]
        processor = MusicLibraryProcessor(config)
        track = create_track(title="Song Title", artists="Old Artist", key="Cm")

        processor.process_track(track)

        captured = capsys.readouterr()
        assert (
            "Updating title 'Song Title' to 'Song Title - New Artist [Cm]' "
            "and artists 'Old Artist' to 'New Artist'" in captured.out
        )

    def test_process_track_output_no_changes(self, default_processor_config, capsys):
        """Test no output when no changes are made."""
        processor = MusicLibraryProcessor(default_processor_config)
        track = create_track(title="Song Title - Test Artist [Cm]", artists="Test Artist", key="Cm")
        # The helper already sets original values to match current values

        processor.process_track(track)

        captured = capsys.readouterr()
        assert captured.out == ""  # No output when no changes

    def test_processor_early_abort_all_disabled(self, sample_track):
        """Test that when all enhancement features are False, tracks are returned unchanged."""
        config = {
            "processor": {
                "add_key_to_title": False,
                "add_artist_to_title": False,
                "remove_artists_in_title": False,
            }
        }
        processor = MusicLibraryProcessor(config)
        original_title = sample_track.title
        original_artists = sample_track.artists

        processor.process_track(sample_track)

        # Track should be returned unchanged
        assert sample_track.title == original_title
        assert sample_track.artists == original_artists

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
        sample_track_disabled = create_track()
        processor_disabled.process_track(sample_track_disabled)
        assert "[Am]" not in sample_track_disabled.title

    def test_add_artist_to_title_flag(self):
        """Test add_artist_to_title flag controls whether artists are added."""
        # Test with artists enabled
        config_enabled = {
            "add_key_to_title": True,
            "add_artist_to_title": True,
            "remove_artists_in_title": True,
        }
        processor_enabled = MusicLibraryProcessor(config_enabled)
        sample_track_enabled = create_track()
        processor_enabled.process_track(sample_track_enabled)
        assert "- Test Artist" in sample_track_enabled.title

        # Test with artists disabled
        config_disabled = {
            "add_key_to_title": True,
            "add_artist_to_title": False,
            "remove_artists_in_title": True,
        }
        processor_disabled = MusicLibraryProcessor(config_disabled)
        sample_track_disabled = create_track()
        processor_disabled.process_track(sample_track_disabled)
        assert "- Test Artist" not in sample_track_disabled.title

    def test_remove_artists_in_title_flag(self):
        """Test remove_artists_in_title flag controls whether duplicate artists are removed."""
        # Create a track where artists appears in title
        track = create_track(
            track_id="test_id",
            title="Party (Subsonic mix) - Dazza, Subsonic",
            artists="Dazza, Subsonic",
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
        # Should keep original artists field unchanged
        assert track.artists == "Dazza, Subsonic"
        # But title should only include artists not already in title content ("Dazza")
        assert track.title == "Party (Subsonic mix) - Dazza [Am]"

        # Test with remove_artists_in_title disabled
        config_disabled = {
            "add_key_to_title": True,
            "add_artist_to_title": True,
            "remove_artists_in_title": False,
        }
        processor_disabled = MusicLibraryProcessor(config_disabled)
        track_disabled = create_track(
            track_id="test_id",
            title="Party (Subsonic mix) - Dazza, Subsonic",
            artists="Dazza, Subsonic",
            key="Am",
        )
        processor_disabled.process_track(track_disabled)
        # Should keep all artists in both field and title
        assert track_disabled.artists == "Dazza, Subsonic"
        assert track_disabled.title == "Party (Subsonic mix) - Dazza, Subsonic [Am]"
