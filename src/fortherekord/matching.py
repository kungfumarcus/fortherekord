"""
Track matching module.

Handles fuzzy matching between Rekordbox and Spotify tracks.
"""

import re
from typing import Dict, List, Optional, Any, Tuple
from rapidfuzz import fuzz, process

from .models import RekordboxTrack


def clean_track_title(title: str, replacements: Dict[str, str] = None) -> str:
    """Clean track title with simple replacements like PowerShell."""
    if not title:
        return ""
    
    cleaned = title.strip()
    cleaned = re.sub(r'\s+', ' ', cleaned)  # Remove extra whitespace
    
    if replacements:
        for from_text, to_text in replacements.items():
            cleaned = cleaned.replace(from_text, to_text)
    
    return cleaned.strip()


def clean_artist_name(artist: str, exclusions: List[str] = None) -> str:
    """Clean artist name with simple exclusions like PowerShell."""
    if not artist:
        return ""
    
    cleaned = artist.strip()
    cleaned = re.sub(r'\s+', ' ', cleaned)  # Remove extra whitespace
    
    if exclusions:
        for exclusion in exclusions:
            # Find the exclusion word and remove everything from that point onwards
            pattern = re.compile(r'\b' + re.escape(exclusion) + r'\b.*', re.IGNORECASE)
            cleaned = pattern.sub('', cleaned)
    
    # Clean up commas and whitespace
    cleaned = re.sub(r',\s*,', ',', cleaned)
    cleaned = re.sub(r',\s*$', '', cleaned)
    cleaned = re.sub(r'^\s*,', '', cleaned)
    
    return cleaned.strip()


def calculate_track_similarity(rekordbox_track: Dict[str, Any], spotify_track: Dict[str, Any]) -> float:
    """Calculate similarity score between two tracks (0-100 scale)."""
    # Clean titles and artists for comparison
    rb_title = clean_track_title(rekordbox_track.get('title', ''))
    rb_artist = clean_artist_name(rekordbox_track.get('artist', ''))
    
    sp_title = clean_track_title(spotify_track.get('title', ''))
    sp_artist = clean_artist_name(spotify_track.get('artist', ''))
    
    # Calculate similarity scores
    title_score = fuzz.ratio(rb_title.lower(), sp_title.lower())
    artist_score = fuzz.ratio(rb_artist.lower(), sp_artist.lower())
    
    # Weighted average (title is more important)
    similarity = (title_score * 0.7) + (artist_score * 0.3)
    
    return similarity


def find_best_match(rekordbox_track: Dict[str, Any], spotify_tracks: List[Dict[str, Any]], 
                   threshold: float = 0.8) -> Optional[Dict[str, Any]]:
    """Find the best matching Spotify track for a Rekordbox track."""
    if not spotify_tracks:
        return None
    
    best_match = None
    best_score = 0.0
    
    for spotify_track in spotify_tracks:
        score = calculate_track_similarity(rekordbox_track, spotify_track)
        if score > best_score:
            best_score = score
            best_match = spotify_track
    
    # Return match only if it meets the threshold
    if best_score >= threshold * 100:  # Convert threshold to 0-100 scale
        match_result = best_match.copy()
        match_result['match_score'] = best_score
        return match_result
    
    return None


def match_rekordbox_to_spotify(rekordbox_tracks: List[Dict[str, Any]], 
                              spotify_client, 
                              threshold: float = 0.8) -> List[Dict[str, Any]]:
    """Match Rekordbox tracks to Spotify tracks."""
    matches = []
    
    for rb_track in rekordbox_tracks:
        # Search for the track on Spotify
        spotify_results = spotify_client.search_track(
            title=rb_track.get('title', ''),
            artist=rb_track.get('artist', ''),
            limit=10
        )
        
        # Convert RekordboxTrack objects to dictionaries for matching
        spotify_dicts = []
        for track in spotify_results:
            track_dict = {
                'title': track.title,
                'artist': track.artist,
                'album': track.album,
                'year': track.year,
                'spotify_uri': track.spotify_uri,
                'track_id': track.track_id
            }
            spotify_dicts.append(track_dict)
        
        # Find best match
        match = find_best_match(rb_track, spotify_dicts, threshold)
        
        match_result = {
            'rekordbox_track': rb_track,
            'spotify_track': match,
            'match_score': match.get('match_score', 0.0) if match else 0.0,
            'similarity_score': match.get('match_score', 0.0) if match else 0.0,
            'match_found': match is not None
        }
        
        matches.append(match_result)
    
    return matches


def create_search_string(track: Dict[str, Any]) -> str:
    """Create a search string for a track."""
    title = track.get('title', '').strip()
    artist = track.get('artist', '').strip()
    
    if not title and not artist:
        return ''
    
    if not artist:
        return title
    
    if not title:
        return artist
    
    return f"{artist} {title}"


def boost_liked_tracks(matches: List[Dict[str, Any]], 
                      liked_tracks: List[Dict[str, Any]], 
                      boost_factor: float = 2.0) -> List[Dict[str, Any]]:
    """Boost match scores for tracks that are in the user's liked tracks."""
    # Create set of liked track URIs for fast lookup
    liked_uris = {track.get('spotify_uri') for track in liked_tracks if track.get('spotify_uri')}
    
    boosted_matches = []
    for match in matches:
        boosted_match = match.copy()
        
        spotify_track = match.get('spotify_track')
        if spotify_track and spotify_track.get('spotify_uri') in liked_uris:
            # Boost the similarity_score but cap at 100.0
            original_score = match.get('similarity_score', 0.0)
            boosted_score = min(100.0, original_score * boost_factor)
            boosted_match['similarity_score'] = boosted_score
            boosted_match['liked_boost_applied'] = True
        
        boosted_matches.append(boosted_match)
    
    return boosted_matches


def filter_matches_by_threshold(matches: List[Dict[str, Any]], threshold: float) -> List[Dict[str, Any]]:
    """Filter matches to only include those above the threshold."""
    return [match for match in matches if match.get('match_score', 0.0) >= threshold]


def get_unmatched_tracks(matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Get list of Rekordbox tracks that couldn't be matched."""
    return [match['rekordbox_track'] for match in matches if not match.get('match_found')]


def get_matched_tracks(matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Get list of successfully matched track pairs."""
    return [match for match in matches if match.get('match_found')]


def create_match_summary(matches: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Create a summary of matching results."""
    total_tracks = len(matches)
    matched = len(get_matched_tracks(matches))
    unmatched = len(get_unmatched_tracks(matches))
    
    if total_tracks > 0:
        match_rate = (matched / total_tracks) * 100
        match_rate_str = str(round(match_rate, 1))
    else:
        match_rate_str = '0.0'
    
    return {
        'total_tracks': total_tracks,
        'matched_tracks': matched,
        'unmatched_tracks': unmatched,
        'match_rate_percent': match_rate_str,
        'average_score': sum(match.get('similarity_score', match.get('match_score', 0.0)) for match in matches) / total_tracks if total_tracks > 0 else 0.0
    }
