"""
Basic CLI shell for ForTheRekord.

CLI application with Rekordbox library loading functionality.
"""

import click

from fortherekord import __version__
from .config import load_config, create_default_config, get_config_path
from .rekordbox import RekordboxLibrary


@click.command()
@click.version_option(version=__version__)
def cli() -> None:
    """
    ForTheRekord - Synchronize Rekordbox DJ library with Spotify playlists.

    A command-line application that provides additional functionality for
    Rekordbox DJs, including track matching, playlist synchronization, and
    artist following.
    """
    # Load configuration
    config = load_config()

    if not config.get("rekordbox_library_path"):
        click.echo("Error: rekordbox_library_path not configured")
        click.echo("Creating default config file...")
        create_default_config()
        click.echo(f"Config created at: {get_config_path()}")
        click.echo("Please verify the database path and run again")
        return

    library_path = config["rekordbox_library_path"]
    click.echo(f"Loading Rekordbox playlists from: {library_path}")

    try:
        # Create Rekordbox library with configured database path
        rekordbox = RekordboxLibrary(library_path)
        playlists = rekordbox.get_playlists()
        click.echo(f"Found {len(playlists)} playlists:")

        for playlist in playlists:
            track_count = len(playlist.tracks)
            first_title = playlist.tracks[0].title if playlist.tracks else "No tracks"
            click.echo(f"{playlist.name} ({track_count}): {first_title}")

    except FileNotFoundError:
        click.echo("Error: Rekordbox database not found at configured path")
        click.echo(f"Please check the path in {get_config_path()}")
        return
    except (OSError, ValueError, ImportError) as e:
        click.echo(f"Error loading Rekordbox library: {e}")
        return

    click.echo("\nSpotify sync not yet implemented.")

    click.echo("\nSpotify sync not yet implemented.")


if __name__ == "__main__":
    cli()  # pylint: disable=no-value-for-parameter  # Click handles args
