"""Tests for rekordboxkit repository, mapping, smartlist codec, serialize, MCP tools."""

from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from fortherekord_mcp import server as mcp_server
from rekordboxkit.criteria import criteria_from_dict
from rekordboxkit.domain import Condition, Criteria
from rekordboxkit.errors import (
    EntityNotFoundError,
    FolderNotEmptyError,
    RekordboxRunningError,
    UnconfirmedFieldError,
    ValidationError,
    WrongEntityTypeError,
)
from rekordboxkit.mapping import date_str, map_folder, map_track, parent_id_of, tag_names_of
from rekordboxkit.repository import RekordboxRepository, _first, _rows
from rekordboxkit.serialize import (
    folder_dict,
    history_folder_dict,
    history_session_dict,
    playlist_dict,
    smart_playlist_dict,
    track_dict,
    track_summary,
    tree_list,
)
from rekordboxkit.session import RekordboxSession
from rekordboxkit.smartlist_codec import criteria_to_smartlist, smartlist_to_criteria


def _row(identifier, name, attribute, seq=1, parent_id=None, smart=None):
    row = Mock()
    row.ID = identifier
    row.Name = name
    row.Attribute = attribute
    row.Seq = seq
    row.SmartList = smart
    if parent_id is None:
        row.Parent = None
    else:
        parent = Mock()
        parent.ID = parent_id
        parent.Name = "parent"
        row.Parent = parent
    return row


def _content(identifier="1", title="Tune", artist="A", folder=r"D:\Aug - 2026\a.wav"):
    content = Mock()
    content.ID = identifier
    content.Title = title
    content.Artist = Mock(Name=artist)
    content.Album = Mock(Name="Album")
    content.Genre = Mock(Name="DnB")
    content.Label = None
    content.Commnt = "note"
    content.Rating = 4
    content.Color = Mock(Commnt="Pink")
    content.MyTagNames = ["dark"]
    content.MyTags = []
    content.Key = Mock(ScaleName="8A")
    content.BPM = 12800
    content.Length = 180
    content.FolderPath = folder
    content.FileNameL = "a.wav"
    content.StockDate = "2026-08-01"
    content.DateCreated = None
    content.ReleaseDate = None
    content.ReleaseYear = None
    content.AlbumArtist = None
    content.AlbumArtistName = None
    content.OrgArtist = None
    content.OrgArtistName = None
    content.Remixer = None
    content.RemixerName = None
    content.Composer = None
    content.ComposerName = None
    content.ColorID = 1
    content.FileType = 11
    content.BitRate = 320
    content.DJPlayCount = "12"
    return content


def _repo(db, exists=True):
    session = RekordboxSession(Path("master.db"))
    session._db = db  # pylint: disable=protected-access
    session.is_rekordbox_running = False
    return RekordboxRepository(session, path_exists=lambda _path: exists)


class TestMappingAndSerialize:
    """Content mapping and JSON payloads."""

    def test_map_track_and_dicts(self):
        """Map a content row and serialize it."""
        track = map_track(_content(), lambda _path: True)
        assert track.bpm == 128.0
        assert track.bitrate == 320
        assert track.file_type == "wav"
        assert track.play_count == 12
        assert track.missing is False
        assert track.tags == ["dark"]
        extra = _content()
        extra.AlbumArtist = Mock(Name="AA")
        extra.OrgArtistName = "OA"
        extra.Remixer = Mock(Name="RX")
        extra.ComposerName = "CO"
        extra.ReleaseYear = 2024
        extra.DateCreated = "2026-07-01"
        extra.ReleaseDate = "2024-01-15"
        mapped = map_track(extra, lambda _path: True)
        assert mapped.album_artist == "AA"
        assert mapped.original_artist == "OA"
        assert mapped.remixer == "RX"
        assert mapped.composer == "CO"
        assert mapped.year == 2024
        assert mapped.date_created == "2026-07-01"
        assert mapped.date_released == "2024-01-15"
        assert track_dict(mapped)["year"] == 2024
        assert track_summary(track)["location"].endswith("a.wav")
        assert track_dict(track)["genre"] == "DnB"
        assert track_dict(track)["play_count"] == 12
        root = Mock()
        root.Parent = Mock(ID="0")
        assert parent_id_of(root) is None
        named = Mock()
        named.Parent = Mock(ID="root")
        assert parent_id_of(named) is None
        assert date_str(datetime(2026, 8, 1)) == "2026-08-01"
        assert date_str("") is None
        tagged = Mock()
        tagged.MyTagNames = None
        inner = Mock(Name="from-link")
        tagged.MyTags = [
            Mock(MyTag=inner),
            Mock(MyTag=None, Name="plain"),
            Mock(MyTag=None, Name=None),
        ]
        assert tag_names_of(tagged) == ["from-link", "plain"]
        orphan = _row(9, "leaf", 0, parent_id=99)
        assert "leaf" in map_folder(orphan, {}).path


