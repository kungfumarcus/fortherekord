"""
ForTheRekord - Synchronize Rekordbox DJ library with Spotify playlists.

A command-line application that provides additional functionality for
Rekordbox DJs, including track matching, playlist synchronization, and
artist following.
"""

try:
    from ._version import version as __version__
except ImportError:
    __version__ = "unknown"

__all__ = ["__version__"]
