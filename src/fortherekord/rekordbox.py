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

    def get_all_tracks(self) -> List[Track]:
        """
        Get all tracks from the collection.
        
        Returns:
            List of all tracks in the database
        """
        db = self._get_database()
        tracks = []
        
        for content in db.get_content():
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
    
    def get_tracks_from_playlists(self, ignore_playlists: List[str] = None) -> List[Track]:
        """
        Get all tracks from playlists, excluding ignored playlists.
        
        Args:
            ignore_playlists: List of playlist names to ignore
            
        Returns:
            List of tracks from all non-ignored playlists
        """
        if ignore_playlists is None:
            ignore_playlists = []
            
        db = self._get_database()
        track_ids = set()  # Use set to avoid duplicates
        tracks = []
        
        for playlist in db.get_playlist():
            playlist_name = playlist.Name
            
            if playlist_name in ignore_playlists:
                print(f"Ignoring playlist: {playlist_name}")
                continue
                
            print(f"Processing playlist '{playlist_name}' with {len(playlist.Songs)} tracks")
            
            for song in playlist.Songs:
                content = song.Content
                track_id = str(content.ID)
                
                if track_id not in track_ids:
                    track_ids.add(track_id)
                    track = Track(
                        id=track_id,
                        title=content.Title or "Unknown Title",
                        artist=content.Artist.Name if content.Artist else "Unknown Artist",
                        duration_ms=int(content.Length * 1000) if content.Length else None,
                        key=content.Key,
                        bpm=content.BPM,
                    )
                    tracks.append(track)
        
        print(f"Found {len(tracks)} tracks to process")
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
        
        try:
            # Find the content record using pyrekordbox query syntax
            content = db.get_content(ID=track_id)
            
            if content is None:
                print(f"WARNING: Track not found for update: {track_id}")
                return False
            
            # Update the fields directly
            content.Title = title
            if content.Artist:
                content.Artist.Name = artist
                
            return True
            
        except Exception as e:
            print(f"ERROR: Failed to update track {track_id}: {e}")
            return False
    
    def save_changes(self) -> bool:
        """
        Save all changes to the database.
        
        In test mode (when FORTHEREKORD_TEST_MODE is set), changes are dumped
        to a file instead of committing to the database.
        
        Returns:
            True if save was successful
        """
        import os
        import json
        from datetime import datetime
        
        if self._db is None:
            return True
            
        # Check if we're in test mode
        test_mode = os.getenv("FORTHEREKORD_TEST_MODE", "").lower() in ("1", "true", "yes")
        
        if test_mode:
            # In test mode, dump changes to a file instead of committing
            try:
                dump_file = os.getenv("FORTHEREKORD_TEST_DUMP_FILE", "test_changes_dump.json")
                
                # Collect pending changes (this would need to be implemented based on pyrekordbox's dirty tracking)
                changes = {
                    "timestamp": datetime.now().isoformat(),
                    "mode": "test_dump",
                    "message": "Changes would have been committed to database",
                    "note": "Database commit prevented in test mode"
                }
                
                # Write to dump file
                with open(dump_file, "w") as f:
                    json.dump(changes, f, indent=2)
                
                print(f"Test mode: Changes dumped to {dump_file} (database not modified)")
                return True
                
            except Exception as e:
                print(f"ERROR: Failed to dump test changes: {e}")
                return False
        else:
            # Normal mode: commit to database
            try:
                # Commit changes using pyrekordbox's commit method
                self._db.commit()
                print("Changes saved to database")
                return True
            except Exception as e:
                print(f"ERROR: Failed to save changes: {e}")
                return False
