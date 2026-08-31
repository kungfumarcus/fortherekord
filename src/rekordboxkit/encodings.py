"""
Decode Rekordbox storage encodings into domain values.

Writes for bpm and key are gated until a live probe confirms the encoding.
"""

from pathlib import Path
from typing import Any, Dict, FrozenSet, Optional

FILE_TYPE_NAMES = {
    0: "mp3",
    1: "mp3",
    4: "m4a",
    5: "flac",
    11: "wav",
    12: "aiff",
}

# Confirmed as straightforward columns or name lookups.
WRITABLE_TRACK_FIELDS: FrozenSet[str] = frozenset(
    {
        "title",
        "artist",
        "album",
        "genre",
        "label",
        "comments",
        "rating",
        "color",
        "tags",
    }
)

UNCONFIRMED_WRITE_FIELDS: FrozenSet[str] = frozenset({"key", "bpm"})

XML_RATING_STEPS = (0, 51, 102, 153, 204, 255)


def decode_bpm(raw: Any) -> Optional[float]:
    """
    Return BPM as a float.

    Values above 1000 are treated as hundredths (12800 -> 128.0).
    """
    if raw is None or raw == "":
        return None
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    if value > 1000:
        return round(value / 100.0, 2)
    return value


def encode_bpm(bpm: float) -> int:
    """Store BPM as hundredths, matching the common Rekordbox integer encoding."""
    return int(round(bpm * 100))


def decode_rating(raw: Any) -> Optional[int]:
    """Return rating as 0-5 stars."""
    if raw is None or raw == "":
        return None
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None
    if 0 <= value <= 5:
        return value
    if value in XML_RATING_STEPS:
        return XML_RATING_STEPS.index(value)
    if 0 <= value <= 255:
        return int(round(value / 51))
    return None


def encode_rating(rating: int) -> int:
    """Store rating as 0-5, the domain contract."""
    if rating < 0 or rating > 5:
        raise ValueError("rating must be 0-5")
    return rating


def decode_file_type(raw: Any) -> Optional[str]:
    """Map FileType int to a short name."""
    if raw is None or raw == "":
        return None
    try:
        return FILE_TYPE_NAMES.get(int(raw))
    except (TypeError, ValueError):
        return None


def decode_bitrate(raw: Any) -> Optional[int]:
    """Return bitrate in kbps. Values above 10000 are treated as bits per second."""
    if raw is None or raw == "":
        return None
    try:
        value = int(float(raw))
    except (TypeError, ValueError):
        return None
    if value <= 0:
        return None
    if value > 10000:
        return int(round(value / 1000.0))
    return value


def decode_play_count(raw: Any) -> Optional[int]:
    """Return DJPlayCount as a non-negative int. Rekordbox stores it as text."""
    if raw is None or raw == "":
        return None
    try:
        value = int(float(raw))
    except (TypeError, ValueError):
        return None
    if value < 0:
        return None
    return value


def resolve_location(folder_path: Optional[str], file_name: Optional[str]) -> Optional[str]:
    """
    Build an absolute file path.

    FolderPath is used as-is when it already looks like a file path.
    Otherwise it is joined with FileNameL.
    """
    folder = (folder_path or "").strip()
    name = (file_name or "").strip()
    if not folder and not name:
        return None
    if folder:
        path = Path(folder)
        if name and path.suffix:
            return str(path)
        if name:
            return str(path / name)
        return str(path)
    return name


def probe_raw_content(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compare raw storage values with decoded domain values.

    Used to confirm encodings against a live row without writing.
    """
    folder = raw.get("FolderPath")
    filename = raw.get("FileNameL")
    return {
        "raw": raw,
        "decoded": {
            "bpm": decode_bpm(raw.get("BPM")),
            "rating": decode_rating(raw.get("Rating")),
            "file_type": decode_file_type(raw.get("FileType")),
            "bitrate": decode_bitrate(raw.get("BitRate")),
            "play_count": decode_play_count(raw.get("DJPlayCount")),
            "location": resolve_location(
                str(folder) if folder is not None else None,
                str(filename) if filename is not None else None,
            ),
        },
    }