class TestSmartlistCodec:
    """Criteria XML round-trip."""

    def test_roundtrip_genre(self):
        """Genre is conditions survive XML."""
        criteria = Criteria(match="all", conditions=[Condition("genre", "is", "Techno")])
        smart = criteria_to_smartlist(criteria, "10", lambda name: name, lambda name: name)
        parsed = smartlist_to_criteria(smart.to_xml(), lambda tag: tag, lambda color: color)
        assert parsed is not None
        assert parsed.conditions[0].field == "genre"
        assert parsed.conditions[0].value == "Techno"

    def test_empty_xml(self):
        """Empty XML is no criteria."""
        assert smartlist_to_criteria(None, str, str) is None

    def test_between_dates_tags_color_and_any(self):
        """Numeric, date, tag, and color conditions round-trip."""
        criteria = Criteria(
            match="any",
            conditions=[
                Condition("bpm", "between", {"min": 126, "max": 132}),
                Condition("bpm", "is", 128.5),
                Condition("date_added", "in_last", {"amount": 2, "unit": "week"}),
                Condition("tags", "contains", "dark"),
                Condition("color", "is", "Pink"),
                Condition("title", "contains", "tune"),
                Condition("title", "is", None),
            ],
        )
        smart = criteria_to_smartlist(
            criteria, "10", lambda name: "tag-" + name, lambda name: "color-" + name
        )
        parsed = smartlist_to_criteria(
            smart.to_xml(),
            lambda tag: tag.replace("tag-", ""),
            lambda color: color.replace("color-", ""),
        )
        assert parsed is not None
        assert parsed.match == "any"
        by_op = {(item.field, item.operator): item for item in parsed.conditions}
        assert by_op[("bpm", "between")].value == {"min": 126, "max": 132}
        assert by_op[("bpm", "is")].value == 128.5
        assert by_op[("date_added", "in_last")].value["unit"] == "week"
        assert by_op[("tags", "contains")].value == "dark"
        assert by_op[("color", "is")].value == "Pink"

    def test_unknown_property_and_unmapped_field(self):
        """Unknown XML properties are skipped; unmapped fields cannot persist."""
        from pyrekordbox.db6.smartlist import SmartList

        with patch("rekordboxkit.smartlist_codec.validate_smart_playlist_criteria"):
            with pytest.raises(ValidationError, match="cannot be saved"):
                criteria_to_smartlist(
                    Criteria(match="all", conditions=[Condition("location", "is", "x")]),
                    "1",
                    str,
                    str,
                )

        def fake_parse(self, _source):
            self.logical_operator = 2
            unknown = Mock(property="mixName", operator=1, value_left="a", value_right="", unit="")
            bad_op = Mock(property="genre", operator=99, value_left="x", value_right="", unit="")
            self.conditions = [unknown, bad_op]

        with patch.object(SmartList, "parse", fake_parse):
            assert smartlist_to_criteria("<xml/>", str, str) is None


class TestRepositoryRead:
    """Tree, get-by-id, and search."""

    def test_tree_and_gets(self):
        """Folders, playlists, and smart playlists are distinct types."""
        folder = _row(1, "bush", 1, seq=1)
        playlist = _row(2, "dark", 0, seq=1, parent_id=1)
        smart = _row(3, "auto", 4, seq=2, parent_id=1)
        content = _content()
        db = Mock()
        db.get_playlist.return_value = [folder, playlist, smart]
        db.get_playlist_contents.return_value = Mock(all=lambda: [content])
        db.get_content.side_effect = lambda **kwargs: (
            content if kwargs.get("ID") in (1, "1") else [content]
        )
        repo = _repo(db)
        tree = repo.list_tree()
        assert tree[0].entity == "folder"
        assert tree[0].children[0].entity == "playlist"
        assert repo.get_playlist_folder("1").name == "bush"
        assert repo.get_playlist("2").tracks[0].title == "Tune"
        with pytest.raises(WrongEntityTypeError):
            repo.get_playlist("1")
        with pytest.raises(EntityNotFoundError):
            repo.get_playlist_folder("99")

    def test_search_tracks_by_location(self):
        """Validation story: location starts with the import folder."""
        db = Mock()
        db.get_content.return_value = [_content()]
        repo = _repo(db)
        criteria = criteria_from_dict(
            {
                "match": "all",
                "conditions": [
                    {"field": "location", "operator": "starts_with", "value": r"D:\Aug - 2026"}
                ],
            }
        )
        found = repo.search_tracks(criteria)
        assert len(found) == 1
        assert found[0].title == "Tune"
        by_plays = repo.search_tracks(
            criteria_from_dict(
                {
                    "match": "all",
                    "conditions": [{"field": "play_count", "operator": "greater", "value": 5}],
                }
            )
        )
        assert by_plays[0].play_count == 12

    def test_search_playlists_and_folders(self):
        """Search playlist objects by name and contained track."""
        folder = _row(1, "nights", 1)
        playlist = _row(2, "crate", 0, parent_id=1)
        smart = _row(3, "smarty", 4, parent_id=1)
        db = Mock()
        db.get_playlist.return_value = [folder, playlist, smart]
        db.get_playlist_contents.return_value = Mock(all=lambda: [_content("9")])
        repo = _repo(db)
        folders = repo.search_playlist_folders(
            Criteria(match="all", conditions=[Condition("name", "contains", "night")])
        )
        assert folders[0].id == "1"
        playlists = repo.search_playlists(
            Criteria(match="all", conditions=[Condition("track", "contains", "9")])
        )
        assert playlists[0].id == "2"
        smarts = repo.search_smart_playlists(
            Criteria(match="all", conditions=[Condition("name", "is", "smarty")])
        )
        assert smarts[0].id == "3"


