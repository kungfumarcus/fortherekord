"""Helpers for reading fields from pyrekordbox content objects."""

from typing import Any, Optional


def artist_name(content: Any) -> str:
    """Return the artist name, or empty string if missing."""
    if content.Artist:
        return content.Artist.Name or ""
    return ""


def related_name(related: Any) -> Optional[str]:
    """Return Name from a related row, or None."""
    if related is None:
        return None
    name = getattr(related, "Name", None)
    if name:
        return str(name)
    return None


def key_name(content: Any) -> Optional[str]:
    """Return musical key as ScaleName or a plain string."""
    key = getattr(content, "Key", None)
    if key is None:
        return None
    scale = getattr(key, "ScaleName", None)
    if scale:
        return str(scale)
    if isinstance(key, str):
        return key
    return None


def color_name(content: Any) -> Optional[str]:
    """Return the track colour name from the related color row."""
    color = getattr(content, "Color", None)
    if color is None:
        return None
    comment = getattr(color, "Commnt", None) or getattr(color, "Name", None)
    if comment:
        return str(comment)
    return None
