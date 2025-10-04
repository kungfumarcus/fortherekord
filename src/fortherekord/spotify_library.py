"""
Spotify API integration for playlist synchronization.

Provides basic authentication and playlist operations.
"""

import os
import threading
from pathlib import Path
from typing import Any, List, Optional

import spotipy
from spotipy.oauth2 import SpotifyOAuth, CacheFileHandler

# For fuzzy string matching
import Levenshtein

from .models import Track, Playlist
from .config import get_config_path


class SpotifyLibrary:
    """
    Spotify API adapter for playlist management.

    Provides playlist management and track operations using Spotify Web API.
    """

    def __init__(self, client_id: str, client_secret: str, config: Optional[dict] = None) -> None:
        """Initialize Spotify client with OAuth credentials."""
        self.client_id = client_id
        self.client_secret = client_secret
        self.config = config or {}
        self.sp: Optional[spotipy.Spotify] = None
        self.user_id = None

        self._authenticate()

    @staticmethod
    def get_cache_path() -> Path:
        """Get the path to the Spotify cache file in user config folder."""
        config_folder = get_config_path().parent
        return config_folder / ".spotify_cache"

    @staticmethod
    def clear_cache() -> None:
        """Clear Spotify authentication cache to prevent stale token issues."""
        try:
            cache_path = SpotifyLibrary.get_cache_path()
            if cache_path.exists():
                os.remove(cache_path)
        except (OSError, PermissionError):
            # Silently ignore if we can't remove the cache file
            pass

    def _authenticate(self) -> None:
        """Setup Spotify OAuth authentication."""
        scope = (
            "playlist-read-private playlist-modify-public playlist-modify-private user-library-read"
        )

        try:
            # Use the new CacheFileHandler approach to avoid deprecation warning
            # Store cache in user config folder alongside config.yaml
            cache_path = self.get_cache_path()
            cache_handler = CacheFileHandler(cache_path=str(cache_path))

            # WORKAROUND: SpotifyOAuth hangs with invalid credentials (GitHub issue #957)
            # Use requests_timeout on the Spotify client to prevent indefinite hanging
            # See: https://github.com/spotipy-dev/spotipy/issues/957
            # See: https://github.com/spotipy-dev/spotipy/pull/1203/files
            auth_manager = SpotifyOAuth(
                client_id=self.client_id,
                client_secret=self.client_secret,
                redirect_uri="http://127.0.0.1:8888/callback",
                scope=scope,
                cache_handler=cache_handler,
            )

            # Apply timeout to the Spotify client to handle authentication timeouts
            self.sp = spotipy.Spotify(
                auth_manager=auth_manager,
                requests_timeout=2,  # 2 second timeout to prevent hanging with invalid credentials
            )

            # Get user ID with manual timeout since spotipy timeout doesn't work reliably
            # WORKAROUND: Manual timeout wrapper for current_user() call
            # Get timeout from config, default to 2 seconds
            timeout_seconds = self.config.get("spotify", {}).get("timeout", 2)

            result: list[Any] = [None]
            exception: list[Optional[Exception]] = [None]

            def call_current_user() -> None:
                try:
                    if self.sp:
                        result[0] = self.sp.current_user()
                except Exception as e:  # pylint: disable=broad-exception-caught
                    exception[0] = e

            thread = threading.Thread(target=call_current_user)
            thread.daemon = True
            thread.start()
            thread.join(timeout=timeout_seconds)

            if thread.is_alive():
                raise ValueError(
                    f"Spotify authentication timed out after {timeout_seconds} seconds - "
                    "likely invalid credentials"
                )

            # Check for exceptions during authentication
            caught_exception = exception[0]
            if caught_exception is not None:
                raise caught_exception from None

            if result[0]:
                user_info = result[0]
                self.user_id = user_info["id"]
            else:
                raise ValueError("Unknown error during Spotify authentication")

        except ValueError:
            # Re-raise ValueError directly
            raise
        except Exception as e:
            # Handle authentication failures gracefully
            error_str = str(e).lower()
            if any(
                keyword in error_str
                for keyword in [
                    "invalid client",
                    "invalid_client",
                    "client_id",
                    "client_secret",
                    "401",
                    "403",
                    "unauthorized",
                    "forbidden",
                    "timeout",
                    "timed out",
                ]
            ):
                raise ValueError(f"Invalid Spotify credentials: {e}") from e
            # Re-raise other exceptions
            raise

    def search_track(self, title: str, artists: str, interactive: bool = False) -> Optional[str]:
        """
        Search for a track and return the best result's Spotify ID.

        Args:
            title: Track title
            artists: Artist name
            interactive: If True, show user multiple options to choose from

        Returns:
            Spotify track ID if found, None otherwise
        """
        if not self.sp:
            raise RuntimeError("Spotify client not authenticated")

        # Simple free text search - just combine title and artist
        query = f"{title} {artists}"
        results = self.sp.search(q=query, type="track", limit=10 if interactive else 5)

        items = results["tracks"]["items"]
        if not items:
            if interactive:
                print(f"\nNo matches found for: {title} - {artists}")
                return None
            return None

        if not interactive:
            # Use Levenshtein similarity on title and artist, pick best above threshold
            def norm(s):
                return s.lower().strip()

            best_score = 0.0
            best_id = None
            threshold = 0.5  # 50% threshold
            norm_title = norm(title)
            norm_artists = norm(artists)
            for track in items:
                candidate_title = norm(track["name"])
                candidate_artists = norm(", ".join([a["name"] for a in track["artists"]]))
                # Title similarity
                if len(norm_title) > 0 and len(candidate_title) > 0:
                    title_sim = 1.0 - Levenshtein.distance(norm_title, candidate_title) / max(
                        len(norm_title), len(candidate_title)
                    )
                else:
                    title_sim = 0.0
                # Artist similarity
                if len(norm_artists) > 0 and len(candidate_artists) > 0:
                    artist_sim = 1.0 - Levenshtein.distance(norm_artists, candidate_artists) / max(
                        len(norm_artists), len(candidate_artists)
                    )
                else:
                    artist_sim = 0.0
                score = (title_sim + artist_sim) / 2
                if score > best_score:
                    best_score = score
                    best_id = track["id"]
            if best_score >= threshold:
                return str(best_id)
            return None

        # Interactive mode: show top 5 results and let user choose
        return self._interactive_track_selection(title, artists, items[:5])

    def _interactive_track_selection(
        self, source_title: str, source_artists: str, candidates: List[dict]
    ) -> Optional[str]:
        """
        Present track options to user and get their selection.

        Args:
            source_title: Original track title
            source_artists: Original track artists
            candidates: List of Spotify track candidates

        Returns:
            Selected Spotify track ID or None if no match chosen
        """
        print(f"\n🎵 Finding match for: {source_title} - {source_artists}")
        print("=" * 60)

        # Display options (first one is the automatic choice)
        for i, track in enumerate(candidates):
            spotify_title = track["name"]
            spotify_artists = ", ".join([artist["name"] for artist in track["artists"]])

            if i == 0:
                # Bold the automatic choice (first result)
                print(f"👑 {i+1}. {spotify_title} - {spotify_artists}")
            else:
                print(f"   {i+1}. {spotify_title} - {spotify_artists}")

        print("\n   0. No match (skip this track)")
        print(
            f"\n   Press Enter to select the top match (👑), "
            f"choose 1-{len(candidates)} or 0, or 'save' to save cache:"
        )

        while True:
            try:
                choice = input("> ").strip()

                if choice == "":
                    # Enter pressed - select the top match (first result)
                    selected = candidates[0]
                    spotify_title = selected["name"]
                    spotify_artists = ", ".join([artist["name"] for artist in selected["artists"]])
                    print(f"✅ Selected: {spotify_title} - {spotify_artists}")
                    return str(selected["id"])

                if choice.lower() == "save":
                    # Force save the mapping cache
                    return "__SAVE_CACHE__"

                choice_num = int(choice)

                if choice_num == 0:
                    print("❌ No match selected")
                    return None

                if 1 <= choice_num <= len(candidates):
                    selected = candidates[choice_num - 1]
                    spotify_title = selected["name"]
                    spotify_artists = ", ".join([artist["name"] for artist in selected["artists"]])
                    print(f"✅ Selected: {spotify_title} - {spotify_artists}")
                    return str(selected["id"])

                print(f"Invalid choice. Please enter 0-{len(candidates)} or press Enter.")

            except ValueError:
                print(
                    f"Invalid input. Please enter a number 0-{len(candidates)}, "
                    "'save', or press Enter."
                )
            except KeyboardInterrupt:
                print("\n❌ Cancelled")
                raise  # Re-raise to exit the program

    def get_playlists(self, ignore_playlists: Optional[List[str]] = None, prefix: Optional[str] = None) -> List[Playlist]:
        """
        Get user's playlists from Spotify.

        Args:
            ignore_playlists: List of playlist names to exclude
            prefix: Optional prefix to filter playlists by

        Returns:
            List of user's playlists
        """
        if ignore_playlists is None:
            ignore_playlists = []

        if not self.sp:
            raise RuntimeError("Spotify client not authenticated")

        playlists = []
        results = self.sp.current_user_playlists()
        pagination_count = 0
        max_pages = 100  # Safety limit to prevent infinite loops

        while results and pagination_count < max_pages:
            for item in results["items"]:
                if (item["name"] not in ignore_playlists and 
                    item["owner"]["id"] == self.user_id and
                    (prefix is None or item["name"].startswith(prefix))):
                    playlist = Playlist(
                        id=item["id"], name=item["name"], tracks=[]  # Will be loaded on demand
                    )
                    playlists.append(playlist)

            # Handle pagination
            if results["next"] and self.sp:
                results = self.sp.next(results)
                pagination_count += 1
            else:
                results = None

        return playlists

    def get_playlist_tracks(self, playlist_id: str) -> List[Track]:
        """
        Get tracks from a specific playlist.

        Args:
            playlist_id: Spotify playlist ID

        Returns:
            List of tracks in the playlist
        """
        if not self.sp:
            raise RuntimeError("Spotify client not authenticated")

        tracks = []
        results = self.sp.playlist_items(playlist_id, additional_types=("track",))
        pagination_count = 0
        max_pages = 100  # Safety limit to prevent infinite loops

        while results and pagination_count < max_pages:
            for item in results["items"]:
                if item["track"] and item["track"]["type"] == "track":
                    track_data = item["track"]
                    artists = track_data["artists"][0]["name"] if track_data["artists"] else ""
                    track = Track(
                        id=track_data["id"],
                        title=track_data["name"],
                        artists=artists,
                        original_title=track_data["name"],
                        original_artists=artists,
                    )
                    tracks.append(track)

            # Handle pagination
            if results["next"] and self.sp:
                results = self.sp.next(results)
                pagination_count += 1
            else:
                results = None

        return tracks

    def create_playlist(self, name: str, tracks: List[Track]) -> str:
        """
        Create a new playlist with tracks.

        Args:
            name: Playlist name
            tracks: List of tracks to add

        Returns:
            Created playlist ID
        """
        if not self.sp or not self.user_id:
            raise RuntimeError("Spotify client not authenticated")

        # Create empty playlist
        playlist = self.sp.user_playlist_create(user=self.user_id, name=name, public=False)

        playlist_id = str(playlist["id"])

        # Add tracks if any
        if tracks:
            track_ids = []
            for track in tracks:
                spotify_id = self.search_track(track.title, track.artists)
                if spotify_id:
                    track_ids.append(spotify_id)

            if track_ids:
                # Add tracks in batches of 100 (Spotify limit)
                for i in range(0, len(track_ids), 100):
                    batch = track_ids[i : i + 100]
                    if self.sp:
                        self.sp.playlist_add_items(playlist_id, batch)

        return playlist_id

    def delete_playlist(self, playlist_id: str) -> None:
        """
        Delete a playlist.

        Args:
            playlist_id: Spotify playlist ID to delete
        """
        if not self.sp:
            raise RuntimeError("Spotify client not authenticated")

        self.sp.current_user_unfollow_playlist(playlist_id)

    def get_all_tracks(self) -> List[Track]:
        """Get all tracks - not applicable for Spotify."""
        raise NotImplementedError("Get all tracks not applicable for Spotify")

    def get_tracks_from_playlists(
        self, ignore_playlists: Optional[List[str]] = None
    ) -> List[Track]:
        """Get all tracks from all playlists."""
        all_tracks = []
        track_ids = set()  # Avoid duplicates

        playlists = self.get_playlists(ignore_playlists)
        for playlist in playlists:
            tracks = self.get_playlist_tracks(playlist.id)
            for track in tracks:
                if track.id not in track_ids:
                    track_ids.add(track.id)
                    all_tracks.append(track)

        return all_tracks

    def update_track_metadata(self, track_id: str, title: str, artists: str) -> bool:
        """Update track metadata - not supported by Spotify API."""
        raise NotImplementedError("Track metadata updates not supported by Spotify API")

    def save_changes(self, tracks: list[Track], dry_run: bool = False) -> int:
        """Save changes - not applicable for Spotify read operations."""
        raise NotImplementedError("Save changes not applicable for Spotify")

    def follow_artist(self, artist_name: str) -> None:
        """Follow an artist - not implemented yet."""
        raise NotImplementedError("Artist following not implemented yet")

    def get_followed_artists(self) -> List[str]:
        """Get followed artists - not implemented yet."""
        raise NotImplementedError("Get followed artists not implemented yet")
