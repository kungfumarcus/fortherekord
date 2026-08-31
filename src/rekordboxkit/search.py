"""Match Criteria against domain entities."""

# pylint: disable=duplicate-code

import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from .domain import (
    Condition,
    Criteria,
    HistoryFolder,
    HistorySession,
    Playlist,
    PlaylistFolder,
    SmartPlaylist,
    Track,
)


def matches_criteria(values: Dict[str, Any], criteria: Criteria, path_prefix: bool = True) -> bool:
    """Return True if values satisfy criteria. path_prefix uses folder-aware starts_with."""
    results = [
        _match_condition(values, condition, path_prefix) for condition in criteria.conditions
    ]
    if criteria.match == "any":
        return any(results)
    return all(results)


def track_values(track: Track) -> Dict[str, Any]:
    """Property map for track search, including filename derived from location."""
    filename = None
    if track.location:
        filename = Path(track.location).name
    return {
        "title": track.title,
        "artist": track.artist,
        "album": track.album,
        "genre": track.genre,
        "label": track.label,
        "comments": track.comments,
        "key": track.key,
        "filename": filename,
        "tags": track.tags,
        "bpm": track.bpm,
        "rating": track.rating,
        "duration": track.duration,
        "color": track.color,
        "location": track.location,
        "missing": track.missing,
        "date_added": track.date_added,
        "bitrate": track.bitrate,
        "file_type": track.file_type,
        "play_count": track.play_count,
    }


def folder_values(folder: PlaylistFolder) -> Dict[str, Any]:
    """Property map for folder search."""
    return {
        "id": folder.id,
        "name": folder.name,
        "path": folder.path,
        "parent": folder.parent_id,
        "position": folder.position,
    }


def playlist_values(playlist: Playlist) -> Dict[str, Any]:
    """Property map for playlist search."""
    return {
        "id": playlist.id,
        "name": playlist.name,
        "path": playlist.path,
        "folder": playlist.folder_id,
        "position": playlist.position,
        "track": [track.id for track in playlist.tracks],
    }


def smart_values(playlist: SmartPlaylist) -> Dict[str, Any]:
    """Property map for smart playlist search (not criteria body)."""
    return {
        "id": playlist.id,
        "name": playlist.name,
        "path": playlist.path,
        "folder": playlist.folder_id,
        "position": playlist.position,
    }


def history_folder_values(folder: HistoryFolder) -> Dict[str, Any]:
    """Property map for history folder search."""
    return {
        "id": folder.id,
        "name": folder.name,
        "path": folder.path,
        "parent": folder.parent_id,
        "position": folder.position,
    }


def history_session_values(session: HistorySession) -> Dict[str, Any]:
    """Property map for history session search."""
    return {
        "id": session.id,
        "name": session.name,
        "path": session.path,
        "folder": session.folder_id,
        "position": session.position,
        "date": session.date,
        "track": [track.id for track in session.tracks],
    }


def _match_condition(  # pylint: disable=too-many-return-statements
    values: Dict[str, Any], condition: Condition, path_prefix: bool
) -> bool:
    actual = values.get(condition.field)
    operator = condition.operator
    expected = condition.value

    if operator == "is":
        return _equals(actual, expected)
    if operator == "is_not":
        return not _equals(actual, expected)
    if operator == "contains":
        return _contains(actual, expected)
    if operator == "not_contains":
        return not _contains(actual, expected)
    if operator == "starts_with":
        if condition.field == "location" and path_prefix:
            return _location_starts_with(actual, expected)
        return _text(actual).startswith(_text(expected))
    if operator == "ends_with":
        return _text(actual).endswith(_text(expected))
    if operator == "greater":
        actual_n = _number(actual)
        expected_n = _number(expected)
        return actual_n is not None and expected_n is not None and actual_n > expected_n
    if operator == "less":
        actual_n = _number(actual)
        expected_n = _number(expected)
        return actual_n is not None and expected_n is not None and actual_n < expected_n
    if operator == "between" and isinstance(expected, dict):
        number = _number(actual)
        low = _number(expected.get("min"))
        high = _number(expected.get("max"))
        return number is not None and low is not None and high is not None and low <= number <= high
    if operator in {"in_last", "not_in_last"} and isinstance(expected, dict):
        in_window = _in_last(actual, expected)
        return in_window if operator == "in_last" else not in_window
    return False


def _equals(actual: Any, expected: Any) -> bool:
    if isinstance(actual, bool) or isinstance(expected, bool):
        return bool(actual) is _as_bool(expected)
    if isinstance(actual, list):
        return _text(expected) in [_text(item) for item in actual]
    if actual is None:
        return expected is None or expected == ""
    if _number(actual) is not None and _number(expected) is not None:
        if not isinstance(actual, str) and not isinstance(expected, str):
            return _number(actual) == _number(expected)
    return _text(actual) == _text(expected)


def _contains(actual: Any, expected: Any) -> bool:
    needle = _text(expected)
    if isinstance(actual, list):
        return any(needle in _text(item) or needle == _text(item) for item in actual)
    return needle in _text(actual)


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).casefold()


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes"}
    return bool(value)


def _number(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _location_starts_with(location: Any, prefix: Any) -> bool:
    if not location or not prefix:
        return False
    loc = os.path.normcase(os.path.normpath(str(location)))
    pre = os.path.normcase(os.path.normpath(str(prefix)))
    return loc == pre or loc.startswith(pre + os.sep)


def _in_last(actual: Any, period: Dict[str, Any]) -> bool:
    if not actual:
        return False
    try:
        parsed = datetime.strptime(str(actual)[:10], "%Y-%m-%d")
    except ValueError:
        return False
    amount = int(period["amount"])
    unit = str(period["unit"])
    delta = timedelta(days=amount) if unit == "day" else timedelta(weeks=amount)
    return parsed >= datetime.now() - delta


def filter_tracks(tracks: List[Track], criteria: Criteria) -> List[Track]:
    """Filter tracks by criteria."""
    return [track for track in tracks if matches_criteria(track_values(track), criteria)]


def filter_folders(folders: List[PlaylistFolder], criteria: Criteria) -> List[PlaylistFolder]:
    """Filter folders by criteria."""
    return [item for item in folders if matches_criteria(folder_values(item), criteria)]


def filter_playlists(playlists: List[Playlist], criteria: Criteria) -> List[Playlist]:
    """Filter playlists by criteria."""
    return [item for item in playlists if matches_criteria(playlist_values(item), criteria)]


def filter_smart_playlists(
    playlists: List[SmartPlaylist], criteria: Criteria
) -> List[SmartPlaylist]:
    """Filter smart playlists by name/path/folder/id/position."""
    return [item for item in playlists if matches_criteria(smart_values(item), criteria)]


def filter_history_folders(folders: List[HistoryFolder], criteria: Criteria) -> List[HistoryFolder]:
    """Filter history folders by their properties."""
    return [item for item in folders if matches_criteria(history_folder_values(item), criteria)]


def filter_history_sessions(
    sessions: List[HistorySession], criteria: Criteria
) -> List[HistorySession]:
    """Filter history sessions by name/path/folder/id/position/date/track."""
    return [item for item in sessions if matches_criteria(history_session_values(item), criteria)]
