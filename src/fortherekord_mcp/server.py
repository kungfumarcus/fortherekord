"""
Rekordbox MCP server.

Stdio tools over rekordboxkit. Does not copy files.
"""

import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

from fortherekord.config import load_config
from rekordboxkit.criteria import criteria_from_dict
from rekordboxkit.domain import Criteria, MutationResult
from rekordboxkit.errors import RekordboxKitError
from rekordboxkit.repository import RekordboxRepository
from rekordboxkit.serialize import (
    folder_dict,
    history_folder_dict,
    history_session_dict,
    history_session_summary,
    playlist_dict,
    playlist_summary,
    smart_playlist_dict,
    smart_playlist_summary,
    track_dict,
    track_summary,
    tree_list,
)
from rekordboxkit.session import RekordboxSession

logging.basicConfig(stream=sys.stderr, level=logging.INFO)
mcp = FastMCP("rekordbox")

_repository: Optional[RekordboxRepository] = None  # pylint: disable=invalid-name


def get_repository() -> RekordboxRepository:
    """Lazy repository bound to the configured master.db."""
    global _repository  # pylint: disable=global-statement
    if _repository is None:
        config = load_config()
        library_path = (config.get("rekordbox") or {}).get("library_path")
        if not library_path:
            raise RuntimeError("rekordbox.library_path not configured")
        session = RekordboxSession(Path(library_path))
        _repository = RekordboxRepository(session)
    return _repository


def set_repository(repository: Optional[RekordboxRepository]) -> None:
    """Replace the repository (tests)."""
    global _repository  # pylint: disable=global-statement
    _repository = repository


def _error(exc: Exception) -> Dict[str, str]:
    return {"error": str(exc)}


def _mutation(result: MutationResult) -> Dict[str, Any]:
    return {"applied": result.applied, "diff": result.diff}


def _criteria(match: str, conditions: List[Dict[str, Any]]) -> Criteria:
    return criteria_from_dict({"match": match, "conditions": conditions})


@mcp.tool()
def list_tree() -> Any:
    """Playlist tree summaries: folders, playlists, and smart playlists."""
    try:
        return tree_list(get_repository().list_tree())
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return _error(exc)


@mcp.tool()
def get_playlist_folder(folder_id: str) -> Any:
    """Get a playlist folder by id."""
    try:
        return folder_dict(get_repository().get_playlist_folder(folder_id))
    except RekordboxKitError as exc:
        return _error(exc)


@mcp.tool()
def get_playlist(playlist_id: str) -> Any:
    """Get a curated playlist by id, including track summaries."""
    try:
        return playlist_dict(get_repository().get_playlist(playlist_id))
    except RekordboxKitError as exc:
        return _error(exc)


@mcp.tool()
def get_smart_playlist(playlist_id: str) -> Any:
    """Get a smart playlist by id, including criteria and result tracks."""
    try:
        return smart_playlist_dict(get_repository().get_smart_playlist(playlist_id))
    except RekordboxKitError as exc:
        return _error(exc)


@mcp.tool()
def get_track(track_id: str) -> Any:
    """Get a collection track by id."""
    try:
        return track_dict(get_repository().get_track(track_id))
    except RekordboxKitError as exc:
        return _error(exc)


@mcp.tool()
def search_tracks(match: str, conditions: List[Dict[str, Any]]) -> Any:
    """Search tracks by any track property (same criteria shape as smart playlists)."""
    try:
        tracks = get_repository().search_tracks(_criteria(match, conditions))
        return [track_summary(track) for track in tracks]
    except RekordboxKitError as exc:
        return _error(exc)


@mcp.tool()
def search_playlist_folders(match: str, conditions: List[Dict[str, Any]]) -> Any:
    """Search playlist folders by id, name, path, parent, or position."""
    try:
        folders = get_repository().search_playlist_folders(_criteria(match, conditions))
        return [folder_dict(folder) for folder in folders]
    except RekordboxKitError as exc:
        return _error(exc)


@mcp.tool()
def search_playlists(match: str, conditions: List[Dict[str, Any]]) -> Any:
    """Search curated playlists by id, name, path, folder, position, or contained track."""
    try:
        playlists = get_repository().search_playlists(_criteria(match, conditions))
        return [playlist_summary(playlist) for playlist in playlists]
    except RekordboxKitError as exc:
        return _error(exc)


@mcp.tool()
def search_smart_playlists(match: str, conditions: List[Dict[str, Any]]) -> Any:
    """Search smart playlists by id, name, path, folder, or position."""
    try:
        playlists = get_repository().search_smart_playlists(_criteria(match, conditions))
        return [smart_playlist_summary(playlist) for playlist in playlists]
    except RekordboxKitError as exc:
        return _error(exc)


@mcp.tool()
def list_history_tree() -> Any:
    """History tree summaries: folders and recorded sessions."""
    try:
        return tree_list(get_repository().list_history_tree())
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return _error(exc)


@mcp.tool()
def get_history_folder(folder_id: str) -> Any:
    """Get a history folder by id."""
    try:
        return history_folder_dict(get_repository().get_history_folder(folder_id))
    except RekordboxKitError as exc:
        return _error(exc)


