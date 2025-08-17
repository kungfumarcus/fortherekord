"""
Basic CLI shell for ForTheRekord.

CLI application with Rekordbox metadata processing functionality.
"""

import click

from fortherekord import __version__
from .config import load_config, create_default_config, get_config_path
from .rekordbox import RekordboxLibrary
from .rekordbox_metadata_processor import RekordboxMetadataProcessor


@click.command()
@click.version_option(version=__version__)
@click.option('--all-tracks', is_flag=True, help='Process all tracks instead of only playlist tracks')
def cli(all_tracks: bool) -> None:
    """
    ForTheRekord - Process Rekordbox track metadata.

    Enhances track titles to standardized format: "Title - Artist [Key]"
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
    click.echo(f"Loading Rekordbox library from: {library_path}")

    try:
        # Create Rekordbox library and metadata processor
        rekordbox = RekordboxLibrary(library_path)
        processor = RekordboxMetadataProcessor(config)
        
        # Get tracks based on --all-tracks flag
        if all_tracks:
            click.echo("Processing all tracks in collection...")
            tracks = rekordbox.get_all_tracks()
        else:
            click.echo("Processing tracks from playlists...")
            tracks = rekordbox.get_tracks_from_playlists(config.get("ignore_playlists", []))

        if not tracks:
            click.echo("No tracks found to process")
            return

        click.echo()
        click.echo("Updating track metadata...")
        
        # Process each track
        updated_count = 0
        for track in tracks:
            original_title = track.title
            enhanced_track = processor.enhance_track_title(track)
            
            if enhanced_track.title != original_title:
                success = rekordbox.update_track_metadata(
                    track.id, 
                    enhanced_track.title, 
                    enhanced_track.artist
                )
                if success:
                    updated_count += 1
                else:
                    click.echo(f"Failed to update track: {original_title}")

        # Check for duplicates
        click.echo()
        click.echo("Checking for duplicates...")
        enhanced_tracks = [processor.enhance_track_title(track) for track in tracks]
        processor.check_for_duplicates(enhanced_tracks)

        # Save changes
        if updated_count > 0:
            click.echo()
            click.echo("Saving changes to database...")
            if rekordbox.save_changes():
                click.echo(f"Successfully updated {updated_count} tracks")
            else:
                click.echo("Error: Failed to save changes")
        else:
            click.echo("No changes needed")

    except FileNotFoundError:
        click.echo("Error: Rekordbox database not found at configured path")
        click.echo(f"Please check the path in {get_config_path()}")
        return
    except (OSError, ValueError, ImportError) as e:
        click.echo(f"Error loading Rekordbox library: {e}")
        return


if __name__ == "__main__":
    cli()  # pylint: disable=no-value-for-parameter  # Click handles args
