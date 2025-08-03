"""
Spotify API integration module.

Handles authentication, playlist management, and track operations.
"""

import json
import webbrowser
from pathlib import Path
from typing import Dict, List, Optional, Any
from urllib.parse import urlencode, urlparse, parse_qs

import spotipy
from spotipy.oauth2 import SpotifyOAuth

from .config import Config
from .models import RekordboxTrack, RekordboxPlaylist, spotify_track_from_data
from .file_utils import save_json, load_json


class SpotifyClient:
    """Spotify API client with authentication and operations."""
    
    def __init__(self, config: Config):
        """Initialize Spotify client with configuration."""
        self.config = config
        self.sp = None
        self.user_id = None
        self._setup_auth()
    
    def _setup_auth(self):
        """Setup Spotify OAuth authentication."""
        scope = "playlist-read-private playlist-modify-public playlist-modify-private user-library-read user-follow-modify"
        
        auth_manager = SpotifyOAuth(
            client_id=self.config.spotify.client_id,
            client_secret=self.config.spotify.client_secret,
            redirect_uri="http://localhost:8080",
            scope=scope,
            cache_path=".spotify_cache"
        )
        
        self.sp = spotipy.Spotify(auth_manager=auth_manager)
        
        # Get user ID
        user_info = self.sp.current_user()
        self.user_id = user_info['id']
    
    def search_track(self, title: str, artist: str, limit: int = 10) -> List[RekordboxTrack]:
        """Search for tracks on Spotify."""
        query = f'track:"{title}" artist:"{artist}"'
        results = self.sp.search(q=query, type='track', limit=limit)
        
        tracks = []
        for item in results['tracks']['items']:
            track = spotify_track_from_data(item)
            tracks.append(track)
        
        return tracks
    
    def get_user_playlists(self) -> List[RekordboxPlaylist]:
        """Get all user playlists."""
        playlists = []
        results = self.sp.current_user_playlists()
        
        while results:
            for item in results['items']:
                playlist = RekordboxPlaylist(
                    name=item['name'],
                    playlist_id=item['id'],
                    spotify_uri=item['uri'],
                    public=item['public'],
                    collaborative=item['collaborative'],
                    owner_id=item['owner']['id'],
                    snapshot_id=item['snapshot_id'],
                    track_count=item['tracks']['total']
                )
                playlists.append(playlist)
            
            if results['next']:
                results = self.sp.next(results)
            else:
                break
        
        return playlists
    
    def get_playlist_tracks(self, playlist_id: str) -> List[Dict[str, Any]]:
        """Get all tracks from a playlist."""
        tracks = []
        results = self.sp.playlist_tracks(playlist_id)
        
        while results:
            for item in results['items']:
                if item['track'] and item['track']['type'] == 'track':
                    track = spotify_track_from_data(item['track'])
                    track['added_at'] = item['added_at']
                    tracks.append(track)
            
            if results['next']:
                results = self.sp.next(results)
            else:
                break
        
        return tracks
    
    def create_playlist(self, name: str, description: str = "", public: bool = True) -> RekordboxPlaylist:
        """Create a new playlist."""
        playlist_data = self.sp.user_playlist_create(
            user=self.user_id,
            name=name,
            public=public,
            description=description
        )
        
        return RekordboxPlaylist(
            name=playlist_data['name'],
            playlist_id=playlist_data['id'],
            spotify_uri=playlist_data['uri'],
            public=playlist_data['public'],
            collaborative=playlist_data['collaborative'],
            owner_id=playlist_data['owner']['id'],
            snapshot_id=playlist_data['snapshot_id']
        )
    
    def delete_playlist(self, playlist_id: str):
        """Unfollow (delete) a playlist."""
        self.sp.current_user_unfollow_playlist(playlist_id)
    
    def add_tracks_to_playlist(self, playlist_id: str, track_uris: List[str]):
        """Add tracks to a playlist."""
        # Spotify API has a limit of 100 tracks per request
        for i in range(0, len(track_uris), 100):
            batch = track_uris[i:i+100]
            self.sp.playlist_add_items(playlist_id, batch)
    
    def remove_tracks_from_playlist(self, playlist_id: str, track_uris: List[str]):
        """Remove tracks from a playlist."""
        # Spotify API has a limit of 100 tracks per request
        for i in range(0, len(track_uris), 100):
            batch = track_uris[i:i+100]
            self.sp.playlist_remove_all_occurrences_of_items(playlist_id, batch)
    
    def replace_playlist_tracks(self, playlist_id: str, track_uris: List[str]):
        """Replace all tracks in a playlist."""
        # First, replace with first 100 tracks (or empty if no tracks)
        if track_uris:
            first_batch = track_uris[:100]
            self.sp.playlist_replace_items(playlist_id, first_batch)
            
            # Add remaining tracks in batches
            if len(track_uris) > 100:
                remaining = track_uris[100:]
                self.add_tracks_to_playlist(playlist_id, remaining)
        else:
            # Empty playlist
            self.sp.playlist_replace_items(playlist_id, [])
    
    def get_saved_tracks(self) -> List[Dict[str, Any]]:
        """Get user's saved (liked) tracks."""
        tracks = []
        results = self.sp.current_user_saved_tracks()
        
        while results:
            for item in results['items']:
                track = spotify_track_from_data(item['track'])
                # Add the added_at field as an attribute
                setattr(track, 'added_at', item['added_at'])
                tracks.append(track)
            
            if results['next']:
                results = self.sp.next(results)
            else:
                break
        
        return tracks
    
    def follow_artist(self, artist_id: str):
        """Follow an artist."""
        self.sp.user_follow_artists([artist_id])
    
    def get_artist_from_track(self, track: Dict[str, Any]) -> Optional[str]:
        """Extract artist ID from track data."""
        if 'artists' in track and track['artists']:
            return track['artists'][0]['id']
        return None
    
    def find_artist_by_name(self, artist_name: str) -> Optional[str]:
        """Find artist ID by name."""
        results = self.sp.search(q=f'artist:"{artist_name}"', type='artist', limit=1)
        if results['artists']['items']:
            return results['artists']['items'][0]['id']
        return None


def clean_playlist_name(name: str, replacements: Optional[List[Dict[str, str]]] = None) -> str:
    """Apply text replacements to playlist name."""
    if replacements is None:
        replacements = []
    
    cleaned = name
    for replacement in replacements:
        cleaned = cleaned.replace(replacement['from'], replacement['to'])
    return cleaned


def clean_track_title_for_spotify(title: str, replacements: Optional[List[Dict[str, str]]] = None) -> str:
    """Apply Spotify-specific text replacements to track title."""
    if replacements is None:
        replacements = []
    
    cleaned = title
    for replacement in replacements:
        cleaned = cleaned.replace(replacement['from'], replacement['to'])
    return cleaned


def cache_spotify_tracks(tracks: List[Dict[str, Any]], cache_file: str = "spotify_tracks_cache.json"):
    """Cache Spotify tracks to file."""
    save_json(tracks, cache_file)


def load_spotify_tracks_cache(cache_file: str = "spotify_tracks_cache.json") -> List[Dict[str, Any]]:
    """Load cached Spotify tracks."""
    try:
        return load_json(cache_file) or []
    except FileNotFoundError:
        return []
