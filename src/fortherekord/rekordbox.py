"""
Rekordbox XML parsing - simple approach matching PowerShell.
"""

import xml.etree.ElementTree as ET
import re
from typing import Dict, List
from pathlib import Path
import urllib.parse

from .models import RekordboxTrack, RekordboxPlaylist


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
            pattern = re.compile(re.escape(exclusion), re.IGNORECASE)
            cleaned = pattern.sub('', cleaned)
    
    # Clean up commas and whitespace
    cleaned = re.sub(r',\s*,', ',', cleaned)
    cleaned = re.sub(r',\s*$', '', cleaned)
    cleaned = re.sub(r'^\s*,', '', cleaned)
    
    return cleaned.strip()


def load_rekordbox_library(library_path: Path) -> ET.ElementTree:
    if not library_path.exists():
        raise FileNotFoundError(f"Library file not found: {library_path}")
    
    tree = ET.parse(library_path)
    return tree


def get_collection_tracks(library_xml: ET.ElementTree) -> Dict[str, RekordboxTrack]:
    """Get all tracks from collection - matches PowerShell Get-RekordboxCollectionTracks."""
    tracks = {}
    root = library_xml.getroot()
    
    collection = root.find(".//COLLECTION")
    if collection is None:
        return tracks
    
    for track_elem in collection.findall("TRACK"):
        track_id = track_elem.get("TrackID")
        if track_id:
            track = parse_track_from_xml(track_elem)
            tracks[track_id] = track
    
    return tracks


def parse_track_from_xml(track_elem: ET.Element) -> Dict:
    """Parse track from XML element - simple like PowerShell."""
    attrs = track_elem.attrib
    
    def safe_int(value):
        try:
            return int(value) if value else None
        except (ValueError, TypeError):
            return None
    
    def safe_float(value):
        try:
            return float(value) if value else None
        except (ValueError, TypeError):
            return None
    
    file_path = None
    location = attrs.get("Location")
    if location and location.startswith("file://"):
        file_path = Path(urllib.parse.unquote(location[7:]))
    
    return RekordboxTrack(
        title=attrs.get("Name", "").strip(),
        artist=attrs.get("Artist", "").strip(),
        album=attrs.get("Album", "").strip() or None,
        duration=safe_int(attrs.get("TotalTime")),
        bpm=safe_float(attrs.get("AverageBpm")),
        key=attrs.get("Tonality"),
        genre=attrs.get("Genre"),
        year=safe_int(attrs.get("Year")),
        file_path=file_path,
        track_id=attrs.get("TrackID"),
        location=location,
        play_count=safe_int(attrs.get("PlayCount")),
        rating=safe_int(attrs.get("Rating")),
        comments=attrs.get("Comments"),
        grouping=attrs.get("Grouping"),
        mix=attrs.get("Mix"),
        label=attrs.get("Label"),
        remixer=attrs.get("Remixer")
    )


def get_playlists(library_xml: ET.ElementTree, ignore_playlists: List[str] = None) -> Dict[str, RekordboxPlaylist]:
    """Get all playlists - simple like PowerShell."""
    if ignore_playlists is None:
        ignore_playlists = []
    
    playlists = {}
    root = library_xml.getroot()
    
    playlists_elem = root.find(".//PLAYLISTS")
    if playlists_elem is None:
        return playlists
    
    for node in playlists_elem.findall("NODE"):
        extracted = extract_playlists_from_node(node, ignore_playlists)
        playlists.update(extracted)
    
    return playlists


def extract_playlists_from_node(node_elem: ET.Element, ignore_playlists: List[str]) -> Dict[str, RekordboxPlaylist]:
    """Extract playlists recursively from XML node."""
    playlists = {}
    
    name = node_elem.get("Name", "").strip()
    if not name or name in ignore_playlists:
        return playlists
    
    child_nodes = node_elem.findall("NODE")
    track_elements = node_elem.findall("TRACK")
    
    is_folder = len(child_nodes) > 0 and len(track_elements) == 0
    
    if not is_folder and len(track_elements) > 0:
        track_ids = [track_elem.get("Key") for track_elem in track_elements if track_elem.get("Key")]
        
        playlist = RekordboxPlaylist(
            name=name,
            track_ids=track_ids,
            key_id=node_elem.get("KeyID"),
            type=node_elem.get("Type"),
            entries=len(track_ids),
            is_folder=False
        )
        
        playlists[name] = playlist
    
    for child_node in child_nodes:
        child_playlists = extract_playlists_from_node(child_node, ignore_playlists)
        playlists.update(child_playlists)
    
    return playlists


def get_tracks_from_playlist(playlist: RekordboxPlaylist, collection_tracks: Dict[str, RekordboxTrack]) -> List[RekordboxTrack]:
    """Get actual track objects for a playlist."""
    tracks = []
    
    for track_id in playlist.track_ids:
        if track_id in collection_tracks:
            tracks.append(collection_tracks[track_id])
    
    return tracks


