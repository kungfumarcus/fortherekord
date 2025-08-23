"""
Basic CLI shell for ForTheRekord.

CLI application with Rekordbox metadata processing functionality.
"""

from typing import Dict, Optional, Any

import click

from fortherekord import __version__
from .config import load_config as config_load_config, create_default_config, get_config_path
from .models import Collection
from .music_library import MusicLibrary
from .playlist_sync import PlaylistSyncService
from .rekordbox_library import RekordboxLibrary
from .music_library_processor import MusicLibraryProcessor
from .spotify_library import SpotifyLibrary


def load_config() -> Optional[Dict[str, Any]]:
    """Load and validate configuration, creating default if needed."""
    config = config_load_config()

    # Support both old flat structure and new hierarchical structure
    # Check if rekordbox library path is configured
    if "rekordbox" not in config or not config["rekordbox"].get("library_path"):
        click.echo("Error: rekordbox library_path not configured")
        click.echo("Creating default config file...")
        create_default_config()
        click.echo(f"Config created at: {get_config_path()}")
        click.echo("Please verify the database path and run again")
        return None

    return config


def load_library(config: Dict[str, Any], dry_run: bool = False) -> RekordboxLibrary:
    """Create and validate RekordboxLibrary, including Rekordbox running check."""
    library_path = config["rekordbox"]["library_path"]
    click.echo(f"Loading Rekordbox library from: {library_path}")

    # Create Rekordbox library
    rekordbox = RekordboxLibrary(config)

    # Connect to Rekordbox database (this triggers the Rekordbox running detection)
    rekordbox._get_database()  # pylint: disable=protected-access

    # Early validation: Check if Rekordbox is running and we need to save changes
    # Skip this check in dry-run mode since we won't be making any changes
    if rekordbox.is_rekordbox_running and not dry_run:
        click.echo("ERROR: Rekordbox is currently running.")
        click.echo("Please close Rekordbox completely before running ForTheRekord.")
        click.echo("This prevents database corruption during metadata updates.")
        raise RuntimeError("Rekordbox is currently running")

    if rekordbox.is_rekordbox_running and dry_run:
        click.echo(
            "Note: Rekordbox is running, but continuing in dry-run mode (no changes will be made)"
        )

    return rekordbox


def initialize_processor(config: dict) -> Optional[MusicLibraryProcessor]:
    """Create music library processor and set original values on tracks."""
    processor = MusicLibraryProcessor(config)

    # Check if all enhancement features are disabled
    if not (
        processor.add_key_to_title
        or processor.add_artist_to_title
        or processor.remove_artists_in_title
    ):
        click.echo("Music library processor is disabled (all enhancement features are turned off)")
        click.echo("Enable features in config.yaml under processor section:")
        click.echo("  add_key_to_title: true")
        click.echo("  add_artist_to_title: true")
        click.echo("  remove_artists_in_title: true")
        return None

    return processor


def get_collection_to_process(rekordbox: RekordboxLibrary) -> Collection:
    """Get collection to process and display playlist hierarchy."""
    # Use get_filtered_collection to apply ignore_playlists filtering
    collection = rekordbox.get_filtered_collection()

    # Get all tracks from the collection (automatically deduplicated)
    tracks = collection.get_all_tracks()

    # Count all playlists recursively (excluding folders)
    def count_non_folder_playlists(playlists: list) -> int:
        count = 0
        for playlist in playlists:
            # Count this playlist if it has tracks (not a folder)
            if len(playlist.tracks) > 0:
                count += 1
            # Recursively count children
            if playlist.children:
                count += count_non_folder_playlists(playlist.children)
        return count

    total_playlists = count_non_folder_playlists(collection.playlists)

    # Display summary with counts
    print(f"Loaded {total_playlists} playlists with {len(tracks)} tracks:")
    for playlist in collection.playlists:
        playlist.display_tree(1)

    return collection


