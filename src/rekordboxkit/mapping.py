"""Map pyrekordbox rows onto domain types."""

from typing import Any, Callable, Dict, List, Optional

from .content import (
    artist_name,
    color_name,
    key_name,
    related_name,
    related_or_attr,
    release_year,
)
from .encodings import (
    decode_bitrate,
    decode_bpm,
    decode_file_type,
    decode_play_count,
    decode_rating,
    resolve_location,
)
from .domain import (
    HistoryFolder,
    HistorySession,
    Playlist,
    PlaylistFolder,
    SmartPlaylist,
    Track,
)

ATTR_PLAYLIST = 0
ATTR_FOLDER = 1
ATTR_SMART = 4


def entity_kind(attribute: int) -> str:
    """Map Rekordbox Attribute to a domain type name."""
    if attribute == ATTR_FOLDER:
        return "folder"
    if attribute == ATTR_SMART:
        return "smart_playlist"
    return "playlist"


def history_kind(attribute: int) -> str:
    """Map Rekordbox History Attribute to a domain type name."""
    if attribute == ATTR_FOLDER:
        return "history_folder"
    return "history_session"


def parent_id_of(row: Any) -> Optional[str]:
    """Return parent folder id, or None at the tree root."""
    parent = getattr(row, "Parent", None)
    if parent is None:
        return None
    identifier = str(parent.ID)
    if identifier in {"0", "root"}:
        return None
    return identifier


def date_str(value: Any) -> Optional[str]:
    """Format a date-like value as yyyy-mm-dd."""
    if value is None or value == "":
        return None
    strftime = getattr(value, "strftime", None)
    if callable(strftime):
        return str(strftime("%Y-%m-%d"))
    text = str(value)
    return text[:10] if text else None


def tag_names_of(content: Any) -> List[str]:
    """My Tag names on a content row."""
    names = getattr(content, "MyTagNames", None)
    if names:
        return [str(name) for name in names if name]
    tags = getattr(content, "MyTags", None)
    result = []
    if tags:
        for tag in tags:
            related = getattr(tag, "MyTag", None) or tag
            name = getattr(related, "Name", None)
            if name:
                result.append(str(name))
    return result


def map_track(content: Any, path_exists: Optional[Callable[[str], bool]] = None) -> Track:
    """Build a domain Track from DjmdContent.

    path_exists is omitted for search so the collection is not stat'd.
    """
    folder_path = getattr(content, "FolderPath", None)
    file_name = getattr(content, "FileNameL", None)
    location = resolve_location(
        str(folder_path) if folder_path else None,
        str(file_name) if file_name else None,
    )
    missing = False
    if location and path_exists is not None:
        missing = not path_exists(location)
    date_added = date_str(getattr(content, "StockDate", None)) or date_str(
        getattr(content, "DateCreated", None)
    )
    length = getattr(content, "Length", None)
    duration = int(float(str(length))) if length not in (None, "") else None
    return Track(
        id=str(content.ID),
        title=content.Title or "",
        artist=artist_name(content),
        album=related_name(getattr(content, "Album", None)),
        genre=related_name(getattr(content, "Genre", None)),
        label=related_name(getattr(content, "Label", None)),
        comments=getattr(content, "Commnt", None) or None,
        rating=decode_rating(getattr(content, "Rating", None)),
        color=color_name(content),
        tags=tag_names_of(content),
        key=key_name(content),
        bpm=decode_bpm(getattr(content, "BPM", None)),
        duration=duration,
        location=location,
        missing=missing,
        date_added=date_added,
        bitrate=decode_bitrate(getattr(content, "BitRate", None)),
        file_type=decode_file_type(getattr(content, "FileType", None)),
        play_count=decode_play_count(getattr(content, "DJPlayCount", None)),
        album_artist=related_or_attr(content, "AlbumArtist", "AlbumArtistName"),
        original_artist=related_or_attr(content, "OrgArtist", "OrgArtistName"),
        remixer=related_or_attr(content, "Remixer", "RemixerName"),
        composer=related_or_attr(content, "Composer", "ComposerName"),
        year=release_year(content),
        date_created=date_str(getattr(content, "DateCreated", None)),
        date_released=date_str(getattr(content, "ReleaseDate", None)),
    )


def build_path(row: Any, rows_by_id: Dict[str, Any]) -> str:
    """Full playlist path using ancestor names."""
    names = [row.Name or ""]
    current = parent_id_of(row)
    seen = set()
    while current and current not in seen:
        seen.add(current)
        parent_row = rows_by_id.get(current)
        if parent_row is None:
            break
        names.insert(0, parent_row.Name or "")
        current = parent_id_of(parent_row)
    return " / ".join(names)


def map_folder(row: Any, rows_by_id: Dict[str, Any]) -> PlaylistFolder:
    """Build a PlaylistFolder from a djmdPlaylist folder row."""
    return PlaylistFolder(
        id=str(row.ID),
        name=row.Name or "",
        parent_id=parent_id_of(row),
        position=int(row.Seq or 0),
        path=build_path(row, rows_by_id),
    )


def map_playlist(row: Any, rows_by_id: Dict[str, Any], tracks: List[Track]) -> Playlist:
    """Build a Playlist from a djmdPlaylist playlist row."""
    return Playlist(
        id=str(row.ID),
        name=row.Name or "",
        folder_id=parent_id_of(row),
        position=int(row.Seq or 0),
        path=build_path(row, rows_by_id),
        tracks=tracks,
    )


def map_history_folder(row: Any, rows_by_id: Dict[str, Any]) -> HistoryFolder:
    """Build a HistoryFolder from a djmdHistory folder row."""
    return HistoryFolder(
        id=str(row.ID),
        name=row.Name or "",
        parent_id=parent_id_of(row),
        position=int(row.Seq or 0),
        path=build_path(row, rows_by_id),
    )


def map_history_session(
    row: Any, rows_by_id: Dict[str, Any], tracks: List[Track]
) -> HistorySession:
    """Build a HistorySession from a djmdHistory session row."""
    return HistorySession(
        id=str(row.ID),
        name=row.Name or "",
        folder_id=parent_id_of(row),
        position=int(row.Seq or 0),
        path=build_path(row, rows_by_id),
        date=date_str(getattr(row, "DateCreated", None)),
        tracks=tracks,
    )


def map_smart_playlist(
    row: Any,
    rows_by_id: Dict[str, Any],
    tracks: List[Track],
    criteria: Any,
) -> SmartPlaylist:
    """Build a SmartPlaylist from a djmdPlaylist smart row."""
    return SmartPlaylist(
        id=str(row.ID),
        name=row.Name or "",
        folder_id=parent_id_of(row),
        position=int(row.Seq or 0),
        path=build_path(row, rows_by_id),
        tracks=tracks,
        criteria=criteria,
    )
