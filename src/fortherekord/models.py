"""
Data models for ForTheRekord application.

Defines the core data structures used throughout the application for tracks,
playlists, and configuration management.
"""

from dataclasses import dataclass
from typing import List, Optional, Protocol


@dataclass
class Track:
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
    bpm: Optional[float] = None


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
