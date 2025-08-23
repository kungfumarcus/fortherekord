"""
Base music library implementation with common functionality.

Provides shared logic for track deduplication and filtering that can be
used by concrete music library implementations.
"""

from typing import List, Optional, Set, Dict, Any
from abc import ABC, abstractmethod

from .models import Track, Playlist, Collection, IMusicLibrary


class MusicLibrary(IMusicLibrary, ABC):
    """
    Base class for music library implementations.

    Provides common functionality like track deduplication and playlist filtering
    while requiring concrete implementations to provide platform-specific data access.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the music library base with configuration."""
        super().__init__()
        self.config = config or {}

    @abstractmethod
    def get_collection(self) -> Collection:
        """
        Get the complete collection including all playlists and tracks (raw, unfiltered).

        Concrete implementations should override this to provide platform-specific
        data loading without any filtering.

        Returns:
            Collection containing all playlists and tracks without filtering
        """
        raise NotImplementedError("Subclasses must implement get_collection")

    def get_filtered_collection(self) -> Collection:
        """
        Get the complete collection with configuration-based filtering applied.

        This method calls get_collection() to get raw data, then applies ignore_playlists
        filtering from the configuration.

        Returns:
            Collection containing filtered playlists and providing track access
        """
        raw_collection = self.get_collection()
        # Get ignore_playlists from appropriate config section
        ignore_list = self.config.get("rekordbox", {}).get("ignore_playlists", [])
        filtered_playlists = [p for p in raw_collection.playlists if p.name not in ignore_list]
        return Collection(playlists=filtered_playlists, tracks=raw_collection.tracks)

    def deduplicate_tracks(self, tracks: List[Track]) -> List[Track]:
        """
        Remove duplicate tracks from a list based on track ID.

        Args:
            tracks: List of tracks that may contain duplicates

        Returns:
            List of unique tracks preserving original order
        """
        seen_ids: Set[str] = set()
        unique_tracks: List[Track] = []

        for track in tracks:
            if track.id not in seen_ids:
                seen_ids.add(track.id)
                unique_tracks.append(track)

        return unique_tracks

    def filter_empty_playlists(self, playlists: List[Playlist]) -> List[Playlist]:
        """
        Filter out playlists that contain no tracks.

        Args:
            playlists: List of playlists to filter

        Returns:
            List of playlists that contain at least one track
        """
        return [p for p in playlists if p.tracks]

    def get_all_tracks_from_playlists(self, playlists: List[Playlist]) -> List[Track]:
        """
        Get all unique tracks from a list of playlists.

        Args:
            playlists: List of playlists to extract tracks from

        Returns:
            Deduplicated list of all tracks from the playlists
        """
        all_tracks: List[Track] = []

        for playlist in playlists:
            all_tracks.extend(playlist.tracks)

        return self.deduplicate_tracks(all_tracks)

    @abstractmethod
    def save_changes(self, tracks: List[Track]) -> int:
        """
        Save changes to tracks in the music library.

        Args:
            tracks: List of tracks with potential changes
            dry_run: If True, only count changes without saving

        Returns:
            Number of tracks that were (or would be) modified
        """
        raise NotImplementedError