def process_tracks_for_playlists(playlists: Dict[str, RekordboxPlaylist], collection_tracks: Dict[str, RekordboxTrack]) -> None:
    """Populate the tracks for all playlists from collection tracks."""
    for playlist in playlists.values():
        playlist.tracks = get_tracks_from_playlist(playlist, collection_tracks)


def parse_rekordbox_library(library_path: str) -> tuple[List[RekordboxTrack], List[RekordboxPlaylist]]:
    """Parse Rekordbox library and return tracks and playlists."""
    library_path = Path(library_path)
    
    library_xml = load_rekordbox_library(library_path)
    
    collection_tracks = get_collection_tracks(library_xml)
    tracks = list(collection_tracks.values())
    
    playlists_dict = get_playlists(library_xml)
    playlists = list(playlists_dict.values())
    
    return tracks, playlists


def normalize_track_metadata(track, config):
    """Normalize track metadata based on configuration."""
    # Create a copy as dictionary
    normalized = {
        'title': track.title or "",
        'artist': track.artist or "",
        'album': track.album,
        'duration': track.duration,
        'bpm': track.bpm,
        'key': track.key,
        'genre': track.genre,
        'year': track.year,
        'track_id': track.track_id
    }
    
    # Apply title replacements
    title_replacements = getattr(config, 'title_replacements', {})
    if hasattr(config, 'text_processing') and config.text_processing:
        for replacement in config.text_processing.replace_in_title:
            normalized['title'] = normalized['title'].replace(replacement.from_text, replacement.to)
    elif title_replacements:
        for from_text, to_text in title_replacements.items():
            normalized['title'] = normalized['title'].replace(from_text, to_text)
    
    # Trim whitespace after replacements
    normalized['title'] = normalized['title'].strip()
    
    # Handle artist extraction from title (if title has " - " format)
    extract_artist = getattr(config, 'extract_artist_from_title', False)
    if extract_artist and not normalized['artist'] and ' - ' in normalized['title']:
        parts = normalized['title'].split(' - ', 1)
        if len(parts) == 2:
            normalized['artist'] = parts[0].strip()
            normalized['title'] = parts[1].strip()
    
    # Remove artist exclusions
    artist_exclusions = getattr(config, 'artist_exclusions', [])
    if hasattr(config, 'spotify') and config.spotify and config.spotify.exclude_from_names:
        for exclusion in config.spotify.exclude_from_names:
            normalized['artist'] = normalized['artist'].replace(exclusion, '').strip()
    elif artist_exclusions:
        for exclusion in artist_exclusions:
            # Remove everything from the exclusion word onwards
            import re
            pattern = re.compile(r'\b' + re.escape(exclusion) + r'.*', re.IGNORECASE)
            normalized['artist'] = pattern.sub('', normalized['artist']).strip()
    
    # Add key to title if present
    add_key = getattr(config, 'add_key_to_title', False)
    if add_key and normalized['key'] and normalized['key'] not in normalized['title']:
        normalized['title'] = f"{normalized['title']} [{normalized['key']}]"
    
    # Remove artist from title if it's already in artist field
    remove_artist = getattr(config, 'remove_artist_from_title', False)
    if remove_artist and normalized['artist'] and normalized['artist'] in normalized['title']:
        # Remove "artist - " from title
        title_pattern = f"{normalized['artist']} - "
        if title_pattern in normalized['title']:
            normalized['title'] = normalized['title'].replace(title_pattern, '')
    
    # Create a simple object to return (duck typing for test compatibility)
    class NormalizedTrack:
        def __init__(self, data):
            for key, value in data.items():
                setattr(self, key, value)
    
    return NormalizedTrack(normalized)


def get_all_playlist_tracks(xml_tree, collection_tracks):
    """Get all tracks from all playlists."""
    playlists = get_playlists(xml_tree)
    all_tracks = {}
    
    for playlist in playlists.values():
        if hasattr(playlist, 'track_ids'):
            for track_id in playlist.track_ids:
                if track_id in collection_tracks:
                    all_tracks[track_id] = collection_tracks[track_id]
    
    return all_tracks


def build_rekordbox_playlist_tree(xml_tree, collection_tracks, config=None):
    """Build complete playlist tree with tracks."""
    playlists = get_playlists(xml_tree)
    
    # Process tracks for each playlist
    for playlist in playlists.values():
        if hasattr(playlist, 'track_ids'):
            playlist.tracks = []
            for track_id in playlist.track_ids:
                if track_id in collection_tracks:
                    track = collection_tracks[track_id]
                    if config:
                        track = normalize_track_metadata(track, config)
                    playlist.tracks.append(track)
    
    return playlists


def parse_track_metadata(track_elem: ET.Element) -> Dict:
    """Alias for parse_track_from_xml for test compatibility."""
    # Return None if no TrackID for test compatibility
    if not track_elem.get("TrackID"):
        return None
    return parse_track_from_xml(track_elem)
