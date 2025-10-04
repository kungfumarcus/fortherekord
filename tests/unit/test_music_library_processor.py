"""
Tests for music library processing functionality.

Tests the MusicLibraryProcessor class for title enhancement and processing.
"""

from unittest.mock import Mock
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
        assert sample_track.enhanced_title == "Test Song - Test Artist [Am]"
        assert sample_track.artists == "Test Artist"

        # Capture printed output
        captured = capsys.readouterr()
        # Expect output showing title enhancement
        assert "Updating title 'Test Song' to 'Test Song - Test Artist [Am]'" in captured.out

    def test_process_track_no_key(self, sample_track_no_key, default_processor_config):
        """Test title enhancement without key."""
        processor = MusicLibraryProcessor(default_processor_config)
        processor.process_track(sample_track_no_key)
        assert sample_track_no_key.enhanced_title == "Test Song - Test Artist"
        assert sample_track_no_key.artists == "Test Artist"

    def test_process_track_extract_artist_from_title(self, default_processor_config):
        """Test extracting artists from title when artists field is empty."""
        processor = MusicLibraryProcessor(default_processor_config)
        track = create_track(title="Test Song - Test Artist", artists="")
        processor.process_track(track)
        assert track.enhanced_title == "Test Song - Test Artist [Am]"
        assert track.artists == "Test Artist"

    def test_process_track_with_text_replacements(self, default_processor_config):
        """Test title enhancement with various text replacement scenarios."""
        # Start with default config and add text replacements
        config = default_processor_config
        config["replace_in_title"] = [
            {"from": " (Original Mix)", "to": ""},  # Remove completely
            {"from": " (Extended Mix)", "to": " (ext)"},  # Replace with shorter form
            {"from": "feat.", "to": "ft."},  # Replace feat. with ft.
            {"from": "remove_me", "to": ""},  # Empty string should remove text
        ]
        config["replace_in_artist"] = [
            {"from": "DJTester", "to": "DJ Tester"},  # Space out DJ names
            {"from": "feat.", "to": "ft."},  # Replace feat. with ft. in artists too
        ]
        processor = MusicLibraryProcessor(config)

        # Test removal of original mix
        track1 = create_track(title="Test Song (Original Mix)")
        processor.process_track(track1)
        assert track1.enhanced_title == "Test Song - Test Artist [Am]"

        # Test replacement mapping
        track2 = create_track(title="Test Song (Extended Mix)")
        processor.process_track(track2)
        assert track2.enhanced_title == "Test Song (ext) - Test Artist [Am]"

        # Test replacement in both title and artists
        track3 = create_track(title="Song feat. Someone", artists="Artist feat. Other", key="Dm")
        processor.process_track(track3)
        assert "ft." in track3.title and "ft." in track3.artists
        assert "feat." not in track3.title and "feat." not in track3.artists

        # Test null replacement (removal)
        track4 = create_track(title="Song remove_me Test")
        processor.process_track(track4)
        assert "remove_me" not in track4.title
        assert "Song  Test - Test Artist [Am]" == track4.enhanced_title

        # Test direct _apply_text_replacements method for artists replacement
        title, artists = processor._apply_text_replacements("Test Song", "DJTester")
        assert title == "Test Song"
        assert artists == "DJ Tester"

    def test_process_track_remove_existing_key(self, default_processor_config):
        """Test removing existing key from title."""
        processor = MusicLibraryProcessor(default_processor_config)
        track = create_track(title="Test Song [Dm]")
        processor.process_track(track)
        assert track.enhanced_title == "Test Song - Test Artist [Am]"

    def test_process_track_whitespace_cleanup(self, default_processor_config):
        """Test whitespace cleanup in title and artists."""
        processor = MusicLibraryProcessor(default_processor_config)

        track = create_track(
            track_id="1", title="  Test   Song  ", artists="  Test   Artist  ", key="Am"
        )

        processor.process_track(track)
        assert track.enhanced_title == "Test Song - Test Artist [Am]"
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
        assert "WARNING: 2 duplicate tracks found: 'same song' by 'artist 1'" in captured.out

    def test_check_for_duplicates_found_no_artist(self, default_processor_config, capsys):
        """Test duplicate checking with duplicates found but no artist info."""
        processor = MusicLibraryProcessor(default_processor_config)

        tracks = [
            create_track(track_id="1", title="Same Song", artists="", key=None),
            create_track(track_id="2", title="Same Song", artists=None, key=None),
        ]

        processor.check_for_duplicates(tracks)
        captured = capsys.readouterr()
        assert "WARNING: 2 duplicate tracks found: 'same song' (no artist)" in captured.out

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
        not_in_title, in_title = processor._split_artists_by_title(
            "Test Song by Artist1", "Artist1, Artist2"
        )
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
        assert track.enhanced_title == "Song Title - Test Artist [Cm]"

    def test_process_track_output_both_changes(self, default_processor_config, capsys):
        """Test output when both title and artists change."""
        config = default_processor_config
        config["replace_in_artist"] = [{"from": "Old Artist", "to": "New Artist"}]
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
        assert "[Am]" in sample_track.enhanced_title

        # Test with key disabled
        config_disabled = {
            "add_key_to_title": False,
            "add_artist_to_title": True,
            "remove_artists_in_title": True,
        }
        processor_disabled = MusicLibraryProcessor(config_disabled)
        sample_track_disabled = create_track()
        processor_disabled.process_track(sample_track_disabled)
        assert "[Am]" not in (sample_track_disabled.enhanced_title or "")

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
        assert "- Test Artist" in sample_track_enabled.enhanced_title

        # Test with artists disabled
        config_disabled = {
            "add_key_to_title": True,
            "add_artist_to_title": False,
            "remove_artists_in_title": True,
        }
        processor_disabled = MusicLibraryProcessor(config_disabled)
        sample_track_disabled = create_track()
        processor_disabled.process_track(sample_track_disabled)
        assert "- Test Artist" not in (sample_track_disabled.enhanced_title or "")

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
        assert track.enhanced_title == "Party (Subsonic mix) - Dazza [Am]"

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
        # Should keep all artists in both field and enhanced title
        assert track_disabled.artists == "Dazza, Subsonic"
        assert track_disabled.enhanced_title == "Party (Subsonic mix) - Dazza, Subsonic [Am]"

    def test_print_artist_only_changes(self, capsys):
        """Test print output when only artists change (not title)."""
        config = {
            "add_key_to_title": False,  # Enable to trigger processing
            "add_artist_to_title": False,  # Don't add artist to title
            "replace_in_artist": [{"from": "Old Artist", "to": "New Artist"}],
        }
        processor = MusicLibraryProcessor(config)

        # Create track where only artist changes due to replacement
        track = create_track(title="Test Song", artists="Old Artist", key=None)  # No key

        processor.process_track(track)

        captured = capsys.readouterr()
        # Should print artist-only change (no title change since no key and
        # add_artist_to_title=False)
        assert "Updating 'Test Song' artists 'Old Artist' to 'New Artist'" in captured.out

    def test_remove_artist_suffixes_no_removal(self):
        """Test _remove_artist_suffixes when no removal is needed."""
        processor = MusicLibraryProcessor({})

        # Test case where artist doesn't match the suffix
        result = processor._remove_artist_suffixes("Song Title - Different Artist", "Main Artist")
        assert result == "Song Title - Different Artist"  # Should return unchanged

        # Test case with no " - " in title
        result = processor._remove_artist_suffixes("Song Title", "Artist")
        assert result == "Song Title"  # Should return unchanged

    def test_set_original_titles_corruption_cleanup(self):
        """Test set_original_titles properly cleans up various corruption patterns."""
        processor = MusicLibraryProcessor({})

        # Create a mock collection with various corrupted titles
        mock_collection = Mock()
        
        # Test cases for different corruption patterns
        test_tracks = [
            # Pattern 1: Simple duplicated artist with key
            create_track(
                track_id="1",
                title="All Funked Up - Mother [Abm]",
                artists="Mother"
            ),
            
            # Pattern 2: Multiple artists, one matches suffix
            create_track(
                track_id="2",
                title="Love On My Mind - Freemasons ft. Amanda Wilson [Bbm]",
                artists="Freemasons ft. Amanda Wilson"
            ),
            
            # Pattern 3: Artist with separators (&, comma)
            create_track(
                track_id="3",
                title="Kojak - Bigphones, Groove Guide [Cm]",
                artists="Bigphones, Groove Guide"
            ),
            
            # Pattern 4: No key, just artist suffix
            create_track(
                track_id="4", 
                title="24 Hours - Agent Sumo",
                artists="Agent Sumo"
            ),
            
            # Pattern 5: Partial artist match (should clean)
            create_track(
                track_id="5",
                title="Be There ft. Ayah Marar - T & Sugah [Dm]",
                artists="T & Sugah"  # "Sugah" should match "T & Sugah"
            ),
            
            # Pattern 6: No match, should not clean
            create_track(
                track_id="6",
                title="Song Title - Different Artist [Am]", 
                artists="Main Artist"  # No match, should not clean
            ),
            
            # Pattern 7: Already clean, should remain unchanged
            create_track(
                track_id="7",
                title="Clean Song",
                artists="Artist Name"
            ),
            
            # Pattern 8: Multiple levels of corruption
            create_track(
                track_id="8",
                title="Stars On The Roof (ft. MoMo) - Alcemist - MoMo, Alcemist [Am]",
                artists="MoMo, Alcemist"
            )
        ]
        
        mock_collection.get_all_tracks.return_value = test_tracks
        
        # Call set_original_titles
        processor.set_original_titles(mock_collection)
        
        # Test results
        expected_results = [
            ("All Funked Up", "Mother"),  # Should remove " - Mother [Abm]"
            ("Love On My Mind", "Freemasons ft. Amanda Wilson"),  # Should remove " - Freemasons ft. Amanda Wilson [Bbm]"
            ("Kojak", "Bigphones, Groove Guide"),  # Should remove " - Bigphones, Groove Guide [Cm]"
            ("24 Hours", "Agent Sumo"),  # Should remove " - Agent Sumo"
            ("Be There ft. Ayah Marar", "T & Sugah"),  # Should remove " - T & Sugah [Dm]"
            ("Song Title - Different Artist [Am]", "Main Artist"),  # Should NOT clean (no match)
            ("Clean Song", "Artist Name"),  # Already clean
            ("Stars On The Roof (ft. MoMo)", "MoMo, Alcemist")  # Should remove both suffixes
        ]
        
        for i, (expected_title, expected_artist) in enumerate(expected_results):
            track = test_tracks[i]
            assert track.original_title == expected_title, f"Track {i+1}: Expected '{expected_title}', got '{track.original_title}'"
            assert track.original_artists == expected_artist, f"Track {i+1}: Expected '{expected_artist}', got '{track.original_artists}'"


