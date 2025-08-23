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
            artists_for_title = track.artists
            if self.remove_artists_in_title:
                artists_for_title = self._get_artists_not_in_title(track.title, track.artists)
            artists_suffix = f" - {artists_for_title}"
            if track.title.endswith(artists_suffix):
                track.title = track.title[: -len(artists_suffix)]
            else:
                artists_suffix = f"{artists_suffix} [{track.key}]"
                if track.title.endswith(artists_suffix):
                    track.title = track.title[: -len(artists_suffix)]

        # Extract artists from title if artists field is empty
        # (do this early, before other processing)
        if not track.artists and " - " in track.title:
            title_parts = track.title.split(" - ")
            if len(title_parts) >= 2:
                extracted_artist = title_parts[1].strip()
                track.title = title_parts[0].strip()
                track.artists = extracted_artist
                print(f"Set artist name for '{track.title}' to '{extracted_artist}'")

        # Remove existing key suffix if present
        track.title = re.sub(r"\s\[..?.?\]$", "", track.title)

        # Apply configured text replacements
        track.title, track.artists = self._apply_text_replacements(track.title, track.artists)

        # Determine artists to include in title
        artists_for_title = track.artists
        if track.artists and self.remove_artists_in_title:
            artists_for_title = self._get_artists_not_in_title(track.title, track.artists)

        # Build enhanced title based on configuration
        artists_for_title = track.artists
        if track.artists and self.remove_artists_in_title:
            artists_for_title = self._get_artists_not_in_title(track.title, track.artists)
        track.title = self._format_enhanced_title(track.title, artists_for_title, track.key)

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

    def _get_artists_not_in_title(self, title: str, artists: str) -> str:
        """Get artists that don't appear in title, for adding to enhanced title."""
        if not artists:
            return artists

        # Split multiple artists
        removed_artists = []
        retained_artists = []

        for artist in [a.strip() for a in artists.split(",")]:
            if artist in title:
                removed_artists.append(artist)
            else:
                retained_artists.append(artist)

        # Only remove if some artists remain
        if retained_artists:
            artists = ", ".join(retained_artists)

        return artists

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

    def check_for_duplicates(self, tracks: List[Track]) -> None:
        """Check for duplicate track titles and print warnings."""
        title_counts: dict[str, int] = {}

        for track in tracks:
            title = track.title
            title_counts[title] = title_counts.get(title, 0) + 1

        for title, count in title_counts.items():
            if count > 1:
                print(f"WARNING: Duplicate track found: {title}")