class TestRepositoryHistory:
    """History tree, get-by-id, and search."""

    def test_history_tree_and_gets(self):
        """History folders and sessions are distinct, tracks follow TrackNo."""
        folder = _row(1, "2026", 1, seq=1)
        session = _row(2, "Saturday", 0, seq=1, parent_id=1)
        session.DateCreated = "2026-08-01"
        first = _content("1", "First")
        second = _content("2", "Second")
        song_late = Mock(TrackNo=2, ContentID="2", Content=None)
        song_first = Mock(TrackNo=1, ContentID="1", Content=first)
        song_empty = Mock(TrackNo=3, ContentID=None, Content=None)
        song_gone = Mock(TrackNo=4, ContentID="99", Content=None)
        db = Mock()
        db.get_history.return_value = [folder, session]
        db.get_history_songs.return_value = [song_late, song_first, song_empty, song_gone]
        db.get_content.side_effect = lambda **kwargs: (
            second if kwargs.get("ID") in (2, "2") else None
        )
        repo = _repo(db)
        tree = repo.list_history_tree()
        assert tree[0].entity == "history_folder"
        assert tree[0].children[0].entity == "history_session"
        assert repo.get_history_folder("1").name == "2026"
        history = repo.get_history("2")
        assert [track.title for track in history.tracks] == ["First", "Second"]
        assert history.date == "2026-08-01"
        with pytest.raises(WrongEntityTypeError):
            repo.get_history("1")
        with pytest.raises(EntityNotFoundError):
            repo.get_history_folder("99")

    def test_search_history(self):
        """Search history folders by name and sessions by contained track."""
        folder = _row(1, "2026", 1)
        session = _row(2, "Saturday", 0, parent_id=1)
        session.DateCreated = "2026-08-01"
        content = _content("9")
        song = Mock(TrackNo=1, ContentID="9", Content=content)
        db = Mock()
        db.get_history.return_value = [folder, session]
        db.get_history_songs.return_value = [song]
        repo = _repo(db)
        folders = repo.search_history_folders(
            Criteria(match="all", conditions=[Condition("name", "is", "2026")])
        )
        assert folders[0].id == "1"
        sessions = repo.search_history_sessions(
            Criteria(match="all", conditions=[Condition("track", "contains", "9")])
        )
        assert sessions[0].id == "2"
        assert history_folder_dict(folders[0])["path"]
        assert history_session_dict(sessions[0])["date"] == "2026-08-01"


