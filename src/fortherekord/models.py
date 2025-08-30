"""
Data models for ForTheRekord application.

Defines the core data structures used throughout the application for tracks,
playlists, and configuration management.
"""

from dataclasses import dataclass
from typing import List, Optional, Protocol, Dict


@dataclass
class Track:  # pylint: disable=too-many-instance-attributes
    """
    Represents a music track with metadata.

    Used for both Rekordbox and Spotify tracks with platform-agnostic
    field structure for easier matching and processing.
    """

    id: str
    title: str
    artists: str
    original_title: str
    original_artists: str
    key: Optional[str] = None
    enhanced_title: Optional[str] = None


@dataclass
class Playlist:
    """
    Represents a playlist containing tracks.

    Supports hierarchical structure with parent/child relationships
    for nested playlist folders.
    """

    id: str
    name: str
    tracks: List[Track]
    parent_id: Optional[str] = None
    parent: Optional["Playlist"] = None
    children: Optional[List["Playlist"]] = None

    def full_name(self) -> str:
        """
        Get the full name of the playlist, including parent folders.

        Returns:
            str: Full hierarchical name of the playlist
        """
        if self.parent:
            return f"{self.parent.full_name()} / {self.name}"
        return self.name

    def display_tree(self, indent: int = 0) -> None:
        """
        Display this playlist and its children in a tree format.

        Args:
            indent: Number of indentation levels (0 for root level)
        """
        indent_str = "  " * indent + "- "
        track_count = len(self.tracks)

        if track_count > 0:
            print(f"{indent_str}{self.name} ({track_count} tracks)")
        else:
            print(f"{indent_str}{self.name}")

        # Recursively display children in their original order
        if self.children:
            for child in self.children:
                child.display_tree(indent + 1)


class IMusicLibrary(Protocol):
    """
    Generic interface for music platform integration.

    Defines the contract that both Rekordbox and Spotify components
    must implement to enable generic playlist synchronization.
    """

    def get_collection(self) -> "Collection":
        """Get the complete collection including all playlists and tracks (raw, unfiltered)."""
        raise NotImplementedError

    def get_filtered_collection(self) -> "Collection":
        """Get the complete collection with configuration-based filtering applied."""
        raise NotImplementedError

    def create_playlist(self, name: str, tracks: List[Track]) -> str:
        """Create a new playlist and return its ID."""
        raise NotImplementedError

    def delete_playlist(self, playlist_id: str) -> None:
        """Delete an existing playlist."""
        raise NotImplementedError


@dataclass
class Collection:
    """
    Represents a music collection with playlists and tracks.

    Encapsulates all data loaded from a music library (like Rekordbox)
    to avoid multiple database calls. Provides efficient track lookup via hash map.
    """

    playlists: List[Playlist]
    tracks: Dict[str, Track]

    @classmethod
    def from_playlists(cls, playlists: List[Playlist]) -> "Collection":
        """Create a Collection from playlists, automatically calculating tracks dictionary."""
        tracks = {}
        for playlist in playlists:
            for track in playlist.tracks:
                tracks[track.id] = track
        return cls(playlists=playlists, tracks=tracks)

    def get_all_tracks(self) -> List[Track]:
        """Get all unique tracks from all playlists."""
        return list(self.tracks.values())

    def get_track(self, track_id: str) -> Optional[Track]:
        """Get a specific track by ID."""
        return self.tracks.get(track_id)

    def get_changed_tracks(self) -> List[Track]:
        """
        Get all tracks that have changes (different from their original values).

        Returns:
            List of tracks where title or artists differs from original values
        """
        changed_tracks = []
        for track in self.tracks.values():
            # Use enhanced_title if available, otherwise use regular title (same logic as save)
            title = track.enhanced_title or track.title
            if title != track.original_title or track.artists != track.original_artists:
                changed_tracks.append(track)
        return changed_tracks
