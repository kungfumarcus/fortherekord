"""
Music library processing functionality.

Handles title enhancement, artists processing, and text replacements
based on configuration settings.
"""

import re
from typing import Dict, List, Tuple, Optional
from .models import Track


class MusicLibraryProcessor:
    """Processes and enhances music library track metadata."""

    def __init__(self, config: Dict) -> None:
        """Initialize with configuration settings."""
        # Use list format for replacements: [{"from": "old", "to": "new"}, ...]
        self.replace_in_title = config.get("replace_in_title", [])
        self.replace_in_artist = config.get("replace_in_artist", [])

        # Configuration for enhancement features - defaults to False for safety
        self.add_key_to_title = config.get("add_key_to_title", False)
        self.add_artist_to_title = config.get("add_artist_to_title", False)
        self.remove_artists_in_title = config.get("remove_artists_in_title", False)

    def process_track(self, track: Track) -> None:
        """
        Process track to enhance title format: "Title - Artist [Key]"
        Modifies the track object in-place.

        Args:
            track: Track object to process (modified in-place)
        """
        
        # Use original_title if available (cleaned version), otherwise fall back to title
        working_title = track.original_title if hasattr(track, 'original_title') and track.original_title else track.title

        # Clean up whitespace in working title and artists
        working_title = re.sub(r"\s+", " ", working_title).strip()
        if track.artists:
            track.artists = re.sub(r"\s+", " ", track.artists).strip()

        # Extract artists from title if artists field is empty
        # (do this early, before other processing)
        if track.artists == "" and " - " in working_title:
            title_parts = working_title.split(" - ")
            if len(title_parts) == 2:
                extracted_artist = title_parts[1].strip()
                working_title = title_parts[0].strip()
                track.artists = extracted_artist
                print(f"Set artist name for '{working_title}' to '{extracted_artist}'")

        # Remove existing key suffix if present (shouldn't be needed with original_title but just in case)
        working_title = re.sub(r"\s\[..?.?\]$", "", working_title)

        # Apply configured text replacements
        working_title, track.artists = self._apply_text_replacements(working_title, track.artists)

        # Build enhanced title based on configuration
        artists_not_in_title = track.artists
        if track.artists and self.remove_artists_in_title:
            artists_not_in_title, _ = self._split_artists_by_title(working_title, track.artists)
        track.enhanced_title = self._format_enhanced_title(
            working_title, artists_not_in_title, track.key
        )

        # Update the actual title field with the processed clean title
        track.title = working_title

        # Print detailed change information
        self._print_track_changes(track)

    def _apply_text_replacements(self, title: str, artists: str) -> Tuple[str, str]:
        """Apply configured text replacements to title and artists."""
        # Apply title replacements
        for replacement in self.replace_in_title:
            text_from = replacement.get("from", "")
            text_to = replacement.get("to", "")

            if text_from in title:
                title = title.replace(text_from, text_to).strip()

        # Apply artist replacements
        for replacement in self.replace_in_artist:
            text_from = replacement.get("from", "")
            text_to = replacement.get("to", "")

            if artists and text_from in artists:
                artists = artists.replace(text_from, text_to).strip()

        return title, artists

    def _print_track_changes(self, track: Track) -> None:
        """Print detailed information about track changes."""
        title = track.enhanced_title or track.title
        title_changed = track.original_title != title
        artist_changed = track.original_artists != track.artists

        if title_changed or artist_changed:
            if title_changed and artist_changed:
                print(
                    f"Updating title '{track.title}' to '{title}' "
                    f"and artists '{track.artists}' to '{track.artists}'"
                )
            elif title_changed:
                print(f"Updating title '{track.title}' to '{title}'")
            elif artist_changed:
                print(
                    f"Updating '{track.title}' artists '{track.original_artists}'"
                    f" to '{track.artists}'"
                )

    def _split_artists_by_title(self, title: str, artists: str) -> Tuple[str, str]:
        """Split artists into those not in title and those in title."""
        if not artists:
            return "", ""

        # Split multiple artists
        artists_not_in_title = []
        artists_in_title = []

        for artist in [a.strip() for a in artists.split(",")]:
            if artist in title:
                artists_in_title.append(artist)
            else:
                artists_not_in_title.append(artist)

        # Only return filtered artists if some remain
        not_in_title_str = ", ".join(artists_not_in_title) if artists_not_in_title else artists
        in_title_str = ", ".join(artists_in_title)

        return not_in_title_str, in_title_str

    def _format_enhanced_title(self, title: str, artists: str, key: Optional[str]) -> str:
        """Format the final enhanced title based on configuration flags."""
        # Start with cleaned title
        enhanced_title = title

        # Add artists if enabled and present
        if artists and self.add_artist_to_title:
            enhanced_title = f"{enhanced_title} - {artists}"

        # Add key if enabled and present
        if key and self.add_key_to_title:
            enhanced_title = f"{enhanced_title} [{key}]"

        return enhanced_title

    def set_original_titles(self, collection) -> None:
        """
        Set original_title and original_artists by de-enhancing the loaded titles.
        This should be called after loading from database but before processing.
        """
        # Use the existing get_all_tracks method to get all unique tracks
        all_tracks = collection.get_all_tracks()
        
        for track in all_tracks:
            # De-enhance the title and artists to set as originals
            clean_title = self._clean_title(track.title, track.artists)
            clean_artists = track.artists  # Artists don't need de-enhancement in this case

            track.original_title = clean_title
            track.original_artists = clean_artists

    def _clean_title(self, title: str, artists: str) -> str:
        """
        De-enhance a title by removing artist suffixes and key brackets.
        Uses smart matching - removes " - xxx" when xxx contains ANY of the individual artists.
        """
        if not title or not " - " in title:
            return title
        
        clean_title = title
        
        # Split artist field into individual artists if provided
        individual_artists = []
        if artists:
            # Split on common separators: comma, &, feat, ft, featuring
            artists_split = re.split(r',\s*|&\s*|\s+feat\.?\s+|\s+ft\.?\s+|\s+featuring\s+', artists)
            individual_artists = [a.strip() for a in artists_split if a.strip()]
        
        # Keep removing patterns from the end
        while True:
            changed = False
            
            # Pattern 1: Remove " - anything [Key]" at the end
            end_with_key = r'^(.+) - (.+?) \[([A-G][#b]?/?[m]?)\]$'
            match = re.match(end_with_key, clean_title)
            if match:
                suffix_part = match.group(2).strip()
                # Check if the suffix appears in any individual artist OR matches the full artist field
                should_remove = False
                
                # Check individual artists
                for artist in individual_artists:
                    if suffix_part.lower() in artist.lower():
                        should_remove = True
                        break
                
                # Check full artist field (case-insensitive)
                if not should_remove and artists and suffix_part.lower() == artists.lower():
                    should_remove = True
                
                if should_remove:
                    clean_title = match.group(1)
                    changed = True
                    continue
            
            # Pattern 2: Remove " - anything" if the suffix appears in ANY artist
            end_pattern = r'^(.+) - (.+?)$'
            match = re.match(end_pattern, clean_title)
            if match:
                suffix_part = match.group(2).strip()
                # Check if the suffix appears in any individual artist OR matches the full artist field
                should_remove = False
                
                # Check individual artists
                for artist in individual_artists:
                    if suffix_part.lower() in artist.lower():
                        should_remove = True
                        break
                
                # Check full artist field (case-insensitive)
                if not should_remove and artists and suffix_part.lower() == artists.lower():
                    should_remove = True
                
                if should_remove:
                    clean_title = match.group(1)
                    changed = True
                    continue
            
            # No more changes, break
            if not changed:
                break
        
        return clean_title.strip()

    def check_for_duplicates(self, tracks: List[Track]) -> None:
        """Check for duplicate tracks by title AND artists and print warnings."""
        track_signatures: dict[str, List[Track]] = {}

        for track in tracks:
            # Use enhanced_title if available, otherwise fall back to title
            title = track.enhanced_title or track.title
            artists = track.artists or ""

            # Create a signature combining title and artists for better duplicate detection
            signature = f"{title}|{artists}".lower().strip()

            if signature not in track_signatures:
                track_signatures[signature] = []
            track_signatures[signature].append(track)

        # Report duplicates
        for signature, duplicate_tracks in track_signatures.items():
            if len(duplicate_tracks) > 1:
                title, artists = signature.split("|", 1)
                if artists:
                    print(
                        f"WARNING: {len(duplicate_tracks)} duplicate tracks found: "
                        f"'{title}' by '{artists}'"
                    )
                else:
                    print(
                        f"WARNING: {len(duplicate_tracks)} duplicate tracks found: "
                        f"'{title}' (no artist)"
                    )
                for track in duplicate_tracks:
                    print(f"  - Track ID: {track.id}")
