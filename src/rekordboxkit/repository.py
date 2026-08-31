"""
Rekordbox library repository.

Domain operations over pyrekordbox. No filesystem copy. Writes need confirm.
"""

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from pyrekordbox.db6.tables import DjmdSongMyTag

from .criteria import (
    FOLDER_SEARCH_FIELDS,
    HISTORY_FOLDER_SEARCH_FIELDS,
    HISTORY_SESSION_SEARCH_FIELDS,
    PLAYLIST_SEARCH_FIELDS,
    SMART_SEARCH_FIELDS,
    TRACK_SEARCH_FIELDS,
    Criteria,
    validate_criteria,
)
from .domain import (
    HistoryFolder,
    HistorySession,
    MutationResult,
    Playlist,
    PlaylistFolder,
    SmartPlaylist,
    Track,
    TreeNode,
)
from .encodings import (
    UNCONFIRMED_WRITE_FIELDS,
    WRITABLE_TRACK_FIELDS,
    encode_rating,
    probe_raw_content,
)
from .errors import (
    EntityNotFoundError,
    FolderNotEmptyError,
    RekordboxRunningError,
    UnconfirmedFieldError,
    ValidationError,
    WrongEntityTypeError,
)
from .mapping import (
    ATTR_FOLDER,
    entity_kind,
    history_kind,
    map_folder,
    map_history_folder,
    map_history_session,
    map_playlist,
    map_smart_playlist,
    map_track,
    parent_id_of,
)
from .search import (
    filter_folders,
    filter_history_folders,
    filter_history_sessions,
    filter_playlists,
    filter_smart_playlists,
    filter_tracks,
)
from .session import RekordboxSession
from .smartlist_codec import criteria_to_smartlist, smartlist_to_criteria

_MISSING = object()


def _query_call(result: Any, name: str) -> Any:
    """Call a real query method; ignore unittest.mock auto-attributes."""
    method = getattr(type(result), name, None)
    if not callable(method):
        return _MISSING
    return method(result)


def _rows(result: Any) -> List[Any]:
    """Unwrap a pyrekordbox query into a list of rows."""
    if result is None:
        return []
    if isinstance(result, (list, tuple)):
        return list(result)
    queried = _query_call(result, "all")
    if queried is not _MISSING:
        return list(queried)
    return [result]


def _first(result: Any) -> Any:
    """Unwrap a pyrekordbox query or scalar into one row."""
    if result is None:
        return None
    if isinstance(result, (list, tuple)):
        return result[0] if result else None
    for name in ("one_or_none", "first"):
        value = _query_call(result, name)
        if value is not _MISSING:
            return value
    queried = _query_call(result, "all")
    if queried is not _MISSING:
        return queried[0] if queried else None
    return result


def _as_id(value: str) -> Any:
    """Prefer integer IDs when the string is numeric."""
    return int(value) if str(value).isdigit() else value


