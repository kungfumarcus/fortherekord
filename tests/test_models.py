"""
Unit tests for data models.

Tests for models.py module functions.
"""

import pytest
from pathlib import Path

from fortherekord.models import RekordboxTrack, RekordboxPlaylist, spotify_track_from_data


class TestRekordboxTrack:
    """Test RekordboxTrack class creation."""
    
    def test_rekordbox_track_basic(self):
        """Test basic track creation."""
        track = RekordboxTrack(title="Test Song", artist="Test Artist")
        assert track.title == "Test Song"
        assert track.artist == "Test Artist"
        assert track.album is None
        assert track.duration is None
    
    def test_rekordbox_track_with_all_fields(self):
        """Test track creation with all fields."""
        track = RekordboxTrack(
            title="Test Song",
            artist="Test Artist",
            album="Test Album",
            duration=180,
            bpm=128.5,
            key="Am",
            genre="House",
            year=2023,
            file_path=Path("/music/test.mp3"),
            track_id="123"
        )
        assert track.title == "Test Song"
        assert track.artist == "Test Artist"
        assert track.album == "Test Album"
        assert track.duration == 180
        assert track.bpm == 128.5
        assert track.key == "Am"
        assert track.genre == "House"
        assert track.year == 2023
        assert track.file_path == Path("/music/test.mp3")
        assert track.track_id == "123"
    
    def test_rekordbox_track_extra_fields(self):
        """Test track creation with extra fields via kwargs."""
        track = RekordboxTrack(
            title="Test Song",
            artist="Test Artist",
            play_count=5,
            rating=4,
            custom_field="custom_value"
        )
        assert track.title == "Test Song"
        assert track.artist == "Test Artist"
        assert track.play_count == 5
        assert track.rating == 4
        assert track.custom_field == "custom_value"


class TestRekordboxPlaylist:
    """Test RekordboxPlaylist class functions."""
    
    def test_rekordbox_playlist_basic(self):
        """Test basic playlist creation."""
        tracks = [
            RekordboxTrack(title="Song 1", artist="Artist 1"),
            RekordboxTrack(title="Song 2", artist="Artist 2")
        ]
        playlist = RekordboxPlaylist(name="Test Playlist", tracks=tracks)
        assert playlist.name == "Test Playlist"
        assert len(playlist.tracks) == 2
        assert playlist.tracks == tracks
    
    def test_rekordbox_playlist_with_track_ids(self):
        """Test playlist creation with track IDs."""
        playlist = RekordboxPlaylist(
            name="Test Playlist",
            track_ids=["1", "2", "3"],
            key_id="playlist123",
            entries=3,
            is_folder=False
        )
        assert playlist.name == "Test Playlist"
        assert playlist.track_ids == ["1", "2", "3"]
        assert playlist.key_id == "playlist123"
        assert playlist.entries == 3
        assert playlist.is_folder is False
    
    def test_empty_playlist(self):
        """Test empty playlist."""
        playlist = RekordboxPlaylist(name="Empty Playlist")
        assert playlist.name == "Empty Playlist"
        assert len(playlist.tracks) == 0
        assert playlist.track_ids == []
        assert playlist.entries == 0
    
    def test_playlist_extra_fields(self):
        """Test playlist creation with extra fields."""
        playlist = RekordboxPlaylist(
            name="Test Playlist",
            spotify_id="spotify123",
            public=True,
            collaborative=False,
            custom_field="value"
        )
        assert playlist.name == "Test Playlist"
        assert playlist.spotify_id == "spotify123"
        assert playlist.public is True
        assert playlist.collaborative is False
        assert playlist.custom_field == "value"


class TestSpotifyTrackFromData:
    """Test Spotify track creation from API data."""
    
    def test_spotify_track_from_api_data(self):
        """Test creating track from API response."""
        api_data = {
            'name': 'Test Song',
            'artists': [{'name': 'Artist 1'}, {'name': 'Artist 2'}],
            'album': {
                'name': 'Test Album',
                'release_date': '2023-06-15'
            },
            'duration_ms': 180000,
            'uri': 'spotify:track:123',
            'id': '123',
            'popularity': 75,
            'external_urls': {'spotify': 'https://open.spotify.com/track/123'},
            'preview_url': 'https://preview.spotify.com/123'
        }
        
        track = spotify_track_from_data(api_data)
        assert track.title == 'Test Song'
        assert track.artist == 'Artist 1, Artist 2'
        assert track.album == 'Test Album'
        assert track.duration == 180
        assert track.year == 2023
        assert track.spotify_uri == 'spotify:track:123'
        assert track.spotify_id == '123'
        assert track.track_id == 'spotify:track:123'
        assert track.popularity == 75
    
    def test_spotify_track_from_minimal_data(self):
        """Test creating track from minimal API data."""
        api_data = {
            'name': 'Test Song',
            'artists': [],
            'uri': 'spotify:track:123'
        }
        
        track = spotify_track_from_data(api_data)
        assert track.title == 'Test Song'
        assert track.artist == 'Unknown Artist'
        assert track.album is None
        assert track.duration is None
        assert track.year is None
        assert track.spotify_uri == 'spotify:track:123'
        assert track.track_id == 'spotify:track:123'
