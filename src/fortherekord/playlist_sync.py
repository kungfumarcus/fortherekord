"""
Playlist synchronization between Rekordbox and Spotify.

Handles one-way sync from Rekordbox to Spotify with simple track matching.
"""

from typing import Dict, List
import click

from .models import Playlist, Track, Collection
from .rekordbox_library import RekordboxLibrary
from .spotify_library import SpotifyLibrary


class PlaylistSyncService:  # pylint: disable=too-few-public-methods
    """Synchronizes playlists from Rekordbox to Spotify."""

    def __init__(self, rekordbox: RekordboxLibrary, spotify: SpotifyLibrary):
        """Initialize with library adapters."""
        self.rekordbox = rekordbox
        self.spotify = spotify

    def sync_collection(self, collection: Collection, dry_run: bool = False) -> None:
        """
        Sync playlists from a Collection to Spotify.

        Args:
            collection: Collection with playlists and tracks already loaded and filtered
            dry_run: If True, preview changes without making them
        """
        if dry_run:
            click.echo("🔍 DRY RUN MODE - Previewing changes without making them")
            click.echo()

        click.echo("Loading Spotify playlists...")
        spotify_playlists = self.spotify.get_playlists()
        spotify_playlist_map = {p.name: p for p in spotify_playlists}

        action_verb = "Previewing" if dry_run else "Syncing"
        click.echo(f"{action_verb} {len(collection.playlists)} playlists to Spotify")

        for rekordbox_playlist in collection.playlists:
            self._sync_single_playlist(rekordbox_playlist, spotify_playlist_map, dry_run)

        if dry_run:
            click.echo()
            click.echo("🔍 DRY RUN COMPLETE - No changes were made to Spotify")
            click.echo("   Run without --dry-run to apply these changes")

    def _sync_single_playlist(
        self,
        rekordbox_playlist: Playlist,
        spotify_playlist_map: Dict[str, Playlist],
        dry_run: bool = False,
    ) -> None:
        """
        Sync a single playlist from Rekordbox to Spotify.

        Args:
            rekordbox_playlist: Source playlist from Rekordbox (with tracks already loaded)
            spotify_playlist_map: Map of existing Spotify playlists by name
            dry_run: If True, preview changes without making them
        """
        playlist_name = rekordbox_playlist.name
        action_verb = "Previewing" if dry_run else "Syncing"
        click.echo(f"\\n{action_verb} playlist: {playlist_name}")

        # Get tracks from the playlist (already loaded in Collection)
        rekordbox_tracks = rekordbox_playlist.tracks
        click.echo(f"  Found {len(rekordbox_tracks)} tracks in Rekordbox")

        # Find matching tracks on Spotify
        matched_tracks = self._find_spotify_matches(rekordbox_tracks, dry_run)
        click.echo(f"  Matched {len(matched_tracks)} tracks on Spotify")

        if playlist_name in spotify_playlist_map:
            # Update existing playlist
            self._update_spotify_playlist(
                spotify_playlist_map[playlist_name], matched_tracks, dry_run
            )
        else:
            # Create new playlist
            self._create_spotify_playlist(playlist_name, matched_tracks, dry_run)

    def _find_spotify_matches(
        self, rekordbox_tracks: List[Track], dry_run: bool = False
    ) -> List[str]:
        """
        Find Spotify track IDs for Rekordbox tracks using simple search.

        Args:
            rekordbox_tracks: List of tracks from Rekordbox
            dry_run: If True, preview matches without detailed search output

        Returns:
            List of Spotify track IDs that were found
        """
        spotify_track_ids = []

        for track in rekordbox_tracks:
            # Simple search: title + artists, take first result
            spotify_id = self.spotify.search_track(track.title, track.artists)
            if spotify_id:
                spotify_track_ids.append(spotify_id)
            elif not dry_run:  # Only show detailed failures when not in dry-run
                click.echo(f"    ✗ No match: {track.title} - {track.artists}")

        return spotify_track_ids

    def _create_spotify_playlist(
        self, name: str, track_ids: List[str], dry_run: bool = False
    ) -> None:
        """
        Create a new Spotify playlist with tracks.

        Args:
            name: Playlist name
            track_ids: List of Spotify track IDs to add
            dry_run: If True, preview creation without making changes
        """
        if dry_run:
            click.echo(f"  📝 Would create new playlist '{name}' with {len(track_ids)} tracks")
            return

        click.echo("  Creating new Spotify playlist...")

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

        click.echo(f"  ✓ Created playlist with {len(track_ids)} tracks")

    def _update_spotify_playlist(
        self, spotify_playlist: Playlist, track_ids: List[str], dry_run: bool = False
    ) -> None:
        """
        Update existing Spotify playlist to match Rekordbox tracks.

        Args:
            spotify_playlist: Existing Spotify playlist
            track_ids: List of Spotify track IDs that should be in playlist
            dry_run: If True, preview changes without making them
        """
        if dry_run:
            click.echo(f"  📝 Would update existing playlist '{spotify_playlist.name}'")
            # Get current tracks for comparison
            current_tracks = self.spotify.get_playlist_tracks(spotify_playlist.id)
            current_track_ids = {track.id for track in current_tracks}
            new_track_ids = set(track_ids)

            # Calculate differences
            tracks_to_add = new_track_ids - current_track_ids
            tracks_to_remove = current_track_ids - new_track_ids

            click.echo(f"      Would add {len(tracks_to_add)} tracks")
            click.echo(f"      Would remove {len(tracks_to_remove)} tracks")
            return

        click.echo("  Updating existing Spotify playlist...")

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

        click.echo(
            f"  ✓ Updated playlist: +{len(tracks_to_add)} tracks, -{len(tracks_to_remove)} tracks"
        )

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
