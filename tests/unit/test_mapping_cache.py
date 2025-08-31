"""
Unit tests for mapping_cache module.
"""

import json
from pathlib import Path
from unittest.mock import patch, mock_open

from fortherekord.mapping_cache import MappingCache, MappingEntry


class TestMappingEntry:
    """Test the MappingEntry dataclass."""

    def test_mapping_entry_creation_and_defaults(self):
        """Test creating MappingEntry with all fields, defaults, and None target."""
        # Test with all fields including manual algorithm
        entry1 = MappingEntry(
            target_track_id="spotify:track:123",
            algorithm_version="manual",
            confidence_score=0.95,
            timestamp=1234567890.0,
        )
        assert entry1.target_track_id == "spotify:track:123"
        assert entry1.algorithm_version == "manual"

        # Test with basic algorithm
        entry2 = MappingEntry(
            target_track_id="spotify:track:456",
            algorithm_version=MappingCache.ALGORITHM_VERSION,
            confidence_score=0.85,
            timestamp=1234567890.0,
        )
        assert entry2.algorithm_version == MappingCache.ALGORITHM_VERSION

        # Test None target (failed match)
        entry3 = MappingEntry(
            target_track_id=None,
            algorithm_version=MappingCache.ALGORITHM_VERSION,
            confidence_score=0.0,
            timestamp=1234567890.0,
        )
        assert entry3.target_track_id is None
        assert entry3.confidence_score == 0.0


