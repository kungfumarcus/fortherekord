"""Helpers for reading fields from pyrekordbox content objects."""

from typing import Any, Optional

from .encodings import decode_play_count


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
    if isinstance(name, str) and name:
        return name
    return None


def related_or_attr(content: Any, relation: str, attr: str) -> Optional[str]:
    """Prefer a related row Name, then a plain string column."""
    name = related_name(getattr(content, relation, None))
    if name:
        return name
    direct = getattr(content, attr, None)
    if isinstance(direct, str) and direct:
        return direct
    return None


def release_year(content: Any) -> Optional[int]:
    """Return ReleaseYear as a positive int, or None if unset."""
    year = decode_play_count(getattr(content, "ReleaseYear", None))
    if not year:
        return None
    return year


def key_name(content: Any) -> Optional[str]:
    """Return musical key as ScaleName or a plain string."""
    key = getattr(content, "Key", None)
    if key is None:
        return None
    scale = getattr(key, "ScaleName", None)
    if isinstance(scale, str) and scale:
        return scale
    if isinstance(key, str):
        return key
    return None


def color_name(content: Any) -> Optional[str]:
    """Return the track colour name from the related color row."""
    color = getattr(content, "Color", None)
    if color is None:
        return None
    comment = getattr(color, "Commnt", None) or getattr(color, "Name", None)
    if isinstance(comment, str) and comment:
        return comment
    return None
