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
        # Use list format for replace_in_title: [{"from": "old", "to": "new"}, ...]
        self.replace_in_title = config.get("replace_in_title", [])

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
        # Check if any enhancement features are enabled
        if not (self.add_key_to_title or self.add_artist_to_title):
            # No enhancements configured, return without changes
            return

        # Clean up whitespace
        track.title = re.sub(r"\s+", " ", track.title).strip()
        if track.artists:
            track.artists = re.sub(r"\s+", " ", track.artists).strip()

        # Remove artists suffix if already present in title
        if track.artists:
            track.title = self._remove_artist_suffixes(track.title, track.artists)

        # Extract artists from title if artists field is empty
        # (do this early, before other processing)
        if track.artists == "" and " - " in track.title:
            title_parts = track.title.split(" - ")
            if len(title_parts) == 2:
                extracted_artist = title_parts[1].strip()
                track.title = title_parts[0].strip()
                track.artists = extracted_artist
                print(f"Set artist name for '{track.title}' to '{extracted_artist}'")

        # Remove existing key suffix if present
        track.title = re.sub(r"\s\[..?.?\]$", "", track.title)

        # Apply configured text replacements
        track.title, track.artists = self._apply_text_replacements(track.title, track.artists)

        # Build enhanced title based on configuration
        artists_not_in_title = track.artists
        if track.artists and self.remove_artists_in_title:
            artists_not_in_title, _ = self._split_artists_by_title(track.title, track.artists)
        track.title = self._format_enhanced_title(track.title, artists_not_in_title, track.key)

        # Print detailed change information
        self._print_track_changes(track)

    def _apply_text_replacements(self, title: str, artists: str) -> Tuple[str, str]:
        """Apply configured text replacements to title and artists."""
        # List format: [{"from": "old", "to": "new"}, ...]
        for replacement in self.replace_in_title:
            text_from = replacement.get("from", "")
            text_to = replacement.get("to", "")

            if text_from in title:
                title = title.replace(text_from, text_to).strip()

            if artists and text_from in artists:
                artists = artists.replace(text_from, text_to).strip()

        return title, artists

    def _print_track_changes(self, track: Track) -> None:
        """Print detailed information about track changes."""
        title_changed = track.original_title != track.title
        artist_changed = track.original_artists != track.artists

        if title_changed or artist_changed:
            if title_changed and artist_changed:
                print(
                    f"Updating title '{track.original_title}' to '{track.title}' "
                    f"and artists '{track.original_artists}' to '{track.artists}'"
                )
            elif title_changed:
                print(f"Updating title '{track.original_title}' to '{track.title}'")
            # Note: Artist-only changes are currently not possible due to title enhancement logic
            # elif artist_changed:
            #     print(f"Updating '{original_title}' artists '{original_artists}' "
            #           f"to '{new_artist}'")

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

    def _remove_artist_suffixes(self, title: str, artists: str) -> str:
        """
        Remove artist suffixes from title, repeating until no more changes are made.

        Args:
            title: The track title
            artists: The artists string

        Returns:
            Title with artist suffixes removed
        """
        if not artists or " - " not in title:
            return title

        # Get the last part after the final " - "
        title_parts = title.split(" - ")
        last_part = title_parts[-1]

        # Remove key suffix from last part for comparison
        last_part_no_key = re.sub(r"\s\[..?.?\]$", "", last_part)

        # Split last part by comma and check if any artist matches
        last_part_artists = [a.strip() for a in last_part_no_key.split(",")]
        track_artists = [a.strip() for a in artists.split(",")]

        # If any artist from the track appears in the last part, remove the suffix
        if any(artist in track_artists for artist in last_part_artists):
            return " - ".join(title_parts[:-1])

        return title

    def check_for_duplicates(self, tracks: List[Track]) -> None:
        """Check for duplicate track titles and print warnings."""
        title_counts: dict[str, int] = {}

        for track in tracks:
            title = track.title
            title_counts[title] = title_counts.get(title, 0) + 1

        for title, count in title_counts.items():
            if count > 1:
                print(f"WARNING: Duplicate track found: {title}")
