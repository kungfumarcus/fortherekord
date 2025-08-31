"""
Track mapping cache for Rekordbox to Spotify track matching.

Implements caching layer to avoid repeated API calls for the same tracks.
"""

import json
import time
from pathlib import Path
from typing import Dict, Optional
from dataclasses import dataclass

from .config import get_config_path


@dataclass
class MappingEntry:
    """Represents a cached mapping entry for a track."""

    target_track_id: Optional[str]  # Spotify track ID or None if unmapped
    algorithm_version: str  # Algorithm version used for matching
    confidence_score: float  # Confidence score of the match
    timestamp: float  # When mapping was created


class MappingCache:
    """Manages the track mapping cache."""

    ALGORITHM_VERSION = "basic"

    def __init__(self) -> None:
        """Initialize the mapping cache."""
        self.cache_file = self._get_cache_file_path()
        self.mappings: Dict[str, MappingEntry] = {}
        self.load_cache()

    def _get_cache_file_path(self) -> Path:
        """Get the path to the mapping cache file."""
        config_folder = get_config_path().parent
        return config_folder / "RekordBoxSpotifyMapping.json"

    def load_cache(self) -> None:
        """Load existing mappings from cache file."""
        if not self.cache_file.exists():
            return

        try:
            with open(self.cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Convert loaded data back to MappingEntry objects
            for track_id, entry_data in data.items():
                if entry_data is None:
                    # Failed mapping stored as null
                    self.mappings[track_id] = MappingEntry(
                        target_track_id=None,
                        algorithm_version=self.ALGORITHM_VERSION,
                        confidence_score=0.0,
                        timestamp=time.time(),
                    )
                elif isinstance(entry_data, dict):
                    # New format: {"spid": "...", "algo": "v1" or "manual"}
                    spotify_id = entry_data["spid"]
                    algo = entry_data["algo"]

                    # Store with the algorithm version (including "manual")
                    self.mappings[track_id] = MappingEntry(
                        target_track_id=spotify_id,
                        algorithm_version=algo,  # Keep original algo (basic or manual)
                        confidence_score=1.0,
                        timestamp=time.time(),
                    )

        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
            # If cache file is corrupted, start fresh
            print(f"Warning: Corrupted mapping cache file, starting fresh: {e}")
            self.mappings = {}

    def save_cache(self) -> None:
        """Save current mappings to cache file using compact format."""
        try:
            # Convert MappingEntry objects to compact format
            data: Dict[str, Optional[Dict[str, str]]] = {}
            for track_id, entry in self.mappings.items():
                if entry.target_track_id is None:
                    # Failed mapping: just store track_id: null
                    data[track_id] = None
                else:
                    # Successful mapping
                    data[track_id] = {
                        "spid": entry.target_track_id,
                        "algo": entry.algorithm_version,
                    }

            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, separators=(",", ":"))  # Compact JSON with no spaces

        except (OSError, TypeError) as e:
            print(f"Warning: Failed to save mapping cache: {e}")

    def get_mapping(self, rekordbox_track_id: str) -> Optional[MappingEntry]:
        """
        Get cached mapping for a Rekordbox track.

        Args:
            rekordbox_track_id: Rekordbox track ID

        Returns:
            MappingEntry if found, None otherwise
        """
        return self.mappings.get(rekordbox_track_id)

    def set_mapping(
        self,
        rekordbox_track_id: str,
        spotify_track_id: Optional[str],
        confidence_score: float = 1.0,
        algorithm_version: Optional[str] = None,
    ) -> None:
        """
        Cache a track mapping.

        Args:
            rekordbox_track_id: Rekordbox track ID
            spotify_track_id: Spotify track ID or None if no match found
            confidence_score: Confidence score of the match
            algorithm_version: Algorithm version used (defaults to ALGORITHM_VERSION,
                              use "manual" for interactive selection)
        """
        if algorithm_version is None:
            algorithm_version = self.ALGORITHM_VERSION

        entry = MappingEntry(
            target_track_id=spotify_track_id,
            algorithm_version=algorithm_version,
            confidence_score=confidence_score,
            timestamp=time.time(),
        )

        self.mappings[rekordbox_track_id] = entry

    def should_remap(self, rekordbox_track_id: str, force_remap: bool = False) -> bool:
        """
        Check if a track should be remapped.

        Args:
            rekordbox_track_id: Rekordbox track ID
            force_remap: If True, always remap regardless of cache

        Returns:
            True if track should be remapped, False if cached mapping should be used
        """
        if force_remap:
            return True

        cached_entry = self.get_mapping(rekordbox_track_id)
        if cached_entry is None:
            return True  # No cached mapping exists

        # Could add logic here to check if mapping is too old or uses outdated algorithm
        return False

    def clear_all_mappings(self) -> int:
        """
        Clear all cached mappings.

        Returns:
            Number of mappings that were cleared
        """
        cleared_count = len(self.mappings)
        self.mappings.clear()
        self.save_cache()
        return cleared_count

    def clear_mappings_by_algorithm(self, algorithm_version: str) -> int:
        """
        Clear cached mappings for a specific algorithm version.

        Args:
            algorithm_version: Algorithm version to clear (e.g., "basic", "manual")

        Returns:
            Number of mappings that were cleared
        """
        original_count = len(self.mappings)

        # Filter out mappings with the specified algorithm version
        self.mappings = {
            track_id: entry
            for track_id, entry in self.mappings.items()
            if entry.algorithm_version != algorithm_version
        }

        cleared_count = original_count - len(self.mappings)

        if cleared_count > 0:
            self.save_cache()

        return cleared_count