class RekordboxRepository:  # pylint: disable=too-many-public-methods
    """Read and update Rekordbox library entities."""

    def __init__(
        self,
        session: RekordboxSession,
        path_exists: Optional[Callable[[str], bool]] = None,
    ):
        """Create a repository. path_exists is injected for tests."""
        self._session = session
        self._path_exists = path_exists or (lambda path: Path(path).exists())

    def list_tree(self) -> List[TreeNode]:
        """Playlist tree as summary nodes."""
        by_id, _rows = self._playlist_index()
        children: Dict[Optional[str], List[Any]] = {}
        for row in by_id.values():
            parent = parent_id_of(row)
            children.setdefault(parent, []).append(row)
        for group in children.values():
            group.sort(key=lambda item: int(item.Seq or 0))
        return [self._tree_node(row, by_id, children) for row in children.get(None, [])]

    def list_history_tree(self) -> List[TreeNode]:
        """History tree as folder and session summaries."""
        by_id, _rows = self._history_index()
        children: Dict[Optional[str], List[Any]] = {}
        for row in by_id.values():
            parent = parent_id_of(row)
            children.setdefault(parent, []).append(row)
        for group in children.values():
            group.sort(key=lambda item: int(item.Seq or 0))
        return [
            self._tree_node(row, by_id, children, history_kind) for row in children.get(None, [])
        ]

    def get_playlist_folder(self, folder_id: str) -> PlaylistFolder:
        """Get a folder by id."""
        row, by_id = self._require_row(folder_id, "folder")
        return map_folder(row, by_id)

    def get_playlist(self, playlist_id: str) -> Playlist:
        """Get a curated playlist by id."""
        row, by_id = self._require_row(playlist_id, "playlist")
        tracks = self._tracks_for(row)
        return map_playlist(row, by_id, tracks)

    def get_smart_playlist(self, playlist_id: str) -> SmartPlaylist:
        """Get a smart playlist by id."""
        row, by_id = self._require_row(playlist_id, "smart_playlist")
        tracks = self._tracks_for(row)
        criteria = self._criteria_for(row)
        return map_smart_playlist(row, by_id, tracks, criteria)

    def get_track(self, track_id: str) -> Track:
        """Get a collection track by id."""
        content = _first(self._session.database().get_content(ID=_as_id(track_id)))
        if content is None:
            raise EntityNotFoundError(f"track not found: {track_id}")
        return map_track(content, self._path_exists)

    def get_history_folder(self, folder_id: str) -> HistoryFolder:
        """Get a history folder by id."""
        row, by_id = self._require_history_row(folder_id, "history_folder")
        return map_history_folder(row, by_id)

    def get_history(self, history_id: str) -> HistorySession:
        """Get a history session by id, with tracks in mix order."""
        row, by_id = self._require_history_row(history_id, "history_session")
        tracks = self._history_tracks_for(row)
        return map_history_session(row, by_id, tracks)

    def search_tracks(self, criteria: Criteria) -> List[Track]:
        """Search collection tracks by criteria."""
        validate_criteria(criteria, TRACK_SEARCH_FIELDS)
        tracks = [
            map_track(content, self._path_exists)
            for content in _rows(self._session.database().get_content())
        ]
        return filter_tracks(tracks, criteria)

    def search_playlist_folders(self, criteria: Criteria) -> List[PlaylistFolder]:
        """Search folders by their properties."""
        validate_criteria(criteria, FOLDER_SEARCH_FIELDS)
        by_id, rows = self._playlist_index()
        folders = [map_folder(row, by_id) for row in rows if entity_kind(row.Attribute) == "folder"]
        return filter_folders(folders, criteria)

    def search_playlists(self, criteria: Criteria) -> List[Playlist]:
        """Search curated playlists by their properties."""
        validate_criteria(criteria, PLAYLIST_SEARCH_FIELDS)
        by_id, rows = self._playlist_index()
        playlists = []
        for row in rows:
            if entity_kind(row.Attribute) != "playlist":
                continue
            tracks = self._tracks_for(row)
            playlists.append(map_playlist(row, by_id, tracks))
        return filter_playlists(playlists, criteria)

    def search_smart_playlists(self, criteria: Criteria) -> List[SmartPlaylist]:
        """Search smart playlists by name, path, folder, id, or position."""
        validate_criteria(criteria, SMART_SEARCH_FIELDS)
        by_id, rows = self._playlist_index()
        playlists = []
        for row in rows:
            if entity_kind(row.Attribute) != "smart_playlist":
                continue
            playlists.append(map_smart_playlist(row, by_id, [], self._criteria_for(row)))
        return filter_smart_playlists(playlists, criteria)

    def search_history_folders(self, criteria: Criteria) -> List[HistoryFolder]:
        """Search history folders by id, name, path, parent, or position."""
        validate_criteria(criteria, HISTORY_FOLDER_SEARCH_FIELDS)
        by_id, rows = self._history_index()
        folders = [
            map_history_folder(row, by_id)
            for row in rows
            if history_kind(row.Attribute) == "history_folder"
        ]
        return filter_history_folders(folders, criteria)

    def search_history_sessions(self, criteria: Criteria) -> List[HistorySession]:
        """Search history sessions by name, path, folder, date, or contained track."""
        validate_criteria(criteria, HISTORY_SESSION_SEARCH_FIELDS)
        by_id, rows = self._history_index()
        sessions = []
        for row in rows:
            if history_kind(row.Attribute) != "history_session":
                continue
            tracks = self._history_tracks_for(row)
            sessions.append(map_history_session(row, by_id, tracks))
        return filter_history_sessions(sessions, criteria)

    def create_playlist_folder(
        self,
        name: str,
        parent_id: Optional[str] = None,
        position: Optional[int] = None,
        confirm: bool = False,
    ) -> MutationResult:
        """Create a playlist folder."""
        diff = {
            "action": "create",
            "entity": "folder",
            "name": name,
            "parent_id": parent_id,
            "position": position,
        }
        if not confirm:
            return MutationResult(applied=False, diff=diff)
        self._ensure_writable()
        row = self._session.database().create_playlist_folder(
            name, parent=_as_id(parent_id) if parent_id else None, seq=position
        )
        self._session.commit()
        diff["id"] = str(row.ID)
        return MutationResult(applied=True, diff=diff)

    def update_playlist_folder(
        self,
        folder_id: str,
        patch: Dict[str, Any],
        confirm: bool = False,
    ) -> MutationResult:
        """Rename, move, or reorder a folder."""
        row, _by_id = self._require_row(folder_id, "folder")
        diff = self._playlist_patch_diff("folder", row, patch)
        if not confirm:
            return MutationResult(applied=False, diff=diff)
        self._apply_playlist_patch(row, patch)
        return MutationResult(applied=True, diff=diff)

    def delete_playlist_folder(
        self, folder_id: str, recursive: bool = False, confirm: bool = False
    ) -> MutationResult:
        """Delete a folder. Fails if it has children unless recursive."""
        row, by_id = self._require_row(folder_id, "folder")
        child_ids = [str(item.ID) for item in by_id.values() if parent_id_of(item) == folder_id]
        if child_ids and not recursive:
            raise FolderNotEmptyError("folder is not empty")
        diff = {"action": "delete", "entity": "folder", "id": folder_id, "recursive": recursive}
        if not confirm:
            return MutationResult(applied=False, diff=diff)
        self._ensure_writable()
        db = self._session.database()
        if recursive:
            self._delete_descendants(folder_id)
        db.delete_playlist(row)
        self._session.commit()
        return MutationResult(applied=True, diff=diff)

    def _delete_descendants(self, folder_id: str) -> None:
        """Delete child playlist objects depth-first."""
        by_id, _rows = self._playlist_index()
        db = self._session.database()
        for child in list(by_id.values()):
            if parent_id_of(child) == folder_id:
                child_id = str(child.ID)
                self._delete_descendants(child_id)
                db.delete_playlist(child)

    def create_playlist(  # pylint: disable=too-many-arguments
        self,
        name: str,
        folder_id: Optional[str] = None,
        position: Optional[int] = None,
        track_ids: Optional[List[str]] = None,
        confirm: bool = False,
    ) -> MutationResult:
        """Create a curated playlist."""
        track_ids = track_ids or []
        diff = {
            "action": "create",
            "entity": "playlist",
            "name": name,
            "folder_id": folder_id,
            "position": position,
            "track_ids": track_ids,
        }
        if not confirm:
            return MutationResult(applied=False, diff=diff)
        self._ensure_writable()
        db = self._session.database()
        row = db.create_playlist(
            name, parent=_as_id(folder_id) if folder_id else None, seq=position
        )
        for track_id in track_ids:
            db.add_to_playlist(row, _as_id(track_id))
        self._session.commit()
        diff["id"] = str(row.ID)
        return MutationResult(applied=True, diff=diff)

    def update_playlist(
        self, playlist_id: str, patch: Dict[str, Any], confirm: bool = False
    ) -> MutationResult:
        """Rename, move, reorder, or replace membership."""
        row, _by_id = self._require_row(playlist_id, "playlist")
        diff = self._playlist_patch_diff("playlist", row, patch)
        if "tracks" in patch:
            diff["tracks"] = patch["tracks"]
        if not confirm:
            return MutationResult(applied=False, diff=diff)
        self._apply_playlist_patch(row, patch)
        if "tracks" in patch:
            self._replace_membership(row, [str(item) for item in patch["tracks"]])
        return MutationResult(applied=True, diff=diff)

    def delete_playlist(self, playlist_id: str, confirm: bool = False) -> MutationResult:
        """Delete a curated playlist."""
        row, _by_id = self._require_row(playlist_id, "playlist")
        diff = {"action": "delete", "entity": "playlist", "id": playlist_id}
        if not confirm:
            return MutationResult(applied=False, diff=diff)
        self._ensure_writable()
        self._session.database().delete_playlist(row)
        self._session.commit()
        return MutationResult(applied=True, diff=diff)

    def create_smart_playlist(  # pylint: disable=too-many-arguments
        self,
        name: str,
        criteria: Criteria,
        folder_id: Optional[str] = None,
        position: Optional[int] = None,
        confirm: bool = False,
    ) -> MutationResult:
        """Create a smart playlist from criteria."""
        smart = criteria_to_smartlist(criteria, "0", self._tag_id_for_name, self._color_id_for_name)
        diff = {
            "action": "create",
            "entity": "smart_playlist",
            "name": name,
            "folder_id": folder_id,
            "position": position,
            "criteria": {"match": criteria.match, "conditions": len(criteria.conditions)},
        }
        if not confirm:
            return MutationResult(applied=False, diff=diff)
        self._ensure_writable()
        row = self._session.database().create_smart_playlist(
            name, smart, parent=_as_id(folder_id) if folder_id else None, seq=position
        )
        self._session.commit()
        diff["id"] = str(row.ID)
        return MutationResult(applied=True, diff=diff)

    def update_smart_playlist(
        self, playlist_id: str, patch: Dict[str, Any], confirm: bool = False
    ) -> MutationResult:
        """Rename, move, reorder, or replace criteria. Cannot edit result tracks."""
        if "tracks" in patch:
            raise ValidationError("smart playlist tracks are derived from criteria")
        row, _by_id = self._require_row(playlist_id, "smart_playlist")
        diff = self._playlist_patch_diff("smart_playlist", row, patch)
        if "criteria" in patch:
            diff["criteria"] = patch["criteria"]
        if not confirm:
            return MutationResult(applied=False, diff=diff)
        self._apply_playlist_patch(row, patch)
        if "criteria" in patch:
            criteria = patch["criteria"]
            if not isinstance(criteria, Criteria):
                raise ValidationError("criteria must be a Criteria object")
            smart = criteria_to_smartlist(
                criteria, str(row.ID), self._tag_id_for_name, self._color_id_for_name
            )
            row.SmartList = smart.to_xml()
            self._session.commit()
        return MutationResult(applied=True, diff=diff)

    def delete_smart_playlist(self, playlist_id: str, confirm: bool = False) -> MutationResult:
        """Delete a smart playlist."""
        row, _by_id = self._require_row(playlist_id, "smart_playlist")
        diff = {"action": "delete", "entity": "smart_playlist", "id": playlist_id}
        if not confirm:
            return MutationResult(applied=False, diff=diff)
        self._ensure_writable()
        self._session.database().delete_playlist(row)
        self._session.commit()
        return MutationResult(applied=True, diff=diff)

    def update_track(
        self, track_id: str, patch: Dict[str, Any], confirm: bool = False
    ) -> MutationResult:
        """Patch writable track properties."""
        content = _first(self._session.database().get_content(ID=_as_id(track_id)))
        if content is None:
            raise EntityNotFoundError(f"track not found: {track_id}")
        self._validate_track_patch(patch)
        diff = {"action": "update", "entity": "track", "id": track_id, "patch": patch}
        if not confirm:
            return MutationResult(applied=False, diff=diff)
        self._ensure_writable()
        self._apply_track_patch(content, patch)
        self._session.commit()
        return MutationResult(applied=True, diff=diff)

    def probe_encodings(self, track_id: str) -> Dict[str, Any]:
        """Read-only raw vs decoded encodings for a track."""
        content = _first(self._session.database().get_content(ID=_as_id(track_id)))
        if content is None:
            raise EntityNotFoundError(f"track not found: {track_id}")
        raw = {
            "BPM": getattr(content, "BPM", None),
            "Rating": getattr(content, "Rating", None),
            "FolderPath": getattr(content, "FolderPath", None),
            "FileNameL": getattr(content, "FileNameL", None),
            "FileType": getattr(content, "FileType", None),
            "BitRate": getattr(content, "BitRate", None),
            "DJPlayCount": getattr(content, "DJPlayCount", None),
            "ColorID": getattr(content, "ColorID", None),
        }
        return probe_raw_content(raw)

    def _tree_node(
        self,
        row: Any,
        by_id: Dict[str, Any],
        children: Dict[Optional[str], List[Any]],
        kind_fn: Callable[[int], str] = entity_kind,
    ) -> TreeNode:
        folder = map_folder(row, by_id)
        node = TreeNode(
            id=str(row.ID),
            name=row.Name or "",
            path=folder.path,
            entity=kind_fn(row.Attribute),
        )
        for child in children.get(str(row.ID), []):
            node.children.append(self._tree_node(child, by_id, children, kind_fn))
        return node

    def _playlist_index(self) -> tuple:
        db = self._session.database()
        rows = _rows(db.get_playlist())
        by_id = {str(row.ID): row for row in rows}
        return by_id, rows

    def _history_index(self) -> tuple:
        rows = _rows(self._session.database().get_history())
        by_id = {str(row.ID): row for row in rows}
        return by_id, rows

    def _require_row(self, entity_id: str, expected: str) -> tuple:
        by_id, _rows = self._playlist_index()
        row = by_id.get(str(entity_id))
        if row is None:
            raise EntityNotFoundError(f"{expected} not found: {entity_id}")
        kind = entity_kind(row.Attribute)
        if kind != expected:
            raise WrongEntityTypeError(f"{entity_id} is a {kind}, not a {expected}")
        return row, by_id

    def _require_history_row(self, entity_id: str, expected: str) -> tuple:
        by_id, _rows = self._history_index()
        row = by_id.get(str(entity_id))
        if row is None:
            raise EntityNotFoundError(f"{expected} not found: {entity_id}")
        kind = history_kind(row.Attribute)
        if kind != expected:
            raise WrongEntityTypeError(f"{entity_id} is a {kind}, not a {expected}")
        return row, by_id

    def _tracks_for(self, row: Any) -> List[Track]:
        if row.Attribute == ATTR_FOLDER:
            return []
        db = self._session.database()
        try:
            contents = db.get_playlist_contents(row).all()
        except AttributeError as exc:
            if "month" in str(exc).lower():
                return []
            raise
        return [map_track(content, self._path_exists) for content in contents]

    def _history_tracks_for(self, row: Any) -> List[Track]:
        db = self._session.database()
        songs = _rows(db.get_history_songs(HistoryID=row.ID))
        songs.sort(key=lambda item: int(item.TrackNo or 0))
        tracks = []
        for song in songs:
            content = getattr(song, "Content", None)
            if content is None:
                content_id = getattr(song, "ContentID", None)
                if content_id in (None, ""):
                    continue
                content = _first(db.get_content(ID=_as_id(str(content_id))))
            if content is None:
                continue
            tracks.append(map_track(content, self._path_exists))
        return tracks

    def _criteria_for(self, row: Any) -> Optional[Criteria]:
        xml = getattr(row, "SmartList", None)
        return smartlist_to_criteria(xml, self._tag_name_for_id, self._color_name_for_id)

    def _ensure_writable(self) -> None:
        if self._session.is_rekordbox_running:
            raise RekordboxRunningError("Rekordbox is currently running")

    def _playlist_patch_diff(self, entity: str, row: Any, patch: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "action": "update",
            "entity": entity,
            "id": str(row.ID),
            "name": patch.get("name", row.Name),
            "parent_id": patch.get("parent_id", patch.get("folder_id", parent_id_of(row))),
            "position": patch.get("position", int(row.Seq or 0)),
        }

    def _apply_playlist_patch(self, row: Any, patch: Dict[str, Any]) -> None:
        self._ensure_writable()
        db = self._session.database()
        if "name" in patch and patch["name"] != row.Name:
            db.rename_playlist(row, str(patch["name"]))
        new_parent = patch.get("parent_id", patch.get("folder_id", _SENTINEL))
        new_seq = patch.get("position", _SENTINEL)
        if new_parent is not _SENTINEL or new_seq is not _SENTINEL:
            parent = (
                None if new_parent is _SENTINEL else (_as_id(new_parent) if new_parent else None)
            )
            seq = None if new_seq is _SENTINEL else new_seq
            db.move_playlist(row, parent=parent, seq=seq)
        self._session.commit()

    def _replace_membership(self, row: Any, track_ids: List[str]) -> None:
        db = self._session.database()
        for song in _rows(db.get_playlist_songs(PlaylistID=row.ID)):
            db.remove_from_playlist(row, song)
        for track_id in track_ids:
            db.add_to_playlist(row, _as_id(track_id))
        self._session.commit()

    def _validate_track_patch(self, patch: Dict[str, Any]) -> None:
        if not patch:
            raise ValidationError("track patch is empty")
        for key in patch:
            if key in UNCONFIRMED_WRITE_FIELDS:
                raise UnconfirmedFieldError(
                    f"writing '{key}' is not enabled until encoding is confirmed"
                )
            if key not in WRITABLE_TRACK_FIELDS:
                raise ValidationError(f"track field '{key}' is not writable")

    def _apply_track_patch(self, content: Any, patch: Dict[str, Any]) -> None:
        db = self._session.database()
        if "title" in patch:
            content.Title = patch["title"]
        if "comments" in patch:
            content.Commnt = patch["comments"]
        if "rating" in patch:
            rating = patch["rating"]
            content.Rating = encode_rating(int(rating)) if rating is not None else None
        if "artist" in patch:
            self._set_artist(content, patch["artist"])
        if "album" in patch:
            content.Album = self._get_or_create_named(db.get_album, db.add_album, patch["album"])
        if "genre" in patch:
            content.Genre = self._get_or_create_named(db.get_genre, db.add_genre, patch["genre"])
        if "label" in patch:
            content.Label = self._get_or_create_named(db.get_label, db.add_label, patch["label"])
        if "color" in patch:
            content.Color = self._color_by_name(patch["color"])
        if "tags" in patch:
            self._set_tags(content, list(patch["tags"]))

    def _set_artist(self, content: Any, name: Optional[str]) -> None:
        db = self._session.database()
        if not name:
            content.Artist = None
            return
        if content.Artist:
            content.Artist.Name = name
            return
        content.Artist = self._get_or_create_named(db.get_artist, db.add_artist, name)

    def _get_or_create_named(self, getter: Callable, adder: Callable, name: Optional[str]) -> Any:
        if not name:
            return None
        existing = _first(getter(Name=name))
        if existing is not None:
            return existing
        return adder(name)

    def _color_by_name(self, name: Optional[str]) -> Any:
        if not name:
            return None
        db = self._session.database()
        for color in _rows(db.get_color()):
            comment = getattr(color, "Commnt", None) or getattr(color, "Name", None)
            if comment and str(comment).casefold() == str(name).casefold():
                return color
        raise ValidationError(f"unknown color '{name}'")

    def _set_tags(self, content: Any, names: List[str]) -> None:
        db = self._session.database()
        existing = list(getattr(content, "MyTags", None) or [])
        for link in existing:
            db.delete(link)
        for index, name in enumerate(names):
            tag = self._my_tag_by_name(name)
            link = DjmdSongMyTag(MyTagID=tag.ID, ContentID=content.ID, TrackNo=index)
            db.add(link)

    def _my_tag_by_name(self, name: str) -> Any:
        db = self._session.database()
        for tag in _rows(db.get_my_tag()):
            if tag.Name and str(tag.Name).casefold() == name.casefold():
                return tag
        raise ValidationError(f"unknown tag '{name}'")

    def _tag_id_for_name(self, name: str) -> str:
        return str(self._my_tag_by_name(name).ID)

    def _tag_name_for_id(self, tag_id: str) -> str:
        row = _first(self._session.database().get_my_tag(ID=_as_id(tag_id)))
        if row is None:
            return tag_id
        return row.Name or tag_id

    def _color_id_for_name(self, name: str) -> str:
        color = self._color_by_name(name)
        return str(color.ID)

    def _color_name_for_id(self, color_id: str) -> str:
        row = _first(self._session.database().get_color(ID=_as_id(color_id)))
        if row is None:
            return color_id
        return getattr(row, "Commnt", None) or getattr(row, "Name", None) or color_id


_SENTINEL = object()
