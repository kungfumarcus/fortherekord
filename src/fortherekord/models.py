"""
Simple data structures for ForTheRekord with clean dot notation.
"""

from typing import List, Optional, Any


class RekordboxTrack:
    """Simple track class with dot notation access."""
    
    def __init__(self, title: str = "", artist: str = "", **kwargs):
        self.title = title
        self.artist = artist
        self.album = kwargs.get('album')
        self.duration = kwargs.get('duration')
        self.bpm = kwargs.get('bpm')
        self.key = kwargs.get('key')
        self.genre = kwargs.get('genre')
        self.year = kwargs.get('year')
        self.track_id = kwargs.get('track_id')
        self.file_path = kwargs.get('file_path')
        
        # Add any additional kwargs as attributes
        for key, value in kwargs.items():
            if not hasattr(self, key):
                setattr(self, key, value)


class RekordboxPlaylist:
    """Simple playlist class with dot notation access."""
    
    def __init__(self, name: str, tracks: List[RekordboxTrack] = None, **kwargs):
        self.name = name
        self.tracks = tracks or []
        self.track_ids = kwargs.get('track_ids', [])
        self.playlist_id = kwargs.get('playlist_id')
        self.key_id = kwargs.get('key_id')
        self.entries = kwargs.get('entries', 0)
        self.is_folder = kwargs.get('is_folder', False)
        
        # Add any additional kwargs as attributes
        for key, value in kwargs.items():
            if not hasattr(self, key):
                setattr(self, key, value)


def spotify_track_from_data(data: dict) -> RekordboxTrack:
    """Convert Spotify API data to RekordboxTrack object."""
    artists = [artist['name'] for artist in data.get('artists', [])]
    artist = ', '.join(artists) if artists else 'Unknown Artist'
    
    album_data = data.get('album', {})
    year = None
    if album_data.get('release_date'):
        year = int(album_data['release_date'][:4])
    
    return RekordboxTrack(
        title=data.get('name', 'Unknown Title'),
        artist=artist,
        album=album_data.get('name'),
        duration=data.get('duration_ms', 0) // 1000 if data.get('duration_ms') else None,
        year=year,
        spotify_uri=data.get('uri'),
        spotify_id=data.get('id'),
        track_id=data.get('uri'),
        popularity=data.get('popularity'),
        external_urls=data.get('external_urls'),
        preview_url=data.get('preview_url')
    )
