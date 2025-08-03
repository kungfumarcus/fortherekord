"""
Tests for Spotify API integration module.

Tests authentication, playlist management, and track operations.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from fortherekord.config import Config, SpotifyConfig, RekordboxConfig
from fortherekord.spotify import SpotifyClient, clean_playlist_name, clean_track_title_for_spotify
from fortherekord.models import RekordboxTrack, RekordboxPlaylist


class TestCleanPlaylistName:
    """Test playlist name cleaning functionality."""
    
    def test_clean_basic(self):
        """Test basic playlist name cleaning with no replacements."""
        result = clean_playlist_name("My Playlist")
        assert result == "My Playlist"
    
    def test_clean_with_replacements(self):
        """Test cleaning with replacements."""
        replacements = [
            {"from": "&", "to": "and"},
            {"from": "/", "to": "-"}
        ]
        result = clean_playlist_name("Rock & Roll/Metal", replacements)
        assert result == "Rock and Roll-Metal"
    
    def test_clean_empty_replacements(self):
        """Test cleaning with empty replacements list."""
        result = clean_playlist_name("Test Playlist", [])
        assert result == "Test Playlist"


class TestCleanTrackTitleForSpotify:
    """Test track title cleaning for Spotify."""
    
    def test_clean_basic(self):
        """Test basic track title cleaning with no replacements."""
        result = clean_track_title_for_spotify("Song Title")
        assert result == "Song Title"
    
    def test_clean_remix_indicators(self):
        """Test cleaning remix indicators."""
        replacements = [{"from": "(Original Mix)", "to": ""}]
        result = clean_track_title_for_spotify("Song Title (Original Mix)", replacements)
        assert result == "Song Title "
    
    def test_clean_multiple_indicators(self):
        """Test cleaning multiple indicators."""
        replacements = [
            {"from": "(Radio Edit)", "to": ""},
            {"from": "(Extended Mix)", "to": ""}
        ]
        result = clean_track_title_for_spotify("Song Title (Radio Edit) (Extended Mix)", replacements)
        assert result == "Song Title  "


@patch('fortherekord.spotify.spotipy.Spotify')
@patch('fortherekord.spotify.SpotifyOAuth')
class TestSpotifyClient:
    """Test SpotifyClient class."""
    
    def test_init(self, mock_oauth, mock_spotify):
        """Test SpotifyClient initialization."""
        mock_sp = Mock()
        mock_sp.current_user.return_value = {'id': 'test_user'}
        mock_spotify.return_value = mock_sp
        
        config = Config(
            spotify=SpotifyConfig(client_id="test_id", client_secret="test_secret"),
            rekordbox=RekordboxConfig(library_path="test.xml")
        )
        
        client = SpotifyClient(config)
        assert client.user_id == 'test_user'
        assert client.sp == mock_sp
    
    def test_search_track(self, mock_oauth, mock_spotify):
        """Test track searching."""
        mock_sp = Mock()
        mock_sp.current_user.return_value = {'id': 'test_user'}
        mock_sp.search.return_value = {
            'tracks': {
                'items': [
                    {
                        'id': 'track1',
                        'name': 'Song Title',
                        'artists': [{'name': 'Artist Name'}],
                        'uri': 'spotify:track:track1',
                        'duration_ms': 180000,
                        'album': {
                            'name': 'Album Name',
                            'release_date': '2023-01-01'
                        }
                    }
                ]
            }
        }
        mock_spotify.return_value = mock_sp
        
        config = Config(
            spotify=SpotifyConfig(client_id="test_id", client_secret="test_secret"),
            rekordbox=RekordboxConfig(library_path="test.xml")
        )
        
        client = SpotifyClient(config)
        results = client.search_track("Song Title", "Artist Name")
        
        assert len(results) == 1
        assert results[0].title == 'Song Title'
        assert results[0].artist == 'Artist Name'
        assert results[0].album == 'Album Name'
        assert results[0].year == 2023
    
    def test_get_user_playlists(self, mock_oauth, mock_spotify):
        """Test getting user playlists."""
        mock_sp = Mock()
        mock_sp.current_user.return_value = {'id': 'test_user'}
        mock_sp.current_user_playlists.return_value = {
            'items': [
                {
                    'id': 'playlist1',
                    'name': 'My Playlist',
                    'uri': 'spotify:playlist:playlist1',
                    'public': True,
                    'collaborative': False,
                    'owner': {'id': 'test_user'},
                    'snapshot_id': 'snapshot1',
                    'tracks': {'total': 10}
                }
            ],
            'next': None
        }
        mock_spotify.return_value = mock_sp
        
        config = Config(
            spotify=SpotifyConfig(client_id="test_id", client_secret="test_secret"),
            rekordbox=RekordboxConfig(library_path="test.xml")
        )
        
        client = SpotifyClient(config)
        playlists = client.get_user_playlists()
        
        assert len(playlists) == 1
        assert playlists[0].name == 'My Playlist'
        assert playlists[0].playlist_id == 'playlist1'
        assert playlists[0].public == True
        assert playlists[0].track_count == 10
    
    def test_create_playlist(self, mock_oauth, mock_spotify):
        """Test creating a playlist."""
        mock_sp = Mock()
        mock_sp.current_user.return_value = {'id': 'test_user'}
        mock_sp.user_playlist_create.return_value = {
            'id': 'new_playlist',
            'name': 'New Playlist',
            'uri': 'spotify:playlist:new_playlist',
            'public': True,
            'collaborative': False,
            'owner': {'id': 'test_user'},
            'snapshot_id': 'new_snapshot'
        }
        mock_spotify.return_value = mock_sp
        
        config = Config(
            spotify=SpotifyConfig(client_id="test_id", client_secret="test_secret"),
            rekordbox=RekordboxConfig(library_path="test.xml")
        )
        
        client = SpotifyClient(config)
        playlist = client.create_playlist("New Playlist")
        
        assert playlist.name == 'New Playlist'
        assert playlist.playlist_id == 'new_playlist'
        assert playlist.spotify_uri == 'spotify:playlist:new_playlist'
        assert playlist.public == True
    
    def test_get_saved_tracks(self, mock_oauth, mock_spotify):
        """Test getting saved (liked) tracks."""
        mock_sp = Mock()
        mock_sp.current_user.return_value = {'id': 'test_user'}
        mock_sp.current_user_saved_tracks.return_value = {
            'items': [
                {
                    'added_at': '2023-01-01T00:00:00Z',
                    'track': {
                        'id': 'track1',
                        'name': 'Liked Song',
                        'artists': [{'name': 'Artist'}],
                        'uri': 'spotify:track:track1',
                        'duration_ms': 180000,
                        'album': {
                            'name': 'Album',
                            'release_date': '2023-01-01'
                        }
                    }
                }
            ],
            'next': None
        }
        mock_spotify.return_value = mock_sp
        
        config = Config(
            spotify=SpotifyConfig(client_id="test_id", client_secret="test_secret"),
            rekordbox=RekordboxConfig(library_path="test.xml")
        )
        
        client = SpotifyClient(config)
        tracks = client.get_saved_tracks()
        
        assert len(tracks) == 1
        assert tracks[0].title == 'Liked Song'
        assert tracks[0].artist == 'Artist'
        assert hasattr(tracks[0], 'added_at')
    
    def test_add_tracks_to_playlist(self, mock_oauth, mock_spotify):
        """Test adding tracks to a playlist."""
        mock_sp = Mock()
        mock_sp.current_user.return_value = {'id': 'test_user'}
        mock_spotify.return_value = mock_sp
        
        config = Config(
            spotify=SpotifyConfig(client_id="test_id", client_secret="test_secret"),
            rekordbox=RekordboxConfig(library_path="test.xml")
        )
        
        client = SpotifyClient(config)
        track_uris = ['spotify:track:1', 'spotify:track:2']
        
        client.add_tracks_to_playlist('playlist1', track_uris)
        
        mock_sp.playlist_add_items.assert_called_once_with('playlist1', track_uris)
    
    def test_replace_playlist_tracks(self, mock_oauth, mock_spotify):
        """Test replacing all tracks in a playlist."""
        mock_sp = Mock()
        mock_sp.current_user.return_value = {'id': 'test_user'}
        mock_spotify.return_value = mock_sp
        
        config = Config(
            spotify=SpotifyConfig(client_id="test_id", client_secret="test_secret"),
            rekordbox=RekordboxConfig(library_path="test.xml")
        )
        
        client = SpotifyClient(config)
        track_uris = ['spotify:track:1', 'spotify:track:2']
        
        client.replace_playlist_tracks('playlist1', track_uris)
        
        mock_sp.playlist_replace_items.assert_called_once_with('playlist1', track_uris)