class TestRepositoryWrite:
    """Confirmed mutations and safety."""

    def test_preview_does_not_create(self):
        """confirm=false returns a diff and does not call create."""
        db = Mock()
        repo = _repo(db)
        result = repo.create_playlist_folder("new", confirm=False)
        assert result.applied is False
        db.create_playlist_folder.assert_not_called()

    def test_create_and_update_playlist(self, monkeypatch):
        """Creating a playlist adds tracks when confirmed."""
        monkeypatch.setenv("FORTHEREKORD_TEST_MODE", "1")
        created = _row(8, "new", 0)
        db = Mock()
        db.create_playlist.return_value = created
        db.get_playlist.return_value = [created]
        db.get_playlist_songs.return_value = []
        repo = _repo(db)
        result = repo.create_playlist("new", track_ids=["1"], confirm=True)
        assert result.applied is True
        db.add_to_playlist.assert_called()
        db.commit.assert_not_called()

    def test_running_blocks_write(self):
        """Rekordbox running refuses confirmed writes."""
        db = Mock()
        repo = _repo(db)
        repo._session.is_rekordbox_running = True  # pylint: disable=protected-access
        with pytest.raises(RekordboxRunningError):
            repo.create_playlist_folder("x", confirm=True)

    def test_folder_not_empty(self):
        """Non-recursive delete of a folder with children fails."""
        folder = _row(1, "bush", 1)
        child = _row(2, "dark", 0, parent_id=1)
        db = Mock()
        db.get_playlist.return_value = [folder, child]
        repo = _repo(db)
        with pytest.raises(FolderNotEmptyError):
            repo.delete_playlist_folder("1", recursive=False, confirm=True)
        preview = repo.delete_playlist_folder("1", recursive=True, confirm=False)
        assert preview.diff["children"] == ["2"]

    def test_reject_folder_cycle_and_missing_parent(self):
        """Cannot move a folder into itself or a descendant."""
        parent = _row(1, "bush", 1)
        child = _row(2, "nights", 1, parent_id=1)
        playlist = _row(3, "crate", 0, parent_id=1)
        db = Mock()
        db.get_playlist.return_value = [parent, child, playlist]
        repo = _repo(db)
        with pytest.raises(ValidationError, match="itself"):
            repo.update_playlist_folder("1", {"parent_id": "1"}, confirm=False)
        with pytest.raises(ValidationError, match="descendant"):
            repo.update_playlist_folder("1", {"parent_id": "2"}, confirm=True)
        with pytest.raises(EntityNotFoundError, match="folder not found"):
            repo.update_playlist("3", {"folder_id": "99"}, confirm=False)
        with pytest.raises(ValidationError, match="parent must be a folder"):
            repo.update_playlist_folder("1", {"parent_id": "3"}, confirm=False)

    def test_update_track_gates_bpm(self):
        """Unconfirmed encodings cannot be written."""
        db = Mock()
        db.get_content.return_value = _content()
        repo = _repo(db)
        with pytest.raises(UnconfirmedFieldError):
            repo.update_track("1", {"bpm": 130}, confirm=True)
        with pytest.raises(ValidationError):
            repo.update_track("1", {"duration": 1}, confirm=True)

    def test_update_track_title_preview_and_apply(self, monkeypatch):
        """Title patch previews then applies in test mode without commit."""
        monkeypatch.setenv("FORTHEREKORD_TEST_MODE", "1")
        content = _content()
        db = Mock()
        db.get_content.return_value = content
        repo = _repo(db)
        preview = repo.update_track("1", {"title": "Clean"}, confirm=False)
        assert preview.applied is False
        applied = repo.update_track("1", {"title": "Clean"}, confirm=True)
        assert applied.applied is True
        assert content.Title == "Clean"
        db.commit.assert_not_called()

    def test_create_smart_playlist_preview(self):
        """Smart playlist create requires persistable criteria."""
        db = Mock()
        repo = _repo(db)
        criteria = Criteria(match="all", conditions=[Condition("genre", "is", "Techno")])
        result = repo.create_smart_playlist("auto", criteria, confirm=False)
        assert result.applied is False
        db.create_smart_playlist.assert_not_called()

    def test_get_track_missing(self):
        """Unknown track id raises."""
        db = Mock()
        db.get_content.return_value = None
        repo = _repo(db)
        with pytest.raises(EntityNotFoundError):
            repo.get_track("nope")

    def test_probe_encodings(self):
        """Probe reads raw storage fields."""
        db = Mock()
        db.get_content.return_value = _content()
        repo = _repo(db)
        report = repo.probe_encodings("1")
        assert "decoded" in report

    def test_query_unwrap_helpers(self):
        """Lists, None, scalars, and real query types unwrap correctly."""

        class Query:
            def __init__(self, rows):
                self._rows = rows

            def all(self):
                return self._rows

            def first(self):
                return self._rows[0] if self._rows else None

            def one_or_none(self):
                return self._rows[0] if self._rows else None

        assert _rows(None) == []
        assert _rows([1, 2]) == [1, 2]
        assert _rows(Query([1])) == [1]
        assert _rows(7) == [7]
        assert _first(None) is None
        assert _first([9]) == 9
        assert _first([]) is None
        assert _first(Query([])) is None
        assert _first(Query([4])) == 4
        assert _first(8) == 8
        assert _rows((1, 2)) == [1, 2]

        class FirstOnly:
            def first(self):
                return 3

        class AllOnly:
            def __init__(self, rows):
                self._rows = rows

            def all(self):
                return self._rows

        assert _first(FirstOnly()) == 3
        assert _first(AllOnly([5])) == 5
        assert _first(AllOnly([])) is None

    def test_confirmed_folder_playlist_and_smart_writes(self, monkeypatch):
        """Confirmed CRUD covers create, rename, move, membership, and delete."""
        monkeypatch.setenv("FORTHEREKORD_TEST_MODE", "1")
        folder = _row(1, "bush", 1)
        playlist = _row(2, "dark", 0, parent_id=1)
        smart = _row(3, "auto", 4, parent_id=1)
        created_folder = _row(10, "new-folder", 1)
        created_playlist = _row(11, "new-list", 0)
        created_smart = _row(12, "new-smart", 4)
        db = Mock()
        db.get_playlist.return_value = [folder, playlist, smart]
        db.create_playlist_folder.return_value = created_folder
        db.create_playlist.return_value = created_playlist
        db.create_smart_playlist.return_value = created_smart
        db.get_playlist_songs.return_value = [Mock()]
        db.get_playlist_contents.return_value = Mock(all=lambda: [_content()])
        db.get_my_tag.return_value = None
        db.get_color.return_value = None
        repo = _repo(db)

        preview = repo.delete_playlist_folder("1", recursive=True, confirm=False)
        assert preview.applied is False
        assert repo.update_playlist_folder("1", {"name": "x"}, confirm=False).applied is False
        assert repo.update_playlist("2", {"name": "x"}, confirm=False).applied is False
        assert repo.update_smart_playlist("3", {"name": "x"}, confirm=False).applied is False
        assert repo._tracks_for(folder) == []  # pylint: disable=protected-access
        created = repo.create_playlist_folder("new-folder", parent_id="1", position=2, confirm=True)
        assert created.diff["id"] == "10"
        repo.update_playlist_folder("1", {"name": "trees", "position": 3}, confirm=True)
        db.rename_playlist.assert_called()
        db.move_playlist.assert_called()
        repo.delete_playlist_folder("1", recursive=True, confirm=True)

        empty = _row(20, "empty", 1)
        db.get_playlist.return_value = [empty]
        repo.delete_playlist_folder("20", confirm=True)

        db.get_playlist.return_value = [folder, playlist, smart]
        listed = repo.create_playlist("listed", folder_id="1", track_ids=["1"], confirm=True)
        assert listed.applied is True
        assert repo.create_playlist("plain", confirm=False).applied is False
        repo.create_playlist("bare", confirm=True)
        repo.update_playlist(
            "2", {"name": "darker", "tracks": ["1"], "folder_id": None, "position": 4}, confirm=True
        )
        assert db.move_playlist.call_args.kwargs["parent"] == "root"
        db.remove_from_playlist.assert_called()
        preview_pl = repo.delete_playlist("2", confirm=False)
        assert preview_pl.applied is False
        repo.delete_playlist("2", confirm=True)

        criteria = Criteria(match="all", conditions=[Condition("genre", "is", "Techno")])
        smart_created = repo.create_smart_playlist(
            "auto", criteria, folder_id="1", position=1, confirm=True
        )
        assert smart_created.diff["id"] == "12"
        with pytest.raises(ValidationError, match="derived"):
            repo.update_smart_playlist("3", {"tracks": ["1"]}, confirm=False)
        repo.update_smart_playlist("3", {"name": "auto2"}, confirm=True)
        repo.update_smart_playlist("3", {"criteria": criteria}, confirm=True)
        assert isinstance(smart.SmartList, str)
        with pytest.raises(ValidationError, match="Criteria"):
            repo.update_smart_playlist("3", {"criteria": {"match": "all"}}, confirm=True)
        preview_sm = repo.delete_smart_playlist("3", confirm=False)
        assert preview_sm.applied is False
        repo.delete_smart_playlist("3", confirm=True)

        db.get_playlist_contents.side_effect = AttributeError("month not supported")
        db.get_playlist.return_value = [smart]
        assert repo.get_smart_playlist("3").tracks == []
        db.get_playlist_contents.side_effect = AttributeError("missing column")
        db.get_playlist.return_value = [playlist]
        with pytest.raises(AttributeError, match="missing column"):
            repo.get_playlist("2")

    def test_update_track_related_fields(self, monkeypatch):
        """Writable related fields, tags, and lookup failures."""
        monkeypatch.setenv("FORTHEREKORD_TEST_MODE", "1")
        content = _content()
        content.Artist = None
        content.MyTags = [Mock()]
        color = Mock(ID="c1", Commnt="Pink", Name=None)
        tag = Mock(ID="t1", Name="dark")
        db = Mock()
        db.get_content.return_value = content
        db.get_artist.return_value = None
        db.add_artist.return_value = Mock(Name="B")
        db.get_album.return_value = Mock(Name="Album")
        db.get_genre.return_value = None
        db.add_genre.return_value = Mock(Name="DnB")
        db.get_label.return_value = None
        db.add_label.return_value = Mock(Name="Label")
        db.get_color.return_value = [color]
        db.get_my_tag.side_effect = lambda **kwargs: (
            tag if kwargs.get("ID") in (1, "t1", "1") else [tag]
        )
        repo = _repo(db)
        with pytest.raises(ValidationError, match="empty"):
            repo.update_track("1", {}, confirm=True)
        with patch("rekordboxkit.repository.DjmdSongMyTag") as tag_link:
            tag_link.return_value = Mock()
            result = repo.update_track(
                "1",
                {
                    "title": "N",
                    "artist": "B",
                    "album": "Album",
                    "genre": "DnB",
                    "label": "Label",
                    "comments": "c",
                    "rating": 5,
                    "color": "Pink",
                    "tags": ["dark"],
                },
                confirm=True,
            )
        assert result.applied is True
        assert content.Title == "N"
        old_artist = Mock(Name="A")
        renamed = Mock(Name="Renamed")
        content.Artist = old_artist
        db.get_artist.return_value = renamed
        repo.update_track("1", {"artist": "Renamed"}, confirm=True)
        assert content.Artist is renamed
        assert old_artist.Name == "A"
        repo.update_track(
            "1", {"artist": "", "album": "", "color": None, "rating": None}, confirm=True
        )
        assert content.Artist is None
        with pytest.raises(ValidationError, match="unknown color"):
            repo.update_track("1", {"color": "nope"}, confirm=True)
        db.get_my_tag.side_effect = lambda **kwargs: []
        with pytest.raises(ValidationError, match="unknown tag"):
            repo.update_track("1", {"tags": ["nope"]}, confirm=True)
        db.get_content.return_value = None
        with pytest.raises(EntityNotFoundError):
            repo.probe_encodings("missing")
        with pytest.raises(EntityNotFoundError):
            repo.update_track("missing", {"title": "x"}, confirm=False)
        db.get_content.return_value = _content()
        assert repo.get_track("abc").title == "Tune"
        assert repo._tag_name_for_id("missing") == "missing"  # pylint: disable=protected-access
        db.get_color.return_value = None
        assert repo._color_name_for_id("9") == "9"  # pylint: disable=protected-access
        db.get_color.return_value = [Mock(ID="c1", Commnt=None, Name="Blue")]
        assert repo._color_id_for_name("Blue") == "c1"  # pylint: disable=protected-access
        db.get_my_tag.side_effect = lambda **kwargs: Mock(ID="t1", Name="dark")
        assert repo._tag_id_for_name("dark") == "t1"  # pylint: disable=protected-access
        assert repo._tag_name_for_id("t1") == "dark"  # pylint: disable=protected-access
        db.get_color.return_value = Mock(ID="c1", Commnt="Pink")
        assert repo._color_name_for_id("c1") == "Pink"  # pylint: disable=protected-access