@mcp.tool()
def get_history(history_id: str) -> Any:
    """Get a history session by id, including tracks in mix order."""
    try:
        return history_session_dict(get_repository().get_history(history_id))
    except RekordboxKitError as exc:
        return _error(exc)


@mcp.tool()
def search_history_folders(match: str, conditions: List[Dict[str, Any]]) -> Any:
    """Search history folders by id, name, path, parent, or position."""
    try:
        folders = get_repository().search_history_folders(_criteria(match, conditions))
        return [history_folder_dict(folder) for folder in folders]
    except RekordboxKitError as exc:
        return _error(exc)


@mcp.tool()
def search_history_sessions(match: str, conditions: List[Dict[str, Any]]) -> Any:
    """Search history sessions by id, name, path, folder, position, date, or contained track."""
    try:
        sessions = get_repository().search_history_sessions(_criteria(match, conditions))
        return [history_session_summary(session) for session in sessions]
    except RekordboxKitError as exc:
        return _error(exc)


@mcp.tool()
def create_playlist_folder(
    name: str,
    parent_id: Optional[str] = None,
    position: Optional[int] = None,
    confirm: bool = False,
) -> Any:
    """Create a playlist folder. Pass confirm=true to apply."""
    try:
        return _mutation(
            get_repository().create_playlist_folder(name, parent_id, position, confirm)
        )
    except RekordboxKitError as exc:
        return _error(exc)


@mcp.tool()
def update_playlist_folder(folder_id: str, patch: Dict[str, Any], confirm: bool = False) -> Any:
    """Rename, move, or reorder a folder. Pass confirm=true to apply."""
    try:
        return _mutation(get_repository().update_playlist_folder(folder_id, patch, confirm))
    except RekordboxKitError as exc:
        return _error(exc)


@mcp.tool()
def delete_playlist_folder(folder_id: str, recursive: bool = False, confirm: bool = False) -> Any:
    """Delete a folder. recursive deletes children. Pass confirm=true to apply."""
    try:
        return _mutation(get_repository().delete_playlist_folder(folder_id, recursive, confirm))
    except RekordboxKitError as exc:
        return _error(exc)


@mcp.tool()
def create_playlist(
    name: str,
    folder_id: Optional[str] = None,
    position: Optional[int] = None,
    track_ids: Optional[List[str]] = None,
    confirm: bool = False,
) -> Any:
    """Create a curated playlist. Pass confirm=true to apply."""
    try:
        return _mutation(
            get_repository().create_playlist(name, folder_id, position, track_ids, confirm)
        )
    except RekordboxKitError as exc:
        return _error(exc)


@mcp.tool()
def update_playlist(playlist_id: str, patch: Dict[str, Any], confirm: bool = False) -> Any:
    """Update playlist name, folder, position, or tracks. Pass confirm=true to apply."""
    try:
        return _mutation(get_repository().update_playlist(playlist_id, patch, confirm))
    except RekordboxKitError as exc:
        return _error(exc)


@mcp.tool()
def delete_playlist(playlist_id: str, confirm: bool = False) -> Any:
    """Delete a curated playlist. Pass confirm=true to apply."""
    try:
        return _mutation(get_repository().delete_playlist(playlist_id, confirm))
    except RekordboxKitError as exc:
        return _error(exc)


@mcp.tool()
def create_smart_playlist(
    name: str,
    match: str,
    conditions: List[Dict[str, Any]],
    folder_id: Optional[str] = None,
    position: Optional[int] = None,
    confirm: bool = False,
) -> Any:
    """Create a smart playlist from criteria. Pass confirm=true to apply."""
    try:
        return _mutation(
            get_repository().create_smart_playlist(
                name, _criteria(match, conditions), folder_id, position, confirm
            )
        )
    except RekordboxKitError as exc:
        return _error(exc)


@mcp.tool()
def update_smart_playlist(playlist_id: str, patch: Dict[str, Any], confirm: bool = False) -> Any:
    """Update smart playlist name, folder, position, or criteria. Pass confirm=true."""
    try:
        if "criteria" in patch and isinstance(patch["criteria"], dict):
            patch = dict(patch)
            patch["criteria"] = criteria_from_dict(patch["criteria"])
        return _mutation(get_repository().update_smart_playlist(playlist_id, patch, confirm))
    except RekordboxKitError as exc:
        return _error(exc)


@mcp.tool()
def delete_smart_playlist(playlist_id: str, confirm: bool = False) -> Any:
    """Delete a smart playlist. Pass confirm=true to apply."""
    try:
        return _mutation(get_repository().delete_smart_playlist(playlist_id, confirm))
    except RekordboxKitError as exc:
        return _error(exc)


@mcp.tool()
def update_track(track_id: str, patch: Dict[str, Any], confirm: bool = False) -> Any:
    """Patch writable track properties. Pass confirm=true to apply."""
    try:
        return _mutation(get_repository().update_track(track_id, patch, confirm))
    except RekordboxKitError as exc:
        return _error(exc)


def main() -> None:
    """Run the MCP server over stdio."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
