"""
Basic CLI shell for ForTheRekord.

Simple entry point with help functionality to establish foundation.
"""

import click

from fortherekord import __version__


@click.group()
@click.version_option(version=__version__)
def cli() -> None:
    """
    ForTheRekord - Synchronize Rekordbox DJ library with Spotify playlists.

    A command-line application that provides additional functionality for
    Rekordbox DJs, including track matching, playlist synchronization, and
    artist following.
    """
    pass


@cli.command()
def sync() -> None:
    """Synchronize Rekordbox library with Spotify playlists."""
    click.echo("Sync functionality not yet implemented.")


if __name__ == "__main__":
    cli()  # pylint: disable=no-value-for-parameter  # Click handles args