class TestMappingCache:
    """Test the MappingCache class."""

    @patch("fortherekord.mapping_cache.get_config_path")
    def test_init_and_cache_file_path(self, mock_get_config_path):
        """Test MappingCache initialization and cache file path generation."""
        mock_get_config_path.return_value = Path("/home/user/.config/fortherekord/config.yaml")

        with patch.object(MappingCache, "load_cache") as mock_load:
            cache = MappingCache()

            # Test initialization
            assert cache.mappings == {}
            mock_load.assert_called_once()

            # Test cache file path
            expected_path = Path("/home/user/.config/fortherekord/RekordBoxSpotifyMapping.json")
            assert cache.cache_file == expected_path

    @patch("fortherekord.mapping_cache.get_config_path")
    @patch("builtins.open", new_callable=mock_open)
    @patch("pathlib.Path.exists")
    @patch("json.load")
    @patch("builtins.print")
    def test_load_cache_scenarios(
        self, mock_print, mock_json_load, mock_exists, mock_file, mock_get_config_path
    ):
        """Test various cache loading scenarios."""
        mock_get_config_path.return_value = Path("/mock/config.yaml")

        # Test 1: File doesn't exist
        mock_exists.return_value = False
        cache1 = MappingCache()
        assert cache1.mappings == {}

        # Test 2: Successful loading - new compact format
        mock_exists.return_value = True
        mock_json_load.return_value = {
            "track1": {"spid": "spotify:track:123", "algo": "v1.0-basic"}
        }
        cache2 = MappingCache()
        assert len(cache2.mappings) == 1
        entry = cache2.mappings["track1"]
        assert entry.target_track_id == "spotify:track:123"
        assert entry.algorithm_version == "v1.0-basic"
        assert entry.confidence_score == 1.0  # Default for new format

        # Test 2b: Failed mapping (None entry)
        mock_json_load.return_value = {"track_failed": None}
        cache2b = MappingCache()
        assert len(cache2b.mappings) == 1
        entry_failed = cache2b.mappings["track_failed"]
        assert entry_failed.target_track_id is None
        assert entry_failed.confidence_score == 0.0

        # Test 2c: Manual override
        mock_json_load.return_value = {
            "track_manual": {"spid": "spotify:track:456", "algo": "manual"}
        }
        cache2c = MappingCache()
        assert len(cache2c.mappings) == 1
        entry_manual = cache2c.mappings["track_manual"]
        assert entry_manual.target_track_id == "spotify:track:456"
        assert entry_manual.algorithm_version == "manual"

        # Test 3: JSON decode error
        mock_json_load.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        cache3 = MappingCache()
        assert cache3.mappings == {}
        assert mock_print.call_count >= 1
        assert "Warning: Corrupted mapping cache file" in str(mock_print.call_args_list)

        # Test 4: Key error (missing fields)
        mock_json_load.side_effect = None
        mock_json_load.return_value = {"track1": {"missing_required_fields": "value"}}
        cache4 = MappingCache()
        assert cache4.mappings == {}

    @patch("fortherekord.mapping_cache.get_config_path")
    @patch("builtins.open", new_callable=mock_open)
    @patch("json.dump")
    @patch("builtins.print")
    def test_save_cache_scenarios(
        self, mock_print, mock_json_dump, mock_file, mock_get_config_path
    ):
        """Test cache saving success and error scenarios."""
        mock_get_config_path.return_value = Path("/mock/config.yaml")

        with patch.object(MappingCache, "load_cache"):
            cache = MappingCache()
            cache.mappings = {
                "track1": MappingEntry(
                    target_track_id="spotify:track:123",
                    algorithm_version=MappingCache.ALGORITHM_VERSION,
                    confidence_score=0.95,
                    timestamp=1234567890.0,
                ),
                "track_failed": MappingEntry(
                    target_track_id=None,  # Failed mapping
                    algorithm_version=MappingCache.ALGORITHM_VERSION,
                    confidence_score=0.0,
                    timestamp=1234567890.0,
                ),
                "track_manual": MappingEntry(
                    target_track_id="spotify:track:456",
                    algorithm_version="manual",  # Manual algorithm
                    confidence_score=1.0,
                    timestamp=1234567890.0,
                ),
            }

            # Test successful save
            cache.save_cache()
            mock_file.assert_called_with(cache.cache_file, "w", encoding="utf-8")
            mock_json_dump.assert_called_once()

            # Check data format conversion - should be compact format
            call_args = mock_json_dump.call_args
            data = call_args[0][0]

            # Regular mapping
            assert "track1" in data
            assert isinstance(data["track1"], dict)
            assert data["track1"]["spid"] == "spotify:track:123"
            assert data["track1"]["algo"] == MappingCache.ALGORITHM_VERSION

            # Failed mapping (should be None)
            assert "track_failed" in data
            assert data["track_failed"] is None

            # Manual override mapping
            assert "track_manual" in data
            assert isinstance(data["track_manual"], dict)
            assert data["track_manual"]["spid"] == "spotify:track:456"
            assert data["track_manual"]["algo"] == "manual"

            # Test OS error
            mock_file.side_effect = OSError("Permission denied")
            cache.save_cache()
            assert mock_print.call_count >= 1
            assert "Warning: Failed to save mapping cache" in str(mock_print.call_args_list)

    @patch("fortherekord.mapping_cache.get_config_path")
    def test_get_mapping(self, mock_get_config_path):
        """Test getting existing and non-existent mappings."""
        mock_get_config_path.return_value = Path("/mock/config.yaml")

        with patch.object(MappingCache, "load_cache"):
            cache = MappingCache()
            entry = MappingEntry(
                target_track_id="spotify:track:123",
                algorithm_version=MappingCache.ALGORITHM_VERSION,
                confidence_score=0.95,
                timestamp=1234567890.0,
            )
            cache.mappings["track1"] = entry

            # Test existing mapping
            result = cache.get_mapping("track1")
            assert result is entry

            # Test non-existent mapping
            result = cache.get_mapping("nonexistent")
            assert result is None

    @patch("fortherekord.mapping_cache.get_config_path")
    @patch("time.time")
    def test_set_mapping_scenarios(self, mock_time, mock_get_config_path):
        """Test setting mappings with various scenarios."""
        mock_get_config_path.return_value = Path("/mock/config.yaml")
        mock_time.return_value = 1234567890.0

        with (
            patch.object(MappingCache, "load_cache"),
            patch.object(MappingCache, "save_cache") as mock_save,
        ):
            cache = MappingCache()

            # Test with defaults
            cache.set_mapping("track1", "spotify:track:123")
            entry1 = cache.mappings["track1"]
            assert entry1.target_track_id == "spotify:track:123"
            assert entry1.algorithm_version == MappingCache.ALGORITHM_VERSION
            assert entry1.confidence_score == 1.0

            # Test with custom values (manual algorithm)
            cache.set_mapping(
                "track2", "spotify:track:456", confidence_score=0.85, algorithm_version="manual"
            )
            entry2 = cache.mappings["track2"]
            assert entry2.confidence_score == 0.85
            assert entry2.algorithm_version == "manual"

            # Test with None target (failed match)
            cache.set_mapping("track3", None, confidence_score=0.0)
            entry3 = cache.mappings["track3"]
            assert entry3.target_track_id is None
            assert entry3.confidence_score == 0.0

            # Verify save_cache was not called
            assert mock_save.call_count == 0

    @patch("fortherekord.mapping_cache.get_config_path")
    def test_should_remap_scenarios(self, mock_get_config_path):
        """Test should_remap logic for various scenarios."""
        mock_get_config_path.return_value = Path("/mock/config.yaml")

        with patch.object(MappingCache, "load_cache"):
            cache = MappingCache()
            entry = MappingEntry(
                target_track_id="spotify:track:123",
                algorithm_version=MappingCache.ALGORITHM_VERSION,
                confidence_score=0.95,
                timestamp=1234567890.0,
            )
            cache.mappings["track1"] = entry

            # Test force_remap=True (always remap)
            assert cache.should_remap("track1", force_remap=True) is True

            # Test no cached entry (should remap)
            assert cache.should_remap("nonexistent") is True

            # Test cached entry exists (should not remap)
            assert cache.should_remap("track1") is False

    @patch("fortherekord.mapping_cache.get_config_path")
    def test_algorithm_version_constant(self, mock_get_config_path):
        """Test that ALGORITHM_VERSION constant is accessible."""
        mock_get_config_path.return_value = Path("/mock/config.yaml")

        with patch.object(MappingCache, "load_cache"):
            cache = MappingCache()
            assert cache.ALGORITHM_VERSION == MappingCache.ALGORITHM_VERSION

    @patch("fortherekord.mapping_cache.get_config_path")
    def test_clear_all_mappings(self, mock_get_config_path):
        """Test clearing all cached mappings."""
        mock_get_config_path.return_value = Path("/mock/config.yaml")

        with patch.object(MappingCache, "load_cache"), patch.object(MappingCache, "save_cache"):
            cache = MappingCache()

            # Add some mappings
            cache.mappings = {
                "track1": MappingEntry("spotify1", "basic", 0.9, 123.0),
                "track2": MappingEntry("spotify2", "manual", 1.0, 124.0),
                "track3": MappingEntry(None, "basic", 0.0, 125.0),
            }

            # Clear all mappings
            cleared_count = cache.clear_all_mappings()

            assert cleared_count == 3
            assert len(cache.mappings) == 0
            cache.save_cache.assert_called_once()

    @patch("fortherekord.mapping_cache.get_config_path")
    def test_clear_mappings_by_algorithm(self, mock_get_config_path):
        """Test clearing mappings for specific algorithm."""
        mock_get_config_path.return_value = Path("/mock/config.yaml")

        with patch.object(MappingCache, "load_cache"), patch.object(MappingCache, "save_cache"):
            cache = MappingCache()

            # Add mappings with different algorithms
            cache.mappings = {
                "track1": MappingEntry("spotify1", "basic", 0.9, 123.0),
                "track2": MappingEntry("spotify2", "manual", 1.0, 124.0),
                "track3": MappingEntry(None, "basic", 0.0, 125.0),
                "track4": MappingEntry("spotify4", "manual", 0.8, 126.0),
            }

            # Clear only basic algorithm mappings
            cleared_count = cache.clear_mappings_by_algorithm("basic")

            assert cleared_count == 2
            assert len(cache.mappings) == 2
            assert "track2" in cache.mappings  # manual should remain
            assert "track4" in cache.mappings  # manual should remain
            assert "track1" not in cache.mappings  # basic should be removed
            assert "track3" not in cache.mappings  # basic should be removed
            cache.save_cache.assert_called_once()

    @patch("fortherekord.mapping_cache.get_config_path")
    def test_clear_mappings_by_algorithm_no_matches(self, mock_get_config_path):
        """Test clearing mappings when no algorithm matches exist."""
        mock_get_config_path.return_value = Path("/mock/config.yaml")

        with patch.object(MappingCache, "load_cache"), patch.object(MappingCache, "save_cache"):
            cache = MappingCache()

            # Add mappings with different algorithms
            cache.mappings = {
                "track1": MappingEntry("spotify1", "basic", 0.9, 123.0),
                "track2": MappingEntry("spotify2", "manual", 1.0, 124.0),
            }

            # Try to clear algorithm that doesn't exist
            cleared_count = cache.clear_mappings_by_algorithm("nonexistent")

            assert cleared_count == 0
            assert len(cache.mappings) == 2  # Nothing should be removed
            cache.save_cache.assert_not_called()  # Should not save if nothing cleared
