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
        # Test with all fields
        entry1 = MappingEntry(
            target_track_id="spotify:track:123",
            algorithm_version=MappingCache.ALGORITHM_VERSION,
            confidence_score=0.95,
            timestamp=1234567890.0,
            manual_override=True,
        )
        assert entry1.target_track_id == "spotify:track:123"
        assert entry1.manual_override is True

        # Test defaults
        entry2 = MappingEntry(
            target_track_id="spotify:track:456",
            algorithm_version=MappingCache.ALGORITHM_VERSION,
            confidence_score=0.85,
            timestamp=1234567890.0,
        )
        assert entry2.manual_override is False  # Default value

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
        assert entry.manual_override is False

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
        assert entry_manual.manual_override is True

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
                    manual_override=False,
                ),
                "track_failed": MappingEntry(
                    target_track_id=None,  # Failed mapping
                    algorithm_version=MappingCache.ALGORITHM_VERSION,
                    confidence_score=0.0,
                    timestamp=1234567890.0,
                    manual_override=False,
                ),
                "track_manual": MappingEntry(
                    target_track_id="spotify:track:456",
                    algorithm_version=MappingCache.ALGORITHM_VERSION,
                    confidence_score=1.0,
                    timestamp=1234567890.0,
                    manual_override=True,  # Manual override
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
            assert entry1.manual_override is False

            # Test with custom values
            cache.set_mapping(
                "track2", "spotify:track:456", confidence_score=0.85, manual_override=True
            )
            entry2 = cache.mappings["track2"]
            assert entry2.confidence_score == 0.85
            assert entry2.manual_override is True

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
