"""JSON-friendly dicts for MCP tool results."""

# pylint: disable=duplicate-code

from typing import Any, Dict, List

from .criteria import criteria_to_dict
from .domain import (
    HistoryFolder,
    HistorySession,
    Playlist,
    PlaylistFolder,
    SmartPlaylist,
    Track,
    TreeNode,
)


def track_summary(track: Track) -> Dict[str, Any]:
    """Small track payload for lists and search."""
    return {
        "id": track.id,
        "title": track.title,
        "artist": track.artist,
        "key": track.key,
        "bpm": track.bpm,
        "location": track.location,
        "missing": track.missing,
    }


def track_dict(track: Track) -> Dict[str, Any]:
    """Full track payload."""
    return {
        "id": track.id,
        "title": track.title,
        "artist": track.artist,
        "album": track.album,
        "genre": track.genre,
        "label": track.label,
        "comments": track.comments,
        "rating": track.rating,
        "color": track.color,
        "tags": list(track.tags),
        "key": track.key,
        "bpm": track.bpm,
        "duration": track.duration,
        "location": track.location,
        "missing": track.missing,
        "date_added": track.date_added,
        "bitrate": track.bitrate,
        "file_type": track.file_type,
        "play_count": track.play_count,
        "album_artist": track.album_artist,
        "original_artist": track.original_artist,
        "remixer": track.remixer,
        "composer": track.composer,
        "year": track.year,
        "date_created": track.date_created,
        "date_released": track.date_released,
    }


def folder_dict(folder: PlaylistFolder) -> Dict[str, Any]:
    """PlaylistFolder payload."""
    return {
        "id": folder.id,
        "name": folder.name,
        "parent_id": folder.parent_id,
        "position": folder.position,
        "path": folder.path,
    }


def history_folder_dict(folder: HistoryFolder) -> Dict[str, Any]:
    """HistoryFolder payload."""
    return {
        "id": folder.id,
        "name": folder.name,
        "parent_id": folder.parent_id,
        "position": folder.position,
        "path": folder.path,
    }


def history_session_summary(session: HistorySession) -> Dict[str, Any]:
    """HistorySession search payload without tracks."""
    return {
        "id": session.id,
        "name": session.name,
        "folder_id": session.folder_id,
        "position": session.position,
        "path": session.path,
        "date": session.date,
    }


def history_session_dict(session: HistorySession) -> Dict[str, Any]:
    """HistorySession payload with ordered track summaries."""
    payload = history_session_summary(session)
    payload["tracks"] = [track_summary(track) for track in session.tracks]
    return payload


def playlist_summary(playlist: Playlist) -> Dict[str, Any]:
    """Playlist search payload without tracks."""
    return {
        "id": playlist.id,
        "name": playlist.name,
        "folder_id": playlist.folder_id,
        "position": playlist.position,
        "path": playlist.path,
    }


def playlist_dict(playlist: Playlist) -> Dict[str, Any]:
    """Playlist payload with track summaries."""
    payload = playlist_summary(playlist)
    payload["tracks"] = [track_summary(track) for track in playlist.tracks]
    return payload


def smart_playlist_summary(playlist: SmartPlaylist) -> Dict[str, Any]:
    """SmartPlaylist search payload without tracks or criteria body."""
    return {
        "id": playlist.id,
        "name": playlist.name,
        "folder_id": playlist.folder_id,
        "position": playlist.position,
        "path": playlist.path,
    }


def smart_playlist_dict(playlist: SmartPlaylist) -> Dict[str, Any]:
    """SmartPlaylist payload."""
    criteria = None
    if playlist.criteria is not None:
        criteria = criteria_to_dict(playlist.criteria)
    payload = smart_playlist_summary(playlist)
    payload["tracks"] = [track_summary(track) for track in playlist.tracks]
    payload["criteria"] = criteria
    return payload


def tree_dict(node: TreeNode) -> Dict[str, Any]:
    """Recursive tree node payload."""
    return {
        "id": node.id,
        "name": node.name,
        "path": node.path,
        "entity": node.entity,
        "children": [tree_dict(child) for child in node.children],
    }


def tree_list(nodes: List[TreeNode]) -> List[Dict[str, Any]]:
    """Serialize a forest of tree nodes."""
    return [tree_dict(node) for node in nodes]
