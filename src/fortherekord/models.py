"""
Data models for ForTheRekord application.

Defines the core data structures used throughout the application for tracks,
playlists, and configuration management.
"""

from dataclasses import dataclass
from typing import List, Optional, Protocol


@dataclass
class Track:  # pylint: disable=too-many-instance-attributes
    """
    Represents a music track with metadata.

    Used for both Rekordbox and Spotify tracks with platform-agnostic
    field structure for easier matching and processing.
    """

    id: str
    title: str
    artist: str
    duration_ms: Optional[int] = None
    key: Optional[str] = None
    original_title: Optional[str] = None
    original_artist: Optional[str] = None


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
    children: Optional[List["Playlist"]] = None

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

    def get_playlists(self) -> List[Playlist]:
        """Retrieve all playlists from the music platform."""
        raise NotImplementedError

    def get_playlist_tracks(self, playlist_id: str) -> List[Track]:
        """Get all tracks from a specific playlist."""
        raise NotImplementedError

    def create_playlist(self, name: str, tracks: List[Track]) -> str:
        """Create a new playlist and return its ID."""
        raise NotImplementedError

    def delete_playlist(self, playlist_id: str) -> None:
        """Delete an existing playlist."""
        raise NotImplementedError

    def follow_artist(self, artist_name: str) -> bool:
        """Follow an artist, return True if successful."""
        raise NotImplementedError

    def get_followed_artists(self) -> List[str]:
        """Get list of currently followed artists."""
        raise NotImplementedError


@dataclass
class Collection:
    """
    Represents a music collection with playlists and tracks.

    Encapsulates all data loaded from a music library (like Rekordbox)
    to avoid multiple database calls.
    """

    playlists: List[Playlist]

    def get_all_tracks(self) -> List[Track]:
        """Get all unique tracks from all playlists."""
        all_tracks = []
        track_ids = set()

        for playlist in self.playlists:
            for track in playlist.tracks:
                if track.id not in track_ids:
                    track_ids.add(track.id)
                    all_tracks.append(track)

        return all_tracks
