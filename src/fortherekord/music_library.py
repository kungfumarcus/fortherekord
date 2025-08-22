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

    def __init__(self) -> None:
        """Initialize the music library base."""
        super().__init__()

    @abstractmethod
    def _get_raw_playlists(self, ignore_playlists: Optional[List[str]] = None) -> List[Playlist]:
        """
        Get raw playlists from the music library platform.

        Concrete implementations should override this to provide platform-specific
        playlist retrieval. Filtering logic is handled by the base class.

        Args:
            ignore_playlists: List of playlist names to exclude from results

        Returns:
            List of playlists with filtering applied
        """
        raise NotImplementedError("Subclasses must implement _get_raw_playlists")

    def get_collection(self, config: Optional[Dict[str, Any]] = None) -> Collection:
        """
        Get the complete collection including all playlists and tracks.

        This method efficiently loads all data in one pass, applying configuration
        internally. The Collection provides access to all tracks via get_all_tracks().

        Args:
            config: Configuration dictionary (implementations extract what they need)

        Returns:
            Collection containing all playlists (filtered) and providing track access
        """
        # Extract ignore_playlists from config, let subclass handle other config
        ignore_playlists = None
        if config:
            ignore_playlists = config.get("ignore_playlists")

        playlists = self._get_raw_playlists(ignore_playlists)
        return Collection(playlists=playlists)

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

    def filter_playlists_by_name(
        self, playlists: List[Playlist], ignore_playlists: Optional[List[str]] = None
    ) -> List[Playlist]:
        """
        Filter playlists by excluding specified names.

        Args:
            playlists: List of playlists to filter
            ignore_playlists: List of playlist names to exclude

        Returns:
            Filtered list of playlists
        """
        if ignore_playlists is None:
            ignore_playlists = []

        return [p for p in playlists if p.name not in ignore_playlists]

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
