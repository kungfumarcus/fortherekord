"""
Rekordbox library integration.

Handles loading and processing of Rekordbox database files usi        return Track(
            id=str(content.ID),
            title=current_title,
            artist=current_artist,
            duration_ms=int(content.Length * 1000) if content.Length else None,
            key=content.Key,
            original_title=current_title,  # Will be set properly by processor
            original_artist=current_artist,  # Will be set properly by processor
        )dbox.
Implements IMusicLibrary interface for playlist synchronization.
"""

import json
import logging
import io
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Any

from pyrekordbox import Rekordbox6Database
from pyrekordbox.db6.database import NoCachedKey

from .models import Track, Playlist
from .music_library import MusicLibrary


class RekordboxLibrary(MusicLibrary):
    """
    Rekordbox database adapter implementing IMusicLibrary interface.

    Provides read-only access to Rekordbox playlists and tracks using
    a configured database path.
    """

    def __init__(self, db_path: str):
        """Initialize adapter with specified database path."""
        super().__init__()
        self.db_path = Path(db_path)
        self._db = None
        self.is_rekordbox_running = False

    def _get_database(self) -> Rekordbox6Database:
        """Get database connection, opening if necessary."""
        if self._db is None:
            if not self.db_path.exists():
                raise FileNotFoundError(f"Rekordbox database not found: {self.db_path}")

            # Capture logging output from pyrekordbox to detect if Rekordbox is running
            log_capture = io.StringIO()
            handler = logging.StreamHandler(log_capture)
            logger = logging.getLogger("pyrekordbox")
            logger.addHandler(handler)
            logger.setLevel(logging.WARNING)

            try:
                self._db = Rekordbox6Database(str(self.db_path))

                # Check the log output for the warning message
                log_output = log_capture.getvalue()
                self.is_rekordbox_running = "Rekordbox is running" in log_output

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
            finally:
                # Clean up the logging handler
                logger.removeHandler(handler)

        return self._db

    def _create_track_from_content(self, content: Any) -> Track:
        """
        Helper method to create a Track object from Rekordbox content.

        Args:
            content: Rekordbox content object

        Returns:
            Track object
        """
        current_title = content.Title or "Unknown Title"
        current_artist = content.Artist.Name if content.Artist else "Unknown Artist"

        return Track(
            id=str(content.ID),
            title=current_title,
            artist=current_artist,
            duration_ms=int(content.Length * 1000) if content.Length else None,
            key=content.Key,
            original_title=current_title,  # Will be set properly by processor
            original_artist=current_artist,  # Will be set properly by processor
        )

    def _get_raw_playlists(self, ignore_playlists: Optional[List[str]] = None) -> List[Playlist]:
        """
        Retrieve top-level playlists from Rekordbox database.

        Returns only playlists with no parent. Child playlists are accessible
        through the children property of their parent playlists.

        Args:
            ignore_playlists: List of playlist names to exclude from results

        Returns:
            List of top-level playlists with full hierarchy built, ordered by Rekordbox sequence
        """
        if ignore_playlists is None:
            ignore_playlists = []

        db = self._get_database()
        all_playlists = []
        playlist_map = {}  # For building parent-child relationships
        seq_map = {}  # For storing Rekordbox sequence order

        # First pass: Create all playlist objects and store sequence numbers
        for rb_playlist in db.get_playlist():
            # Get tracks for this playlist
            tracks = []
            for song in rb_playlist.Songs:
                track = self._create_track_from_content(song.Content)
                tracks.append(track)

            # Create playlist object with parent_id
            playlist = Playlist(
                id=str(rb_playlist.ID),
                name=rb_playlist.Name or "Unnamed Playlist",
                tracks=tracks,
                parent_id=str(rb_playlist.Parent.ID) if rb_playlist.Parent else None,
            )
            all_playlists.append(playlist)
            playlist_map[playlist.id] = playlist
            seq_map[playlist.id] = rb_playlist.Seq

        # Sort all playlists by their Rekordbox sequence order
        all_playlists.sort(key=lambda p: seq_map[p.id])

        # Second pass: Build parent-child relationships with sorted children
        for playlist in all_playlists:
            if playlist.parent_id and playlist.parent_id in playlist_map:
                parent = playlist_map[playlist.parent_id]
                if parent.children is None:
                    parent.children = []
                parent.children.append(playlist)

        # Sort children for each parent by sequence order
        for playlist in all_playlists:
            if playlist.children:
                playlist.children.sort(key=lambda p: seq_map[p.id])

        # Return only top-level playlists (no parent) that are not ignored
        return [p for p in all_playlists if p.parent_id is None and p.name not in ignore_playlists]

    def get_playlists(self, ignore_playlists: Optional[List[str]] = None) -> List[Playlist]:
        """
        Get top-level playlists (for backward compatibility).

        Args:
            ignore_playlists: List of playlist names to exclude from results

        Returns:
            List of top-level playlists with filtering applied
        """
        return self._get_raw_playlists(ignore_playlists)

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
                    track = self._create_track_from_content(song.Content)
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

    def get_all_tracks(self) -> List[Track]:
        """
        Get all tracks from the collection.

        Returns:
            List of all tracks in the database
        """
        db = self._get_database()
        tracks = []

        for content in db.get_content():
            track = self._create_track_from_content(content)
            tracks.append(track)

        return tracks

    def update_track_metadata(self, track_id: str, title: str, artist: str) -> bool:
        """
        Update track metadata in the database.

        Args:
            track_id: ID of the track to update
            title: New title
            artist: New artist

        Returns:
            True if update was successful
        """
        db = self._get_database()

        # Find the content record using pyrekordbox query syntax
        content = db.get_content(ID=track_id)

        if content is None:
            print(f"WARNING: Track not found for update: {track_id}")
            return False

        # Update the fields
        content.Title = title
        if content.Artist:
            content.Artist.Name = artist

        return True

    def save_changes(self, tracks: list[Track]) -> int:  # pylint: disable=too-many-locals
        """
        Count how many tracks actually have different values and save only if there are changes.

        Args:
            tracks: List of Track objects to check and save

        Returns:
            Number of tracks that actually had different values
        """
        # Count tracks that actually have different values
        modified_count = 0

        # Compare current values with original values for provided tracks
        for track in tracks:
            # Use the original values stored on the Track object
            current_title = track.title or ""
            current_artist = track.artist or ""

            original_title = track.original_title or ""
            original_artist = track.original_artist or ""

            # Check if either title or artist has changed
            if current_title != original_title or current_artist != original_artist:
                # Update the track in the database
                success = self.update_track_metadata(track.id, current_title, current_artist)
                if success:
                    modified_count += 1
                else:
                    print(f"WARNING: Failed to update track {track.id}: {current_title}")

        # Check if we're in test mode
        test_mode = os.getenv("FORTHEREKORD_TEST_MODE", "").lower() in ("1", "true", "yes")

        if test_mode:
            # In test mode, dump changes to a file instead of committing
            dump_file = os.getenv("FORTHEREKORD_TEST_DUMP_FILE", "test_changes_dump.json")

            changes = {
                "timestamp": datetime.now().isoformat(),
                "mode": "test_dump",
                "modified_count": modified_count,
                "message": "Changes would have been committed to database",
                "note": "Database commit prevented in test mode",
            }

            # Write to dump file
            with open(dump_file, "w", encoding="utf-8") as f:
                json.dump(changes, f, indent=2)

            print(f"Test mode: Changes dumped to {dump_file} (database not modified)")
            return modified_count

        # Normal mode: commit to database only if there are changes
        if modified_count > 0 and self._db:
            self._db.commit()
            print("Changes saved to database")
        return modified_count
