"""
Entry point for ForTheRekord when run as a module or by PyInstaller.

This allows the package to be run with 'python -m fortherekord'
and provides a clean entry point for PyInstaller.
"""

from fortherekord.main import cli

if __name__ == "__main__":
    cli()  # pylint: disable=no-value-for-parameter  # Click handles args
