"""Domain types for the Rekordbox library (MCP contract)."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

RangeValue = Dict[str, Any]
PeriodValue = Dict[str, Any]
ConditionValue = Union[str, int, float, bool, RangeValue, PeriodValue, None]


@dataclass
class Condition:
    """One comparison in a query or smart-playlist criteria."""

    field: str
    operator: str
    value: ConditionValue


@dataclass
class Criteria:
    """
    Match all or any conditions.

    Used for smart playlists and for unsaved searches.
    """

    match: str
    conditions: List[Condition]


@dataclass
class Track:  # pylint: disable=too-many-instance-attributes
    """A collection item."""

    id: str
    title: str
    artist: str
    album: Optional[str] = None
    genre: Optional[str] = None
    label: Optional[str] = None
    comments: Optional[str] = None
    rating: Optional[int] = None
    color: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    key: Optional[str] = None
    bpm: Optional[float] = None
    duration: Optional[int] = None
    location: Optional[str] = None
    missing: bool = False
    date_added: Optional[str] = None
    bitrate: Optional[int] = None
    file_type: Optional[str] = None
    play_count: Optional[int] = None
    album_artist: Optional[str] = None
    original_artist: Optional[str] = None
    remixer: Optional[str] = None
    composer: Optional[str] = None
    year: Optional[int] = None
    date_created: Optional[str] = None
    date_released: Optional[str] = None


@dataclass
class PlaylistFolder:
    """A node that holds folders, playlists, and smart playlists."""

    id: str
    name: str
    parent_id: Optional[str]
    position: int
    path: str


@dataclass
class Playlist:
    """A curated ordered list of tracks."""

    id: str
    name: str
    folder_id: Optional[str]
    position: int
    path: str
    tracks: List[Track]


@dataclass
class SmartPlaylist:
    """A saved query whose track list is derived from criteria."""

    id: str
    name: str
    folder_id: Optional[str]
    position: int
    path: str
    tracks: List[Track]
    criteria: Optional[Criteria]


@dataclass
class HistoryFolder:
    """A node in the Rekordbox History tree."""

    id: str
    name: str
    parent_id: Optional[str]
    position: int
    path: str


@dataclass
class HistorySession:
    """A recorded performance: ordered tracks mixed in sequence."""

    id: str
    name: str
    folder_id: Optional[str]
    position: int
    path: str
    date: Optional[str]
    tracks: List[Track]


@dataclass
class TreeNode:
    """Summary node for the playlist tree."""

    id: str
    name: str
    path: str
    entity: str
    children: List["TreeNode"] = field(default_factory=list)


@dataclass
class MutationResult:
    """Result of a confirmable write."""

    applied: bool
    diff: Dict[str, Any]
