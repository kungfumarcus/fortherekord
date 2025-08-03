"""
Tests for matching module.
"""

import pytest
from unittest.mock import Mock, patch

from fortherekord.matching import (
    clean_track_title,
    clean_artist_name,
    calculate_track_similarity,
    match_rekordbox_to_spotify,
    boost_liked_tracks,
    create_match_summary
)


class TestCleanTrackTitle:
    """Test clean_track_title function."""
    
    def test_clean_basic(self):
        """Test basic title cleaning."""
        result = clean_track_title("Song Title")
        assert result == "Song Title"
    
    def test_clean_empty(self):
        """Test cleaning empty title."""
        result = clean_track_title("")
        assert result == ""
    
    def test_clean_with_replacements(self):
        """Test cleaning with replacements."""
        replacements = {"feat.": "featuring", "&": "and"}
        result = clean_track_title("Song feat. Artist & Others", replacements)
        assert result == "Song featuring Artist and Others"
    
    def test_clean_whitespace_normalization(self):
        """Test whitespace normalization."""
        result = clean_track_title("Song   Title   With   Spaces")
        assert result == "Song Title With Spaces"


class TestCleanArtistName:
    """Test clean_artist_name function."""
    
    def test_clean_basic(self):
        """Test basic artist cleaning."""
        result = clean_artist_name("Artist Name")
        assert result == "Artist Name"
    
    def test_clean_empty(self):
        """Test cleaning empty artist."""
        result = clean_artist_name("")
        assert result == ""
    
    def test_clean_with_exclusions(self):
        """Test cleaning with exclusions."""
        exclusions = ["featuring", "feat."]
        result = clean_artist_name("Artist featuring Someone", exclusions)
        assert result == "Artist"
    
    def test_clean_case_insensitive_exclusions(self):
        """Test case insensitive exclusions."""
        exclusions = ["FEATURING"]
        result = clean_artist_name("Artist featuring Someone", exclusions)
        assert result == "Artist"
    
    def test_clean_comma_cleanup(self):
        """Test comma cleanup after exclusions."""
        exclusions = ["featuring"]
        result = clean_artist_name("Artist, featuring Someone", exclusions)
        assert result == "Artist"


class TestCalculateTrackSimilarity:
    """Test calculate_track_similarity function."""
    
    def test_identical_tracks(self):
        """Test similarity of identical tracks."""
        track1 = {
            'title': 'Song Title',
            'artist': 'Artist Name'
        }
        track2 = {
            'title': 'Song Title',
            'artist': 'Artist Name'
        }
        
        similarity = calculate_track_similarity(track1, track2)
        assert similarity == 100.0
    
    def test_different_tracks(self):
        """Test similarity of completely different tracks."""
        track1 = {
            'title': 'Song One',
            'artist': 'Artist One'
        }
        track2 = {
            'title': 'Song Two',
            'artist': 'Artist Two'
        }
        
        similarity = calculate_track_similarity(track1, track2)
        assert similarity < 80.0  # These are quite different but have some similarity
    
    def test_similar_tracks(self):
        """Test similarity of similar tracks."""
        track1 = {
            'title': 'Song Title (Original Mix)',
            'artist': 'Artist Name'
        }
        track2 = {
            'title': 'Song Title',
            'artist': 'Artist Name'
        }
        
        similarity = calculate_track_similarity(track1, track2)
        assert similarity > 65.0  # Should be reasonably high since artist matches perfectly


class TestBoostLikedTracks:
    """Test boost_liked_tracks function."""
    
    def test_boost_liked_tracks(self):
        """Test boosting scores for liked tracks."""
        matches = [
            {
                'spotify_track': {'spotify_uri': 'spotify:track:liked1'},
                'similarity_score': 80.0,
                'match_found': True
            },
            {
                'spotify_track': {'spotify_uri': 'spotify:track:not_liked'},
                'similarity_score': 80.0,
                'match_found': True
            }
        ]
        
        liked_tracks = [{'spotify_uri': 'spotify:track:liked1'}]
        boost_factor = 1.2
        
        boosted = boost_liked_tracks(matches, liked_tracks, boost_factor)
        
        assert boosted[0]['similarity_score'] == 96.0  # 80 * 1.2
        assert boosted[1]['similarity_score'] == 80.0  # unchanged
    
    def test_boost_no_liked_tracks(self):
        """Test boosting with no liked tracks."""
        matches = [
            {
                'spotify_track': {'spotify_uri': 'spotify:track:test'},
                'similarity_score': 80.0,
                'match_found': True
            }
        ]
        
        liked_tracks = []
        boost_factor = 1.2
        
        boosted = boost_liked_tracks(matches, liked_tracks, boost_factor)
        
        assert boosted[0]['similarity_score'] == 80.0  # unchanged


class TestCreateMatchSummary:
    """Test create_match_summary function."""
    
    def test_match_summary(self):
        """Test creating match summary."""
        matches = [
            {'match_found': True, 'similarity_score': 90.0, 'rekordbox_track': {'title': 'Track1'}},
            {'match_found': True, 'similarity_score': 85.0, 'rekordbox_track': {'title': 'Track2'}},
            {'match_found': False, 'similarity_score': 30.0, 'rekordbox_track': {'title': 'Track3'}},
            {'match_found': False, 'similarity_score': 25.0, 'rekordbox_track': {'title': 'Track4'}}
        ]
        
        summary = create_match_summary(matches)
        
        assert summary['total_tracks'] == 4
        assert summary['matched_tracks'] == 2
        assert summary['match_rate_percent'] == '50.0'
        assert summary['average_score'] == 57.5  # (90+85+30+25)/4
    
    def test_match_summary_empty(self):
        """Test creating summary with no matches."""
        matches = []
        
        summary = create_match_summary(matches)
        
        assert summary['total_tracks'] == 0
        assert summary['matched_tracks'] == 0
        assert summary['match_rate_percent'] == '0.0'
        assert summary['average_score'] == 0.0


@patch('fortherekord.matching.process')
class TestMatchRekordboxToSpotify:
    """Test match_rekordbox_to_spotify function."""
    
    def test_basic_matching(self, mock_process):
        """Test basic track matching."""
        # Mock the spotify client
        mock_spotify = Mock()
        mock_track = Mock()
        mock_track.title = 'Song Title'
        mock_track.artist = 'Artist Name'
        mock_track.album = 'Album Name'
        mock_track.year = 2023
        mock_track.spotify_uri = 'spotify:track:123'
        mock_track.track_id = 'track123'
        
        mock_spotify.search_track.return_value = [mock_track]
        
        rekordbox_tracks = [
            {
                'title': 'Song Title',
                'artist': 'Artist Name',
                'track_id': 'rb1'
            }
        ]
        
        # Mock rapidfuzz process.extractOne to return a good match
        mock_process.extractOne.return_value = (
            {
                'title': 'Song Title',
                'artist': 'Artist Name',
                'spotify_uri': 'spotify:track:123'
            },
            95.0,
            0
        )
        
        matches = match_rekordbox_to_spotify(rekordbox_tracks, mock_spotify)
        
        assert len(matches) == 1
        assert matches[0]['match_found'] is True
        assert matches[0]['similarity_score'] == 100.0  # Perfect match gives 100.0
        assert matches[0]['spotify_track']['spotify_uri'] == 'spotify:track:123'