class TestMcpServer:
    """MCP tools delegate to the repository."""

    def teardown_method(self):
        """Clear the module repository."""
        mcp_server.set_repository(None)

    def test_list_tree_and_search(self):
        """Tools return serialized payloads."""
        repo = Mock()
        from rekordboxkit.domain import TreeNode, Track as DomainTrack

        repo.list_tree.return_value = [TreeNode(id="1", name="root", path="root", entity="folder")]
        repo.search_tracks.return_value = [
            DomainTrack(id="1", title="Tune", artist="A", location=r"D:\Aug - 2026\a.wav")
        ]
        mcp_server.set_repository(repo)
        tree = mcp_server.list_tree()
        assert tree[0]["entity"] == "folder"
        found = mcp_server.search_tracks(
            "all", [{"field": "location", "operator": "starts_with", "value": r"D:\Aug - 2026"}]
        )
        assert found[0]["title"] == "Tune"
        from rekordboxkit.domain import HistoryFolder, HistorySession

        repo.list_history_tree.return_value = [
            TreeNode(id="h", name="2026", path="2026", entity="history_folder")
        ]
        repo.search_history_folders.return_value = [HistoryFolder("h", "2026", None, 1, "2026")]
        repo.search_history_sessions.return_value = [
            HistorySession("s", "set", "h", 1, "2026 / set", "2026-08-01", [])
        ]
        repo.get_history_folder.return_value = HistoryFolder("h", "2026", None, 1, "2026")
        repo.get_history.return_value = HistorySession(
            "s", "set", "h", 1, "2026 / set", "2026-08-01", []
        )
        assert mcp_server.list_history_tree()[0]["entity"] == "history_folder"
        assert mcp_server.get_history_folder("h")["name"] == "2026"
        assert mcp_server.get_history("s")["date"] == "2026-08-01"
        cond = [{"field": "name", "operator": "is", "value": "2026"}]
        assert mcp_server.search_history_folders("all", cond)[0]["id"] == "h"
        assert mcp_server.search_history_sessions("all", cond)[0]["id"] == "s"

    def test_errors_are_payloads(self):
        """Kit errors become {error: ...}."""
        repo = Mock()
        repo.get_track.side_effect = EntityNotFoundError("missing")
        mcp_server.set_repository(repo)
        assert mcp_server.get_track("x")["error"] == "missing"

    def test_mutations_confirm_flag(self):
        """create_playlist_folder passes confirm through."""
        repo = Mock()
        from rekordboxkit.domain import MutationResult

        repo.create_playlist_folder.return_value = MutationResult(False, {"action": "create"})
        mcp_server.set_repository(repo)
        payload = mcp_server.create_playlist_folder("x", confirm=False)
        assert payload["applied"] is False

    def test_get_and_update_wrappers(self):
        """Get and update tools serialize entities."""
        from rekordboxkit.domain import (
            MutationResult,
            Playlist,
            PlaylistFolder,
            SmartPlaylist,
            Track as DomainTrack,
        )

        repo = Mock()
        repo.get_playlist_folder.return_value = PlaylistFolder("1", "f", None, 1, "f")
        repo.get_playlist.return_value = Playlist("2", "p", "1", 1, "f / p", [])
        repo.get_smart_playlist.return_value = SmartPlaylist("3", "s", "1", 1, "f / s", [], None)
        repo.get_track.return_value = DomainTrack("9", "t", "a")
        repo.update_track.return_value = MutationResult(True, {"id": "9"})
        mcp_server.set_repository(repo)
        assert folder_dict(repo.get_playlist_folder("1"))["name"] == "f"
        assert mcp_server.get_playlist_folder("1")["id"] == "1"
        assert mcp_server.get_playlist("2")["id"] == "2"
        assert mcp_server.get_smart_playlist("3")["id"] == "3"
        assert mcp_server.get_track("9")["id"] == "9"
        assert mcp_server.update_track("9", {"title": "n"}, True)["applied"] is True
        assert playlist_dict(repo.get_playlist("2"))["folder_id"] == "1"
        assert smart_playlist_dict(repo.get_smart_playlist("3"))["criteria"] is None
        from rekordboxkit.domain import Criteria as DomainCriteria, Condition as DomainCondition

        with_criteria = SmartPlaylist(
            "4",
            "s2",
            "1",
            1,
            "f / s2",
            [],
            DomainCriteria(match="all", conditions=[DomainCondition("genre", "is", "Techno")]),
        )
        assert smart_playlist_dict(with_criteria)["criteria"]["match"] == "all"
        assert tree_list([]) == []

    def test_remaining_tools_and_errors(self):
        """Search and mutation tools serialize and map kit errors."""
        from rekordboxkit.domain import (
            MutationResult,
            Playlist,
            PlaylistFolder,
            SmartPlaylist,
        )

        repo = Mock()
        folder = PlaylistFolder("1", "f", None, 1, "f")
        playlist = Playlist("2", "p", "1", 1, "f / p", [])
        smart = SmartPlaylist("3", "s", "1", 1, "f / s", [], None)
        repo.search_playlist_folders.return_value = [folder]
        repo.search_playlists.return_value = [playlist]
        repo.search_smart_playlists.return_value = [smart]
        repo.create_playlist.return_value = MutationResult(False, {"action": "create"})
        repo.update_playlist_folder.return_value = MutationResult(False, {"action": "update"})
        repo.delete_playlist_folder.return_value = MutationResult(False, {"action": "delete"})
        repo.update_playlist.return_value = MutationResult(True, {"action": "update"})
        repo.delete_playlist.return_value = MutationResult(True, {"action": "delete"})
        repo.create_smart_playlist.return_value = MutationResult(False, {"action": "create"})
        repo.update_smart_playlist.return_value = MutationResult(True, {"action": "update"})
        repo.delete_smart_playlist.return_value = MutationResult(True, {"action": "delete"})
        mcp_server.set_repository(repo)
        cond = [{"field": "name", "operator": "is", "value": "f"}]
        assert mcp_server.search_playlist_folders("all", cond)[0]["id"] == "1"
        assert mcp_server.search_playlists("all", cond)[0]["id"] == "2"
        assert mcp_server.search_smart_playlists("all", cond)[0]["id"] == "3"
        assert mcp_server.create_playlist("p", confirm=False)["applied"] is False
        assert mcp_server.update_playlist_folder("1", {"name": "x"})["applied"] is False
        assert mcp_server.delete_playlist_folder("1")["applied"] is False
        assert mcp_server.update_playlist("2", {"name": "n"}, True)["applied"] is True
        assert mcp_server.delete_playlist("2", True)["applied"] is True
        assert (
            mcp_server.create_smart_playlist(
                "s", "all", [{"field": "genre", "operator": "is", "value": "Techno"}]
            )["applied"]
            is False
        )
        assert (
            mcp_server.update_smart_playlist(
                "3",
                {
                    "criteria": {
                        "match": "all",
                        "conditions": [{"field": "genre", "operator": "is", "value": "T"}],
                    }
                },
                True,
            )["applied"]
            is True
        )
        assert isinstance(repo.update_smart_playlist.call_args[0][1]["criteria"], Criteria)
        assert mcp_server.delete_smart_playlist("3", True)["applied"] is True

        repo.search_tracks.side_effect = ValidationError("bad")
        assert mcp_server.search_tracks("all", cond)["error"] == "bad"
        repo.search_playlist_folders.side_effect = ValidationError("bad")
        assert mcp_server.search_playlist_folders("all", cond)["error"] == "bad"
        repo.search_playlists.side_effect = ValidationError("bad")
        assert mcp_server.search_playlists("all", cond)["error"] == "bad"
        repo.search_smart_playlists.side_effect = ValidationError("bad")
        assert mcp_server.search_smart_playlists("all", cond)["error"] == "bad"
        repo.get_playlist_folder.side_effect = EntityNotFoundError("missing")
        assert mcp_server.get_playlist_folder("x")["error"] == "missing"
        repo.get_playlist.side_effect = EntityNotFoundError("missing")
        assert mcp_server.get_playlist("x")["error"] == "missing"
        repo.get_smart_playlist.side_effect = EntityNotFoundError("missing")
        assert mcp_server.get_smart_playlist("x")["error"] == "missing"
        repo.create_playlist_folder.side_effect = RekordboxRunningError("open")
        assert mcp_server.create_playlist_folder("x", confirm=True)["error"] == "open"
        repo.update_playlist_folder.side_effect = EntityNotFoundError("missing")
        assert mcp_server.update_playlist_folder("x", {})["error"] == "missing"
        repo.delete_playlist_folder.side_effect = FolderNotEmptyError("kids")
        assert mcp_server.delete_playlist_folder("x")["error"] == "kids"
        repo.create_playlist.side_effect = ValidationError("bad")
        assert mcp_server.create_playlist("p")["error"] == "bad"
        repo.update_playlist.side_effect = EntityNotFoundError("missing")
        assert mcp_server.update_playlist("x", {})["error"] == "missing"
        repo.delete_playlist.side_effect = EntityNotFoundError("missing")
        assert mcp_server.delete_playlist("x")["error"] == "missing"
        repo.create_smart_playlist.side_effect = ValidationError("bad")
        assert mcp_server.create_smart_playlist("s", "all", cond)["error"] == "bad"
        repo.update_smart_playlist.side_effect = EntityNotFoundError("missing")
        assert mcp_server.update_smart_playlist("x", {})["error"] == "missing"
        repo.delete_smart_playlist.side_effect = EntityNotFoundError("missing")
        assert mcp_server.delete_smart_playlist("x")["error"] == "missing"
        repo.update_track.side_effect = UnconfirmedFieldError("bpm")
        assert mcp_server.update_track("1", {"bpm": 1})["error"] == "bpm"
        repo.list_tree.side_effect = RuntimeError("boom")
        assert mcp_server.list_tree()["error"] == "boom"
        repo.list_history_tree.side_effect = RuntimeError("boom")
        assert mcp_server.list_history_tree()["error"] == "boom"
        repo.get_history_folder.side_effect = EntityNotFoundError("missing")
        assert mcp_server.get_history_folder("x")["error"] == "missing"
        repo.get_history.side_effect = EntityNotFoundError("missing")
        assert mcp_server.get_history("x")["error"] == "missing"
        repo.search_history_folders.side_effect = ValidationError("bad")
        assert mcp_server.search_history_folders("all", cond)["error"] == "bad"
        repo.search_history_sessions.side_effect = ValidationError("bad")
        assert mcp_server.search_history_sessions("all", cond)["error"] == "bad"

    def test_get_repository_and_main(self, tmp_path):
        """Lazy repository uses config; main runs stdio."""
        mcp_server.set_repository(None)
        with patch.object(mcp_server, "load_config", return_value={"rekordbox": {}}):
            with pytest.raises(RuntimeError, match="library_path"):
                mcp_server.get_repository()
        db_file = tmp_path / "master.db"
        db_file.write_bytes(b"")
        with patch.object(
            mcp_server, "load_config", return_value={"rekordbox": {"library_path": str(db_file)}}
        ):
            with patch.object(mcp_server, "RekordboxSession") as session_cls:
                with patch.object(mcp_server, "RekordboxRepository") as repo_cls:
                    session_cls.return_value = Mock()
                    repo = Mock()
                    repo_cls.return_value = repo
                    assert mcp_server.get_repository() is repo
                    assert mcp_server.get_repository() is repo
                    repo_cls.assert_called_once()
        with patch.object(mcp_server.mcp, "run") as run:
            mcp_server.main()
            run.assert_called_once_with(transport="stdio")
        import fortherekord_mcp.__main__ as mcp_main

        assert mcp_main.main is mcp_server.main
