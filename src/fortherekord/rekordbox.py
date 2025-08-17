"""
Rekordbox library integration.

Handles loading and processing of Rekordbox database files using pyrekordbox.
Implements IMusicLibrary interface for playlist synchronization.
"""

import subprocess
import sys
from pathlib import Path
from typing import List

from pyrekordbox import Rekordbox6Database
from pyrekordbox.db6.database import NoCachedKey

from .models import Track, Playlist, IMusicLibrary


class RekordboxLibrary(IMusicLibrary):
    """
    Rekordbox database adapter implementing IMusicLibrary interface.

    Provides read-only access to Rekordbox playlists and tracks using
    a configured database path.
    """

    def __init__(self, db_path: str):
        """Initialize adapter with specified database path."""
        self.db_path = Path(db_path)
        self._db = None

    def _get_database(self) -> Rekordbox6Database:
        """Get database connection, opening if necessary."""
        if self._db is None:
            if not self.db_path.exists():
                raise FileNotFoundError(f"Rekordbox database not found: {self.db_path}")

            try:
                self._db = Rekordbox6Database(str(self.db_path))
            except NoCachedKey:
                # Try to download the key automatically
                print("Database key not found. Attempting to download...")
                try:
                    subprocess.run(
                        [sys.executable, "-m", "pyrekordbox", "download-key"],
                        capture_output=True,
                        text=True,
                        check=True,
                    )
                    print("Key downloaded successfully!")
                    # Try opening the database again
                    self._db = Rekordbox6Database(str(self.db_path))
                except subprocess.CalledProcessError as e:
                    raise RuntimeError(
                        f"Failed to download database key: {e.stderr or e.stdout}"
                    ) from e
                except NoCachedKey as e:
                    raise RuntimeError(
                        "Database key could not be obtained. Please ensure Rekordbox is "
                        "installed and has been run at least once, or manually download "
                        "the key using: python -m pyrekordbox download-key"
                    ) from e
        return self._db

    def get_playlists(self) -> List[Playlist]:
        """
        Retrieve all playlists from Rekordbox database.

        Returns:
            List of playlists with track information
        """
        db = self._get_database()
        playlists = []

        # Get all playlists from database
        for rb_playlist in db.get_playlist():
            # Get tracks for this playlist
            tracks = []
            for song in rb_playlist.Songs:
                content = song.Content
                track = Track(
                    id=str(content.ID),
                    title=content.Title or "Unknown Title",
                    artist=content.Artist.Name if content.Artist else "Unknown Artist",
                    duration_ms=int(content.Length * 1000) if content.Length else None,
                    key=content.Key,
                    bpm=content.BPM,
                )
                tracks.append(track)

            # Create playlist object
            playlist = Playlist(
                id=str(rb_playlist.ID),
                name=rb_playlist.Name or "Unnamed Playlist",
                tracks=tracks,
            )
            playlists.append(playlist)

        return playlists

    def get_playlist_tracks(self, playlist_id: str) -> List[Track]:
        """
        Get all tracks from a specific playlist.

        Args:
            playlist_id: ID of the playlist to get tracks for

        Returns:
            List of tracks in the playlist
        """
        db = self._get_database()

        # Find the specific playlist
        for rb_playlist in db.get_playlist():
            if str(rb_playlist.ID) == playlist_id:
                tracks = []
                for song in rb_playlist.Songs:
                    content = song.Content
                    track = Track(
                        id=str(content.ID),
                        title=content.Title or "Unknown Title",
                        artist=content.Artist.Name if content.Artist else "Unknown Artist",
                        duration_ms=int(content.Length * 1000) if content.Length else None,
                        key=content.Key,
                        bpm=content.BPM,
                    )
                    tracks.append(track)
                return tracks

        raise ValueError(f"Playlist not found: {playlist_id}")

    def create_playlist(self, name: str, tracks: List[Track]) -> str:
        """Create playlist - not supported (read-only)."""
        raise NotImplementedError("Playlist creation not supported - Rekordbox is read-only")

    def delete_playlist(self, playlist_id: str) -> None:
        """Delete playlist - not supported (read-only)."""
        raise NotImplementedError("Playlist deletion not supported - Rekordbox is read-only")

    def follow_artist(self, artist_name: str) -> bool:
        """Follow artist - not supported (source library only)."""
        raise NotImplementedError("Artist following not supported - Rekordbox is source library")

    def get_followed_artists(self) -> List[str]:
        """Get followed artists - not supported (source library only)."""
        raise NotImplementedError("Followed artists not supported - Rekordbox is source library")
