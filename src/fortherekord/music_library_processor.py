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
        # Support both dictionary and list formats for replace_in_title
        self.replace_in_title = config.get("replace_in_title", {})
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

        # Start with original values
        original_title = track.title.strip() if track.title else ""
        original_artist = track.artist.strip() if track.artist else ""

        title = original_title
        artist = original_artist
        key = track.key

        # Clean up whitespace
        title = re.sub(r"\s+", " ", title)
        if artist:
            artist = re.sub(r"\s+", " ", artist)

        # Remove existing key suffix if present
        title = re.sub(r"\s\[..?.?\]$", "", title)

        # Extract artist from title if artist field is empty
        if not artist and " - " in title:
            title_parts = title.split(" - ")
            if len(title_parts) >= 2:
                title = title_parts[0].strip()
                artist = title_parts[1].strip()

        # Apply configured text replacements
        title, artist = self._apply_text_replacements(title, artist)

        # Remove artist suffix if already present in title (do this early)
        if artist:
            artist_suffix = f" - {artist}"
            if title.endswith(artist_suffix):
                title = title[: -len(artist_suffix)]

        # Remove duplicate artists from title (only if enabled)
        if artist and self.remove_artists_in_title:
            artist = self._remove_duplicate_artists(title, artist)

        # Build enhanced title based on configuration
        enhanced_title = self._format_enhanced_title(title, artist, key)

        # Print detailed change information
        self._print_track_changes(original_title, enhanced_title, original_artist, artist)

        # Modify track in-place with enhanced metadata
        track.title = enhanced_title
        track.artist = artist

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

    def _print_track_changes(
        self,
        original_title: str,
        new_title: str,
        original_artist: str,
        new_artist: str,
    ) -> None:
        """Print detailed information about track changes."""
        title_changed = original_title != new_title
        artist_changed = original_artist != new_artist

        if not title_changed and not artist_changed:
            return  # No changes, don't print anything

        if title_changed and artist_changed:
            print(
                f"Updating title '{original_title}' to '{new_title}' "
                f"and artist '{original_artist}' to '{new_artist}'"
            )
        elif title_changed:
            print(f"Updating title '{original_title}' to '{new_title}'")
        # Note: Artist-only changes are currently not possible due to title enhancement logic
        # elif artist_changed:
        #     print(f"Updating '{original_title}' artist '{original_artist}' to '{new_artist}'")

    def _remove_duplicate_artists(self, title: str, artist: str) -> str:
        """
        Remove artist names that appear in title, keeping remaining artists.

        This matches the PowerShell logic:
        - Remove artist suffix from title temporarily for checking
        - Split artists by comma (with whitespace handling)
        - Only remove artists if some would remain
        - Return original artist if all would be removed
        """
        if not artist:
            return artist

        # Remove artist suffix temporarily to check for duplicates in base title
        # This matches PowerShell: $titleMinusArtist = $title.Replace(" - $artist", "")
        title_minus_artist = title.replace(f" - {artist}", "")

        # Split multiple artists by comma with whitespace normalization
        # This matches PowerShell: $artist -split '\s*,\s*'
        artists = [a.strip() for a in artist.split(",") if a.strip()]
        removed_artists = []
        retained_artists = []

        # Check each individual artist
        for individual_artist in artists:
            if individual_artist in title_minus_artist:
                removed_artists.append(individual_artist)
            else:
                retained_artists.append(individual_artist)

        # Only remove artists if some remain (PowerShell logic)
        # if ($removedArtists.Count -gt 0 -and $retainedArtists.Count -gt 0)
        if removed_artists and retained_artists:
            new_artist = ", ".join(retained_artists)
            removed_list = ", ".join(removed_artists)
            print(
                f"Removed artist(s) '{removed_list}' from title "
                f"'{title_minus_artist}' with artists '{new_artist}'"
            )
            return new_artist

        # Return original artist if no duplicates or all would be removed
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

    def extract_original_metadata(self, tracks: List[Track]) -> None:
        """
        Extract original title and artist from enhanced titles and update tracks directly.

        Args:
            tracks: List of Track objects to process
        """
        for track in tracks:
            title = track.title
            # Store artist for potential future use
            _ = track.artist

            # Extract key from brackets
            key_match = re.search(r"\s\[([^\]]+)\]$", title)
            if key_match:
                # Remove key from title (key extraction not implemented yet)
                title = title[: key_match.start()]

            # Extract artist after last " - "
            if " - " in title:
                # Extract the last artist first
                parts = title.rsplit(" - ", 1)
                original_artist = parts[1].strip() if len(parts) == 2 else ""

                # Remove all " - artist" patterns to get original title
                # This handles cases like "Title - Artist1 - Artist2 - Artist3"
                original_title = re.sub(r"( - [^-]+)+$", "", title)

                # Update the track's original values
                track.original_title = original_title
                track.original_artist = original_artist
            else:
                # No enhancement detected, use current values as original
                track.original_title = track.title
                track.original_artist = track.artist

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
