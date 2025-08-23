"""
Music library processing functionality.

Handles title enhancement, artist processing, and text replacements
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
        self.ignore_playlists = config.get("ignore_playlists", [])

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
        if not (self.add_key_to_title or self.add_artist_to_title or self.remove_artists_in_title):
            # No enhancements configured, return without changes
            return

        # Start with original values (extracted from enhanced titles)

        key = track.key

        # Clean up whitespace
        track.title = re.sub(r"\s+", " ", track.title).strip()
        if track.artist:
            track.artist = re.sub(r"\s+", " ", track.artist).strip()

        # Remove existing key suffix if present
        track.title = re.sub(r"\s\[..?.?\]$", "", track.title)

        # Extract artist from title if artist field is empty
        if not track.artist and " - " in track.title:
            title_parts = track.title.split(" - ")
            if len(title_parts) >= 2:
                track.title = title_parts[0].strip()
                track.artist = title_parts[1].strip()

        # Apply configured text replacements
        track.title, track.artist = self._apply_text_replacements(track.title, track.artist)

        # Remove artist suffix if already present in title (do this early)
        if track.artist:
            artist_suffix = f" - {track.artist}"
            if track.title.endswith(artist_suffix):
                track.title = track.title[: -len(artist_suffix)]

        # Remove duplicate artists from title (only if enabled)
        if track.artist and self.remove_artists_in_title:
            track.artist = self._remove_duplicate_artists(track.title, track.artist)

        # Build enhanced title based on configuration
        track.title = self._format_enhanced_title(track.title, track.artist, key)

        # Print detailed change information
        self._print_track_changes(track)

    def _apply_text_replacements(self, title: str, artist: str) -> Tuple[str, str]:
        """Apply configured text replacements to title and artist."""
        # List format: [{"from": "old", "to": "new"}, ...]
        for replacement in self.replace_in_title:
            text_from = replacement.get("from", "")
            text_to = replacement.get("to", "")

            if text_from in title:
                title = title.replace(text_from, text_to).strip()

            if artist and text_from in artist:
                artist = artist.replace(text_from, text_to).strip()

        return title, artist

    def _print_track_changes(self, track: Track) -> None:
        """Print detailed information about track changes."""
        title_changed = track.original_title != track.title
        artist_changed = track.original_artist != track.artist

        if title_changed or artist_changed:
            if title_changed and artist_changed:
                print(
                    f"Updating title '{track.original_title}' to '{track.title}' "
                    f"and artist '{track.original_artist}' to '{track.artist}'"
                )
            elif title_changed:
                print(f"Updating title '{track.original_title}' to '{track.title}'")
            # Note: Artist-only changes are currently not possible due to title enhancement logic
            # elif artist_changed:
            #     print(f"Updating '{original_title}' artist '{original_artist}' to '{new_artist}'")

    def _remove_duplicate_artists(self, title: str, artist: str) -> str:
        """Remove artist names that appear in title, keeping remaining artists."""
        if not artist:
            return artist

        # Split multiple artists
        artists = [a.strip() for a in artist.split(",")]
        removed_artists = []
        retained_artists = []

        for individual_artist in artists:
            if individual_artist in title:
                removed_artists.append(individual_artist)
            else:
                retained_artists.append(individual_artist)

        # Only remove if some artists remain
        if removed_artists and retained_artists:
            return ", ".join(retained_artists)

        return artist

    def _format_enhanced_title(self, title: str, artist: str, key: Optional[str]) -> str:
        """Format the final enhanced title based on configuration flags."""
        # Start with cleaned title
        enhanced_title = title

        # Add artist if enabled and present
        if artist and self.add_artist_to_title:
            enhanced_title = f"{enhanced_title} - {artist}"

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

    def should_ignore_playlist(self, playlist_name: str) -> bool:
        """Check if playlist should be ignored based on configuration."""
        return playlist_name in self.ignore_playlists
