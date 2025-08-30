"""
Playlist synchronization between Rekordbox and Spotify.

Handles one-way sync from Rekordbox to Spotify with simple track matching.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
import click

from .models import Playlist, Track, Collection
from .rekordbox_library import RekordboxLibrary
from .spotify_library import SpotifyLibrary
from .mapping_cache import MappingCache
from .cli_tools import cursor_up


@dataclass
class Progress:
    """Progress tracking for playlist synchronization."""

    current: int
    total: int

    def percentage(self) -> int:
        """Calculate current progress percentage."""
        return int((self.current - 1) / self.total * 100) if self.total > 0 else 0


class PlaylistSyncService:  # pylint: disable=too-few-public-methods
    """Synchronizes playlists from Rekordbox to Spotify."""

    def __init__(
        self,
        rekordbox: RekordboxLibrary,
        spotify: SpotifyLibrary,
        config: Optional[Dict] = None,
    ):
        """Initialize with library adapters."""
        self.rekordbox = rekordbox
        self.spotify = spotify

        # Check for mandatory playlist prefix from config
        if config is None:
            config = {}
        self.playlist_prefix = config.get("spotify", {}).get("playlist_prefix")
        if not self.playlist_prefix:
            raise ValueError("spotify.playlist_prefix is required in configuration but not found")

        # Get exclude patterns for playlist names
        self.exclude_from_playlist_names = config.get("spotify", {}).get(
            "exclude_from_playlist_names", []
        )

        # Initialize mapping cache
        self.mapping_cache = MappingCache()

    def sync_collection(self, collection: Collection, dry_run: bool = False) -> None:
        """
        Sync playlists from a Collection to Spotify.

        Args:
            collection: Collection with playlists and tracks already loaded and filtered
            dry_run: If True, preview changes without making them
        """
        if dry_run:
            click.echo("DRY RUN MODE - Previewing changes without making them")
            click.echo()

        click.echo("Loading Spotify playlists...")
        spotify_playlists = self.spotify.get_playlists()
        spotify_playlist_map = {p.name: p for p in spotify_playlists}

        # Process all playlists recursively (including children)
        all_playlists = self._get_all_playlists_recursive(collection.playlists)

        action_verb = "Previewing" if dry_run else "Syncing"
        click.echo(f"{action_verb} {len(all_playlists)} playlists to Spotify\n")

        # Use manual progress tracking with in-place updates
        for i, rekordbox_playlist in enumerate(all_playlists):
            progress = Progress(i + 1, len(all_playlists))
            self._sync_single_playlist(rekordbox_playlist, spotify_playlist_map, progress, dry_run)

        click.echo(" " * 40)
        click.echo("Overall [100%]")

        click.echo()  # Final newline

        if dry_run:
            click.echo("DRY RUN COMPLETE - No changes were made to Spotify")
            click.echo("   Run without --dry-run to apply these changes")

    def _sync_single_playlist(
        self,
        rekordbox_playlist: Playlist,
        spotify_playlist_map: Dict[str, Playlist],
        progress: Progress,
        dry_run: bool = False,
    ) -> None:
        """
        Sync a single playlist from Rekordbox to Spotify.

        Args:
            rekordbox_playlist: Source playlist from Rekordbox (with tracks already loaded)
            spotify_playlist_map: Map of existing Spotify playlists by name
            dry_run: If True, preview changes without making them
            progress: Progress tracking object for display (required)
        """
        # Apply mandatory prefix to create Spotify playlist name
        # First, clean the name by removing excluded terms
        spotify_name = self.playlist_prefix + self._clean_playlist_name(
            rekordbox_playlist.full_name()
        )

        # Initialize single-line display
        base_line = (
            f"({progress.current}/{progress.total}) "
            f"{rekordbox_playlist.full_name()} -> {spotify_name}"
        )

        # Show overall progress
        click.echo()
        click.echo(" " * 20)
        click.echo(f"Overall [{progress.percentage()}%]")
        click.echo(f"{cursor_up(4)}")

        # Find matching tracks with progress updates
        matched_tracks = self._find_spotify_matches(rekordbox_playlist.tracks, dry_run, base_line)

        # If no tracks matched on Spotify, delete the playlist if it exists, or skip creating it
        if len(matched_tracks) == 0:
            if spotify_name in spotify_playlist_map:
                playlist_obj = spotify_playlist_map[spotify_name]
                if dry_run:
                    result_text = f"{base_line} (0 matching tracks) - would delete"
                else:
                    result_text = f"{base_line} (0 matching tracks) - deleted"
                    if not self.spotify.sp or not self.spotify.user_id:
                        raise RuntimeError("Spotify client not authenticated")
                    self.spotify.sp.current_user_unfollow_playlist(playlist_obj.id)
            else:
                if dry_run:
                    result_text = f"{base_line} (0 matching tracks) - would skip"
                else:
                    result_text = f"{base_line} (0 matching tracks) - skipped"

            # Update the line with final result
            click.echo(f"\r{result_text}" + " " * 20)
            return

        if spotify_name in spotify_playlist_map:
            # Update existing playlist
            _tracks_added, _tracks_removed = self._update_spotify_playlist(
                spotify_playlist_map[spotify_name], matched_tracks, dry_run
            )
        else:
            # Create new playlist with prefix
            _tracks_added, _tracks_removed = self._create_spotify_playlist(
                spotify_name, matched_tracks, dry_run
            )

        click.echo(
            f"\r{base_line} ({len(matched_tracks)}/{len(rekordbox_playlist.tracks)}){" " * 5}"
        )

    def _find_spotify_matches(
        self,
        rekordbox_tracks: List[Track],
        dry_run: bool = False,
        base_line: str = "",
    ) -> List[str]:
        """
        Find Spotify track IDs for Rekordbox tracks using cached mappings and search.

        Args:
            rekordbox_tracks: List of tracks from Rekordbox
            dry_run: If True, preview matches without detailed search output
            base_line: Base line text for progress updates

        Returns:
            List of Spotify track IDs that were found
        """
        spotify_track_ids = []
        tracks_to_search = []
        cached_hits = 0

        # First pass: check cache for existing mappings
        for track in rekordbox_tracks:
            if not self.mapping_cache.should_remap(
                track.id, False
            ):  # Never force remap in this context
                cached_entry = self.mapping_cache.get_mapping(track.id)
                if cached_entry and cached_entry.target_track_id:
                    spotify_track_ids.append(cached_entry.target_track_id)
                    cached_hits += 1
                else:
                    # Cached as "not found" - skip API call but don't add to results
                    pass
            else:
                tracks_to_search.append(track)

        # Second pass: search for tracks not in cache
        if tracks_to_search:
            for i, track in enumerate(tracks_to_search):
                # Update progress in place
                total_processed = cached_hits + i + 1  # +1 because we're processing track i
                progress_percent = int((total_processed / len(rekordbox_tracks)) * 100)
                click.echo(f"\r{base_line} [{progress_percent}%]{cursor_up()}")

                spotify_id = self._search_and_cache_track(track, dry_run)
                if spotify_id:
                    spotify_track_ids.append(spotify_id)

        return spotify_track_ids

    def _search_and_cache_track(self, track: Track, dry_run: bool = False) -> Optional[str]:
        """
        Search for a single track and cache the result.

        Args:
            track: Rekordbox track to search for
            dry_run: If True, preview matches without detailed search output

        Returns:
            Spotify track ID if found, None otherwise
        """
        # Simple search: title + artists, take first result
        spotify_id = self.spotify.search_track(track.title, track.artists)

        # Cache the result (whether successful or not)
        confidence_score = 1.0 if spotify_id else 0.0
        self.mapping_cache.set_mapping(track.id, spotify_id, confidence_score)

        if not spotify_id and not dry_run:  # Only show detailed failures when not in dry-run
            click.echo(f"      X No match: {track.title} - {track.artists}")

        return spotify_id

    def _create_spotify_playlist(
        self, name: str, track_ids: List[str], dry_run: bool = False
    ) -> tuple[int, int]:
        """
        Create a new Spotify playlist with tracks.

        Args:
            name: Playlist name
            track_ids: List of Spotify track IDs to add
            dry_run: If True, preview creation without making changes

        Returns:
            Tuple of (tracks_added, tracks_removed)
        """
        if dry_run:
            return len(track_ids), 0

        if not self.spotify.sp or not self.spotify.user_id:
            raise RuntimeError("Spotify client not authenticated")

        # Create empty playlist
        playlist = self.spotify.sp.user_playlist_create(
            user=self.spotify.user_id, name=name, public=False
        )

        playlist_id = playlist["id"]

        # Add tracks in batches
        if track_ids:
            self._add_tracks_to_playlist(playlist_id, track_ids)

        return len(track_ids), 0

    def _update_spotify_playlist(
        self, spotify_playlist: Playlist, track_ids: List[str], dry_run: bool = False
    ) -> tuple[int, int]:
        """
        Update existing Spotify playlist to match Rekordbox tracks.

        Args:
            spotify_playlist: Existing Spotify playlist
            track_ids: List of Spotify track IDs that should be in playlist
            dry_run: If True, preview changes without making them

        Returns:
            Tuple of (tracks_added, tracks_removed)
        """
        if dry_run:
            # Get current tracks for comparison
            current_tracks = self.spotify.get_playlist_tracks(spotify_playlist.id)
            current_track_ids = {track.id for track in current_tracks}
            new_track_ids = set(track_ids)

            # Calculate differences
            tracks_to_add = new_track_ids - current_track_ids
            tracks_to_remove = current_track_ids - new_track_ids

            return len(tracks_to_add), len(tracks_to_remove)

        # Get current tracks
        current_tracks = self.spotify.get_playlist_tracks(spotify_playlist.id)
        current_track_ids = {track.id for track in current_tracks}
        new_track_ids = set(track_ids)

        # Calculate differences
        tracks_to_add = new_track_ids - current_track_ids
        tracks_to_remove = current_track_ids - new_track_ids

        # Remove tracks that shouldn't be there
        if tracks_to_remove:
            self._remove_tracks_from_playlist(spotify_playlist.id, list(tracks_to_remove))

        # Add new tracks
        if tracks_to_add:
            self._add_tracks_to_playlist(spotify_playlist.id, list(tracks_to_add))

        return len(tracks_to_add), len(tracks_to_remove)

    def _add_tracks_to_playlist(self, playlist_id: str, track_ids: List[str]) -> None:
        """Add tracks to playlist in batches."""
        if not self.spotify.sp:
            raise RuntimeError("Spotify client not authenticated")

        for i in range(0, len(track_ids), 100):  # Spotify API limit
            batch = track_ids[i : i + 100]
            self.spotify.sp.playlist_add_items(playlist_id, batch)

    def _remove_tracks_from_playlist(self, playlist_id: str, track_ids: List[str]) -> None:
        """Remove tracks from playlist in batches."""
        if not self.spotify.sp:
            raise RuntimeError("Spotify client not authenticated")

        for i in range(0, len(track_ids), 100):  # Spotify API limit
            batch = track_ids[i : i + 100]
            self.spotify.sp.playlist_remove_all_occurrences_of_items(playlist_id, batch)

    def _clean_playlist_name(self, name: str) -> str:
        """
        Clean playlist name by removing excluded terms.

        Args:
            name: Original playlist name

        Returns:
            Cleaned playlist name with excluded terms removed
        """
        cleaned_name = name
        for exclude_term in self.exclude_from_playlist_names:
            # Remove the term and any extra spaces that might result
            cleaned_name = cleaned_name.replace(exclude_term, "").strip()
            # Clean up multiple spaces
            while "  " in cleaned_name:
                cleaned_name = cleaned_name.replace("  ", " ")

        return cleaned_name

    def _get_all_playlists_recursive(self, playlists: List[Playlist]) -> List[Playlist]:
        """
        Get all playlists including children recursively.

        Args:
            playlists: Top-level playlists

        Returns:
            Flattened list of all playlists including children (excluding those with excluded terms)
        """
        all_playlists = []
        for playlist in playlists:
            # Skip playlists that contain excluded terms
            should_skip = False
            for exclude_term in self.exclude_from_playlist_names:
                if exclude_term.lower() in playlist.name.lower():
                    should_skip = True
                    break

            if not should_skip:
                # Only include playlists that have tracks (not empty folders)
                if len(playlist.tracks) > 0:
                    all_playlists.append(playlist)

            # Recursively add children (regardless of whether parent was skipped)
            if playlist.children:
                all_playlists.extend(self._get_all_playlists_recursive(playlist.children))

        return all_playlists