def process_tracks(
    collection: Collection,
    music_library: MusicLibrary,
    processor: MusicLibraryProcessor,
    dry_run: bool = False,
) -> None:
    """Process track library, check for duplicates, and save changes."""
    print("Processing playlist metadata...")

    if dry_run:
        click.echo()
        click.echo("DRY RUN MODE - Previewing track metadata changes")
    else:
        click.echo()
        click.echo("Updating track metadata...")

    # Get all tracks from the collection
    tracks = collection.get_all_tracks()

    # Process each track to enhance titles (modifies tracks in-place)
    click.echo()
    for track in tracks:
        processor.process_track(track)

    # Check for duplicates
    click.echo()
    click.echo("Checking for duplicates...")
    processor.check_for_duplicates(tracks)

    # Get tracks that actually have changes
    changed_tracks = collection.get_changed_tracks()

    # Save changes and get actual count of modified tracks
    click.echo()
    if dry_run:
        click.echo("Would save changes to database...")
        # Count how many tracks would be modified without calling save_changes
        modified_count = len(changed_tracks)
        if modified_count > 0:
            click.echo(f"Would update {modified_count} tracks")
        else:
            click.echo("No changes needed")
    else:
        click.echo("Saving changes to database...")
        # Only save tracks that actually have changes
        saved_count = music_library.save_changes(changed_tracks)
        if saved_count > 0:
            click.echo(f"Successfully updated {saved_count} tracks")
        else:
            click.echo("No changes needed")


@click.command()
@click.version_option(version=__version__)
@click.option("--dry-run", is_flag=True, help="Preview changes without making them")
def cli(dry_run: bool) -> None:  # pylint: disable=too-many-return-statements
    """
    ForTheRekord - Process Rekordbox track metadata.

    Enhances track titles to standardized format: "Title - Artist [Key]"
    """
    config = load_config()
    if not config:
        return

    try:
        rekordbox = load_library(config, dry_run)

        collection = get_collection_to_process(rekordbox)

        # Check if there are any tracks to process
        if not collection.get_all_tracks():
            click.echo("No tracks found to process")
            return

        processor_config = config.get("processor", {})
        processor = initialize_processor(processor_config)

        # Only process tracks if processor is enabled
        if processor is not None:
            process_tracks(collection, rekordbox, processor, dry_run)
        else:
            click.echo("Skipping track processing (processor is disabled)")
            click.echo("No changes needed")

        # Sync Spotify - Authenticate with Spotify using OAuth
        try:
            spotify_config = config.get("spotify", {})
            if not spotify_config.get("client_id") or not spotify_config.get("client_secret"):
                click.echo("Spotify credentials not configured")
                click.echo(f"Please add spotify client_id and client_secret to {get_config_path()}")
                return

            spotify = SpotifyLibrary(spotify_config["client_id"], spotify_config["client_secret"])
            click.echo(f"Authenticated with Spotify as user: {spotify.user_id}")

            # Sync playlists from Rekordbox to Spotify using the collection
            click.echo(f"Found {len(collection.playlists)} Rekordbox playlists to sync")

            # Use PlaylistSyncService to sync the playlists
            sync_service = PlaylistSyncService(rekordbox, spotify)
            sync_service.sync_collection(collection, dry_run=dry_run)

            click.echo("Spotify playlist sync complete.")
        except (ValueError, ConnectionError, OSError) as e:
            click.echo(f"Failed to authenticate with Spotify: {e}")
            return

    except RuntimeError:
        # Rekordbox running error already handled in load_library
        return
    except FileNotFoundError:
        click.echo("Error: Rekordbox database not found at configured path")
        click.echo(f"Please check the path in {get_config_path()}")
        return
    except (OSError, ValueError, ImportError) as e:
        click.echo(f"Error loading Rekordbox library: {e}")
        return


if __name__ == "__main__":
    cli()  # pylint: disable=no-value-for-parameter  # Click handles args
