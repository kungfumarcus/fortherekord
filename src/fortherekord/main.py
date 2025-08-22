"""
Basic CLI shell for ForTheRekord.

CLI application with Rekordbox metadata processing functionality.
"""

from typing import Dict, Optional

import click

from fortherekord import __version__
from .config import load_config as config_load_config, create_default_config, get_config_path
from .playlist_sync import PlaylistSyncService
from .rekordbox_library import RekordboxLibrary
from .rekordbox_metadata_processor import RekordboxMetadataProcessor
from .spotify_library import SpotifyLibrary


def load_config() -> Optional[Dict[str, str]]:
    """Load and validate configuration, creating default if needed."""
    config = config_load_config()

    if not config.get("rekordbox_library_path"):
        click.echo("Error: rekordbox_library_path not configured")
        click.echo("Creating default config file...")
        create_default_config()
        click.echo(f"Config created at: {get_config_path()}")
        click.echo("Please verify the database path and run again")
        return None

    return config


def load_library(library_path: str) -> RekordboxLibrary:
    """Create and validate RekordboxLibrary, including Rekordbox running check."""
    click.echo(f"Loading Rekordbox library from: {library_path}")

    # Create Rekordbox library
    rekordbox = RekordboxLibrary(library_path)

    # Connect to Rekordbox database (this triggers the Rekordbox running detection)
    rekordbox._get_database()  # pylint: disable=protected-access

    # Early validation: Check if Rekordbox is running and we need to save changes
    if rekordbox.is_rekordbox_running:
        click.echo("ERROR: Rekordbox is currently running.")
        click.echo("Please close Rekordbox completely before running ForTheRekord.")
        click.echo("This prevents database corruption during metadata updates.")
        raise RuntimeError("Rekordbox is currently running")

    return rekordbox


def initialize_processor(config: dict, tracks: list) -> RekordboxMetadataProcessor:
    """Create metadata processor and set original values on tracks."""
    processor = RekordboxMetadataProcessor(config)

    # Process tracks to extract original values from enhanced titles
    processor.extract_original_metadata(tracks)

    return processor


def get_collection_to_process(rekordbox: RekordboxLibrary, config: dict) -> tuple:
    """Get collection to process and display playlist hierarchy."""
    click.echo("Loading collection from playlists...")

    # Pass the full config to RekordboxLibrary, let it extract what it needs
    collection = rekordbox.get_collection(config)

    # Display playlist hierarchy in original Rekordbox order
    print("Processing playlists:")
    for playlist in collection.playlists:
        playlist.display_tree(1)

    # Get all tracks from the collection (automatically deduplicated)
    tracks = collection.get_all_tracks()

    return collection, tracks


def process_tracks(
    tracks: list, rekordbox: RekordboxLibrary, processor: RekordboxMetadataProcessor
) -> None:
    """Process track metadata, check for duplicates, and save changes."""
    click.echo()
    click.echo("Updating track metadata...")

    # Process each track to enhance titles (modifies tracks in-place)
    for track in tracks:
        processor.enhance_track_title(track)

    # Check for duplicates
    click.echo()
    click.echo("Checking for duplicates...")
    processor.check_for_duplicates(tracks)

    # Save changes and get actual count of modified tracks
    click.echo()
    click.echo("Saving changes to database...")
    saved_count = rekordbox.save_changes(tracks)

    if saved_count > 0:
        click.echo(f"Successfully updated {saved_count} tracks")
    else:
        click.echo("No changes needed")


@click.command()
@click.version_option(version=__version__)
def cli() -> None:  # pylint: disable=too-many-return-statements
    """
    ForTheRekord - Process Rekordbox track metadata.

    Enhances track titles to standardized format: "Title - Artist [Key]"
    """
    config = load_config()
    if not config:
        return

    try:
        rekordbox = load_library(config["rekordbox_library_path"])

        collection, tracks = get_collection_to_process(rekordbox, config)
        if not tracks:
            click.echo("No tracks found to process")
            return

        processor = initialize_processor(config, tracks)
        process_tracks(tracks, rekordbox, processor)

        # Sync Spotify - Authenticate with Spotify using OAuth
        try:
            if not config.get("spotify_client_id") or not config.get("spotify_client_secret"):
                click.echo("Spotify credentials not configured")
                click.echo(
                    f"Please add spotify_client_id and spotify_client_secret to {get_config_path()}"
                )
                return

            spotify = SpotifyLibrary(config["spotify_client_id"], config["spotify_client_secret"])
            click.echo(f"Authenticated with Spotify as user: {spotify.user_id}")

            # Sync playlists from Rekordbox to Spotify using the collection
            click.echo(f"Found {len(collection.playlists)} Rekordbox playlists to sync")

            # Use PlaylistSyncService to sync the playlists
            sync_service = PlaylistSyncService(rekordbox, spotify)
            sync_service.sync_collection(collection)

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
