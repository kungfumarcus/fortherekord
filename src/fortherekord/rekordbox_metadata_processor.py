"""
Rekordbox metadata processing functionality.

Handles title enhancement, artist processing, and text replacements
based on configuration settings.
"""

import re
from typing import Dict, List, Tuple, Optional
from .models import Track


class RekordboxMetadataProcessor:
    """Processes and enhances Rekordbox track metadata."""
    
    def __init__(self, config: Dict) -> None:
        """Initialize with configuration settings."""
        # Support both dictionary and list formats for replace_in_title
        self.replace_in_title = config.get("replace_in_title", {})
        self.ignore_playlists = config.get("ignore_playlists", [])
    
    def enhance_track_title(self, track: Track) -> Track:
        """
        Enhance track title to format: "Title - Artist [Key]"
        
        Args:
            track: Original track with metadata
            
        Returns:
            Track with enhanced title and cleaned artist field
        """
        # Start with original values
        title = track.title.strip() if track.title else ""
        artist = track.artist.strip() if track.artist else ""
        key = track.key
        
        # Clean up whitespace
        title = re.sub(r'\s+', ' ', title)
        if artist:
            artist = re.sub(r'\s+', ' ', artist)
        
        # Remove existing key suffix if present
        title = re.sub(r'\s\[..?.?\]$', '', title)
        
        # Extract artist from title if artist field is empty
        if not artist and " - " in title:
            title_parts = title.split(" - ")
            if len(title_parts) >= 2:
                title = title_parts[0].strip()
                artist = title_parts[1].strip()
        
        # Apply configured text replacements
        title, artist = self._apply_text_replacements(title, artist)
        
        # Remove duplicate artists from title
        if artist:
            artist = self._remove_duplicate_artists(title, artist)
            
            # Remove artist suffix if already present in title
            artist_suffix = f" - {artist}"
            if title.endswith(artist_suffix):
                title = title[:-len(artist_suffix)]
        
        # Build enhanced title
        enhanced_title = self._format_enhanced_title(title, artist, key)
        
        # Return new track with enhanced metadata, preserving original values
        return Track(
            id=track.id,
            title=enhanced_title,
            artist=artist,
            key=track.key,
            bpm=track.bpm,
            original_title=track.original_title,  # Preserve original values
            original_artist=track.original_artist
        )
    
    def _apply_text_replacements(self, title: str, artist: str) -> Tuple[str, str]:
        """Apply configured text replacements to title and artist."""
        # Dictionary format: {"from": "to"}
        for text_from, text_to in self.replace_in_title.items():
            if text_to is None:
                text_to = ""
            
            if text_from in title:
                title = title.replace(text_from, text_to).strip()
            
            if artist and text_from in artist:
                artist = artist.replace(text_from, text_to).strip()
        
        return title, artist
    
    def _remove_duplicate_artists(self, title: str, artist: str) -> str:
        """Remove artist names that appear in title, keeping remaining artists."""
        if not artist:
            return artist
            
        # Split multiple artists
        artists = [a.strip() for a in artist.split(",")]
        removed_artists = []
        retained_artists = []
        
        title_minus_artist = title.replace(f" - {artist}", "")
        
        for individual_artist in artists:
            if individual_artist in title_minus_artist:
                removed_artists.append(individual_artist)
            else:
                retained_artists.append(individual_artist)
        
        # Only remove if some artists remain
        if removed_artists and retained_artists:
            return ", ".join(retained_artists)
        
        return artist
    
    def _format_enhanced_title(self, title: str, artist: str, key: Optional[str]) -> str:
        """Format the final enhanced title."""
        # Start with cleaned title
        enhanced_title = title
        
        # Add artist if present
        if artist:
            enhanced_title = f"{enhanced_title} - {artist}"
        
        # Add key if present
        if key:
            enhanced_title = f"{enhanced_title} [{key}]"
        
        return enhanced_title
    
    def extract_original_metadata(self, tracks: List[Track]) -> None:
        """
        Extract original title and artist from enhanced titles and update tracks directly.
        
        Args:
            tracks: List of Track objects to process
        """
        for track in tracks:
            title = track.title
            artist = track.artist
            key = None
            
            # Extract key from brackets
            key_match = re.search(r'\s\[([^\]]+)\]$', title)
            if key_match:
                key = key_match.group(1)
                title = title[:key_match.start()]
            
            # Extract artist after last " - "
            if " - " in title:
                # Extract the last artist first
                parts = title.rsplit(" - ", 1)
                original_artist = parts[1].strip() if len(parts) == 2 else ""
                
                # Remove all " - artist" patterns to get original title
                # This handles cases like "Title - Artist1 - Artist2 - Artist3"
                original_title = re.sub(r'( - [^-]+)+$', '', title)
                
                # Update the track's original values
                track.original_title = original_title
                track.original_artist = original_artist
            else:
                # No enhancement detected, use current values as original
                track.original_title = track.title
                track.original_artist = track.artist
    
    def check_for_duplicates(self, tracks: List[Track]) -> None:
        """Check for duplicate track titles and print warnings."""
        title_counts = {}
        
        for track in tracks:
            title = track.title
            title_counts[title] = title_counts.get(title, 0) + 1
        
        for title, count in title_counts.items():
            if count > 1:
                print(f"WARNING: Duplicate track found: {title}")
    
    def should_ignore_playlist(self, playlist_name: str) -> bool:
        """Check if playlist should be ignored based on configuration."""
        return playlist_name in self.ignore_playlists
