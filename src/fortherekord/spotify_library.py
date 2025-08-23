"""
Spotify API integration for playlist synchronization.

Provides basic authentication and playlist operations.
"""

from typing import List, Optional

import spotipy
from spotipy.oauth2 import SpotifyOAuth

from .models import Track, Playlist


class SpotifyLibrary:
    """
    Spotify API adapter for playlist management.

    Provides playlist management and track operations using Spotify Web API.
    """

    def __init__(self, client_id: str, client_secret: str) -> None:
        """Initialize Spotify client with OAuth credentials."""
        self.client_id = client_id
        self.client_secret = client_secret
        self.sp: Optional[spotipy.Spotify] = None
        self.user_id: Optional[str] = None
        self._authenticate()

    def _authenticate(self) -> None:
        """Setup Spotify OAuth authentication."""
        scope = (
            "playlist-read-private playlist-modify-public playlist-modify-private user-library-read"
        )

        auth_manager = SpotifyOAuth(
            client_id=self.client_id,
            client_secret=self.client_secret,
            redirect_uri="http://127.0.0.1:8888/callback",
            scope=scope,
            cache_path=".spotify_cache",
        )

        self.sp = spotipy.Spotify(auth_manager=auth_manager)

        # Get user ID
        user_info = self.sp.current_user()
        self.user_id = user_info["id"]

    def search_track(self, title: str, artists: str) -> Optional[str]:
        """
        Search for a track and return the first result's Spotify ID.

        Args:
            title: Track title
            artists: Artist name

        Returns:
            Spotify track ID if found, None otherwise
        """
        if not self.sp:
            raise RuntimeError("Spotify client not authenticated")

        query = f"track:{title} artists:{artists}"
        results = self.sp.search(q=query, type="track", limit=1)

        if results["tracks"]["items"]:
            return str(results["tracks"]["items"][0]["id"])
        return None

    def get_playlists(self, ignore_playlists: Optional[List[str]] = None) -> List[Playlist]:
        """
        Get user's playlists from Spotify.

        Args:
            ignore_playlists: List of playlist names to exclude

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
                if item["name"] not in ignore_playlists and item["owner"]["id"] == self.user_id:
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
        results = self.sp.playlist_tracks(playlist_id)
        pagination_count = 0
        max_pages = 100  # Safety limit to prevent infinite loops

        while results and pagination_count < max_pages:
            for item in results["items"]:
                if item["track"] and item["track"]["type"] == "track":
                    track_data = item["track"]
                    artist_name = (
                        track_data["artists"][0]["name"]
                        if track_data["artists"]
                        else "Unknown Artist"
                    )
                    track = Track(
                        id=track_data["id"],
                        title=track_data["name"],
                        artists=artist_name,
                        original_title=track_data["name"],
                        original_artists=artist_name,
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
