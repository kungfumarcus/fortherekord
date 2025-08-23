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
from typing import List, Any

from pyrekordbox import Rekordbox6Database
from pyrekordbox.db6.database import NoCachedKey

from .models import Track, Playlist, Collection
from .music_library import MusicLibrary


class RekordboxLibrary(MusicLibrary):
    """
    Rekordbox database adapter implementing IMusicLibrary interface.

    Provides read-only access to Rekordbox playlists and tracks using
    a configured database path.
    """

    def __init__(self, config: dict):
        """Initialize adapter with configuration."""
        super().__init__(config)

        # Extract rekordbox-specific config
        rekordbox_config = config.get("rekordbox", {})
        library_path = rekordbox_config.get("library_path")
        if not library_path:
            raise ValueError("rekordbox.library_path not configured")

        self.db_path = Path(library_path)
        self.ignore_playlists = rekordbox_config.get("ignore_playlists", [])
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
            key=(
                content.Key.ScaleName
                if hasattr(content.Key, "ScaleName") and content.Key
                else (content.Key if isinstance(content.Key, str) else None)
            ),
            original_title=current_title,  # Will be set properly by processor
            original_artist=current_artist,  # Will be set properly by processor
        )

    def get_collection(self) -> Collection:
        """
        Get the complete collection including all playlists and tracks.

        Returns only playlists with no parent. Child playlists are accessible
        through the children property of their parent playlists.

        Returns:
            Collection with top-level playlists with full hierarchy built,
            ordered by Rekordbox sequence
        """
        db = self._get_database()
        all_playlists = []
        playlist_map = {}  # For building parent-child relationships
        seq_map = {}  # For storing Rekordbox sequence order
        track_map: dict[str, Track] = {}  # For storing all unique tracks

        # First pass: Create all playlist objects and store sequence numbers
        for rb_playlist in db.get_playlist():
            # Get track list for this playlist
            tracks = []

            # Use get_playlist_contents which works for both regular and smart playlists
            try:
                playlist_contents = db.get_playlist_contents(rb_playlist).all()
                for content in playlist_contents:
                    track_id = str(content.ID)

                    # Check if track is already in the hash
                    if track_id in track_map:
                        # Reuse existing track object
                        track = track_map[track_id]
                    else:
                        # Create new track and add to hash
                        track = self._create_track_from_content(content)
                        track_map[track_id] = track

                    tracks.append(track)
            except (AttributeError, KeyError, TypeError):
                # If get_playlist_contents fails, fall back to empty list
                # This handles edge cases where the playlist might be corrupted
                pass

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

        # Return only top-level playlists (no parent) - filtering is done in base class
        top_level_playlists = [p for p in all_playlists if p.parent_id is None]
        return Collection(playlists=top_level_playlists, tracks=track_map)

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

    def save_changes(
        self, tracks: list[Track], dry_run: bool = False
    ) -> int:  # pylint: disable=too-many-locals
        """
        Count how many tracks actually have different values and save only if there are changes.

        Args:
            tracks: List of Track objects to check and save
            dry_run: If True, only count changes without making them

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
                if dry_run:
                    # In dry-run mode, just count the change without making it
                    modified_count += 1
                else:
                    # Update the track in the database
                    success = self.update_track_metadata(track.id, current_title, current_artist)
                    if success:
                        modified_count += 1
                    else:
                        print(f"WARNING: Failed to update track {track.id}: {current_title}")

        # Check if we're in test mode
        test_mode = os.getenv("FORTHEREKORD_TEST_MODE", "").lower() in ("1", "true", "yes")

        if dry_run:
            # In dry-run mode, don't commit anything
            return modified_count

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
