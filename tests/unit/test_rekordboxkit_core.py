"""Tests for rekordboxkit write guard, session, encodings, criteria, and search."""

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from rekordboxkit.content import (
    artist_name,
    color_name,
    key_name,
    related_name,
    related_or_attr,
    release_year,
)
from rekordboxkit.criteria import (
    FOLDER_SEARCH_FIELDS,
    criteria_from_dict,
    criteria_to_dict,
    validate_criteria,
    validate_smart_playlist_criteria,
)
from rekordboxkit.domain import (
    Condition,
    Criteria,
    HistoryFolder,
    HistorySession,
    Playlist,
    PlaylistFolder,
    SmartPlaylist,
    Track,
)
from rekordboxkit.encodings import (
    decode_bitrate,
    decode_bpm,
    decode_file_type,
    decode_play_count,
    decode_rating,
    encode_bpm,
    encode_rating,
    probe_raw_content,
    resolve_location,
)
from rekordboxkit.errors import RekordboxRunningError, ValidationError
from rekordboxkit.search import (
    filter_folders,
    filter_history_folders,
    filter_history_sessions,
    filter_playlists,
    filter_smart_playlists,
    filter_tracks,
    matches_criteria,
)
from rekordboxkit.session import RekordboxSession
from rekordboxkit.write_guard import commit_database, is_test_mode


class TestWriteGuard:
    """Commit safety."""

    def test_test_mode_skips_commit(self, tmp_path, monkeypatch):
        """Test mode writes a dump file and does not commit."""
        dump = tmp_path / "dump.json"
        monkeypatch.setenv("FORTHEREKORD_TEST_MODE", "1")
        monkeypatch.setenv("FORTHEREKORD_TEST_DUMP_FILE", str(dump))
        db = Mock()
        commit_database(db)
        db.commit.assert_not_called()
        assert json.loads(dump.read_text(encoding="utf-8"))["test_mode"] is True

    def test_test_mode_without_dump_file(self, monkeypatch):
        """Test mode without dump path still skips commit."""
        monkeypatch.setenv("FORTHEREKORD_TEST_MODE", "1")
        monkeypatch.delenv("FORTHEREKORD_TEST_DUMP_FILE", raising=False)
        db = Mock()
        commit_database(db)
        db.commit.assert_not_called()

    @patch.dict("os.environ", {"FORTHEREKORD_TEST_MODE": "0"}, clear=False)
    def test_commit_when_not_test_mode(self):
        """Real mode calls db.commit."""
        db = Mock()
        commit_database(db)
        db.commit.assert_called_once()

    def test_is_test_mode(self, monkeypatch):
        """FORTHEREKORD_TEST_MODE=1 enables test mode."""
        monkeypatch.setenv("FORTHEREKORD_TEST_MODE", "1")
        assert is_test_mode() is True


class TestSession:
    """Database session."""

    @patch("rekordboxkit.session.Rekordbox6Database")
    @patch("pathlib.Path.exists", return_value=True)
    def test_open_and_reuse(self, _exists, mock_db_class):
        """Opens once and reuses the connection."""
        mock_db_class.return_value = Mock()
        session = RekordboxSession(Path("master.db"))
        first = session.database()
        second = session.database()
        assert first is second
        mock_db_class.assert_called_once()

    @patch("pathlib.Path.exists", return_value=False)
    def test_missing_file(self, _exists):
        """Missing database path raises FileNotFoundError."""
        session = RekordboxSession(Path("missing.db"))
        with pytest.raises(FileNotFoundError, match="Rekordbox database not found"):
            session.database()

    @patch("rekordboxkit.session.get_rekordbox_pid", return_value=123)
    def test_detects_running(self, _pid):
        """A live Rekordbox PID marks the session as running."""
        session = RekordboxSession(Path("master.db"))
        assert session.is_rekordbox_running is True

    @patch("rekordboxkit.session.get_rekordbox_pid", return_value=0)
    def test_detects_closed(self, _pid):
        """No Rekordbox PID means writes are allowed."""
        session = RekordboxSession(Path("master.db"))
        assert session.is_rekordbox_running is False
        session.is_rekordbox_running = True
        assert session.is_rekordbox_running is True

    def test_commit_requires_closed_rekordbox(self):
        """Commit while running raises."""
        session = RekordboxSession(Path("master.db"))
        session._db = Mock()  # pylint: disable=protected-access
        session.is_rekordbox_running = True
        with pytest.raises(RekordboxRunningError):
            session.commit()

    def test_commit_noop_without_db(self):
        """Commit with no open database is a no-op."""
        session = RekordboxSession(Path("master.db"))
        session.commit()

    @patch.dict("os.environ", {"FORTHEREKORD_TEST_MODE": "0"}, clear=False)
    def test_commit_delegates(self):
        """Commit calls the database when allowed."""
        session = RekordboxSession(Path("master.db"))
        session._db = Mock()  # pylint: disable=protected-access
        session.is_rekordbox_running = False
        session.commit()
        session._db.commit.assert_called_once()  # pylint: disable=protected-access

    @patch("rekordboxkit.session.get_rekordbox_pid", return_value=99)
    def test_commit_rechecks_pid(self, mock_pid):
        """Commit asks the process list, not a snapshot from open."""
        session = RekordboxSession(Path("master.db"))
        session._db = Mock()  # pylint: disable=protected-access
        with pytest.raises(RekordboxRunningError):
            session.commit()
        mock_pid.assert_called()


class TestEncodings:
    """BPM, rating, path, and file type decoding."""

    def test_bpm_hundredths_and_plain(self):
        """Large integers are hundredths; small values are BPM."""
        assert decode_bpm(12800) == 128.0
        assert decode_bpm(128) == 128.0
        assert decode_bpm(None) is None
        assert decode_bpm("x") is None
        assert encode_bpm(128.0) == 12800

    def test_rating_scales(self):
        """0-5 and XML 0/51/.../255 both decode to stars."""
        assert decode_rating(4) == 4
        assert decode_rating(204) == 4
        assert decode_rating(255) == 5
        assert decode_rating(100) == 2
        assert decode_rating(300) is None
        assert decode_rating("x") is None
        assert decode_rating(None) is None
        assert encode_rating(3) == 3
        with pytest.raises(ValueError):
            encode_rating(9)

    def test_file_type_and_location(self):
        """FileType ints and FolderPath/FileNameL combine into a location."""
        assert decode_file_type(11) == "wav"
        assert decode_file_type(99) is None
        assert decode_file_type("") is None
        assert decode_file_type("x") is None
        assert decode_bitrate(320) == 320
        assert decode_bitrate(320000) == 320
        assert decode_bitrate(0) is None
        assert decode_bitrate("") is None
        assert decode_bitrate("x") is None
        assert decode_play_count("12") == 12
        assert decode_play_count(3) == 3
        assert decode_play_count("") is None
        assert decode_play_count("x") is None
        assert decode_play_count(-1) is None
        assert resolve_location(r"D:\Aug - 2026\track.wav", "track.wav").endswith("track.wav")
        joined = resolve_location(r"D:\Aug - 2026", "track.wav")
        assert "track.wav" in joined
        assert resolve_location(None, None) is None
        assert resolve_location(None, "only.wav") == "only.wav"
        assert resolve_location(r"D:\folder", None) == str(Path(r"D:\folder"))

    def test_probe_raw_content(self):
        """Probe returns raw and decoded views."""
        report = probe_raw_content(
            {
                "BPM": 12800,
                "Rating": 4,
                "FolderPath": r"D:\a\b.wav",
                "FileNameL": "b.wav",
                "FileType": 11,
                "BitRate": 320,
                "DJPlayCount": "7",
            }
        )
        assert report["decoded"]["bpm"] == 128.0
        assert report["decoded"]["file_type"] == "wav"
        assert report["decoded"]["bitrate"] == 320
        assert report["decoded"]["play_count"] == 7


class TestCriteria:
    """Criteria validation."""

    def test_valid_and_roundtrip(self):
        """Valid criteria serializes and deserializes."""
        payload = {
            "match": "all",
            "conditions": [
                {"field": "location", "operator": "starts_with", "value": r"D:\Aug - 2026"},
                {"field": "bpm", "operator": "between", "value": {"min": 126, "max": 132}},
            ],
        }
        criteria = criteria_from_dict(payload)
        validate_criteria(criteria)
        assert criteria_to_dict(criteria)["match"] == "all"

    def test_rejects_empty_month_and_illegal_ops(self):
        """Empty lists, month, and illegal operators fail."""
        with pytest.raises(ValidationError, match="at least one"):
            validate_criteria(Criteria(match="all", conditions=[]))
        with pytest.raises(ValidationError, match="all' or 'any"):
            validate_criteria(Criteria(match="xor", conditions=[Condition("title", "is", "a")]))
        with pytest.raises(ValidationError, match="month"):
            validate_criteria(
                Criteria(
                    match="all",
                    conditions=[Condition("date_added", "in_last", {"amount": 1, "unit": "month"})],
                )
            )
        with pytest.raises(ValidationError, match="not valid"):
            validate_criteria(
                Criteria(match="all", conditions=[Condition("bpm", "starts_with", "12")])
            )
        with pytest.raises(ValidationError):
            criteria_from_dict({"match": "all", "conditions": "nope"})
        with pytest.raises(ValidationError):
            validate_smart_playlist_criteria(
                Criteria(match="all", conditions=[Condition("location", "starts_with", "D:\\x")])
            )
        with pytest.raises(ValidationError):
            validate_smart_playlist_criteria(
                Criteria(match="all", conditions=[Condition("bitrate", "is", 320)])
            )
        validate_criteria(
            Criteria(match="all", conditions=[Condition("name", "contains", "dark")]),
            FOLDER_SEARCH_FIELDS,
        )
        with pytest.raises(ValidationError, match="between requires"):
            validate_criteria(Criteria(match="all", conditions=[Condition("bpm", "between", 120)]))
        with pytest.raises(ValidationError, match="between requires"):
            validate_criteria(
                Criteria(match="all", conditions=[Condition("bpm", "between", {"min": 1})])
            )
        with pytest.raises(ValidationError, match="each condition"):
            criteria_from_dict({"match": "all", "conditions": ["nope"]})
        with pytest.raises(ValidationError, match="field and operator"):
            criteria_from_dict({"match": "all", "conditions": [{"field": "title"}]})
        with pytest.raises(ValidationError, match="unknown field"):
            validate_criteria(Criteria(match="all", conditions=[Condition("nope", "is", "x")]))
        with pytest.raises(ValidationError, match="in_last requires"):
            validate_criteria(
                Criteria(match="all", conditions=[Condition("date_added", "in_last", "x")])
            )
        with pytest.raises(ValidationError, match="in_last requires"):
            validate_criteria(
                Criteria(
                    match="all", conditions=[Condition("date_added", "in_last", {"amount": 1})]
                )
            )
        with pytest.raises(ValidationError, match="day' or 'week"):
            validate_criteria(
                Criteria(
                    match="all",
                    conditions=[Condition("date_added", "in_last", {"amount": 1, "unit": "year"})],
                )
            )
        validate_criteria(
            Criteria(
                match="all",
                conditions=[Condition("date_added", "not_in_last", {"amount": 1, "unit": "day"})],
            )
        )


class TestSearch:
    """In-memory criteria matching."""

    def test_location_prefix_and_tags(self):
        """Location starts_with is path-aware; tags use contains."""
        track = Track(
            id="1",
            title="Tune",
            artist="A",
            location=r"D:\Aug - 2026\song.wav",
            tags=["dark"],
            bpm=128,
            missing=False,
        )
        criteria = Criteria(
            match="all",
            conditions=[
                Condition("location", "starts_with", r"D:\Aug - 2026"),
                Condition("tags", "contains", "dark"),
            ],
        )
        assert filter_tracks([track], criteria) == [track]
        mixed = Criteria(
            match="all",
            conditions=[Condition("location", "starts_with", "D:/Aug - 2026")],
        )
        assert filter_tracks([track], mixed) == [track]
        other = Track(id="2", title="X", artist="B", location=r"D:\Other\a.wav")
        assert filter_tracks([other], criteria) == []
        extra = Track(
            id="3",
            title="Tune",
            artist="A",
            album_artist="AA",
            original_artist="OA",
            remixer="RX",
            composer="CO",
            year=2024,
            date_created="2026-07-01",
            date_released="2024-01-15",
        )
        by_year = Criteria(match="all", conditions=[Condition("year", "is", 2024)])
        assert filter_tracks([extra], by_year) == [extra]
        by_album_artist = Criteria(match="all", conditions=[Condition("album_artist", "is", "AA")])
        assert filter_tracks([extra], by_album_artist) == [extra]

    def test_any_match_between_and_playlist_track(self):
        """any match, numeric between, and playlist membership."""
        slow = Track(id="1", title="a", artist="a", bpm=100)
        fast = Track(id="2", title="b", artist="b", bpm=140)
        criteria = Criteria(
            match="any",
            conditions=[
                Condition("bpm", "between", {"min": 90, "max": 110}),
                Condition("title", "is", "missing"),
            ],
        )
        assert [item.id for item in filter_tracks([slow, fast], criteria)] == ["1"]
        playlist = Playlist(
            id="p",
            name="crate",
            folder_id=None,
            position=1,
            path="crate",
            tracks=[fast],
        )
        found = filter_playlists(
            [playlist],
            Criteria(match="all", conditions=[Condition("track", "contains", "2")]),
        )
        assert found == [playlist]
        folders = filter_folders(
            [PlaylistFolder(id="f", name="nights", parent_id=None, position=1, path="nights")],
            Criteria(match="all", conditions=[Condition("name", "contains", "night")]),
        )
        assert len(folders) == 1
        assert matches_criteria(
            {"missing": True}, Criteria(match="all", conditions=[Condition("missing", "is", True)])
        )
        assert matches_criteria(
            {"missing": True},
            Criteria(match="all", conditions=[Condition("missing", "is", "yes")]),
        )
        assert not matches_criteria(
            {"title": "Tune"},
            Criteria(match="all", conditions=[Condition("title", "is_not", "tune")]),
        )
        assert matches_criteria(
            {"title": "Tune"},
            Criteria(match="all", conditions=[Condition("title", "not_contains", "xyz")]),
        )
        assert matches_criteria(
            {"title": "Tune"},
            Criteria(match="all", conditions=[Condition("title", "starts_with", "tu")]),
        )
        assert matches_criteria(
            {"title": "Tune"},
            Criteria(match="all", conditions=[Condition("title", "ends_with", "ne")]),
        )
        assert matches_criteria(
            {"bpm": 140},
            Criteria(match="all", conditions=[Condition("bpm", "greater", 120)]),
        )
        assert matches_criteria(
            {"bpm": 100},
            Criteria(match="all", conditions=[Condition("bpm", "less", 120)]),
        )
        assert not matches_criteria(
            {"bpm": None},
            Criteria(match="all", conditions=[Condition("bpm", "greater", 1)]),
        )
        assert not matches_criteria(
            {"bpm": 100},
            Criteria(match="all", conditions=[Condition("bpm", "between", {"min": 1})]),
        )
        assert matches_criteria(
            {"tags": ["dark", "heavy"]},
            Criteria(match="all", conditions=[Condition("tags", "is", "dark")]),
        )
        assert matches_criteria(
            {"title": None},
            Criteria(match="all", conditions=[Condition("title", "is", None)]),
        )
        assert not matches_criteria(
            {"location": None},
            Criteria(match="all", conditions=[Condition("location", "starts_with", r"D:\x")]),
        )
        assert not matches_criteria(
            {"date_added": "not-a-date"},
            Criteria(
                match="all",
                conditions=[Condition("date_added", "in_last", {"amount": 1, "unit": "day"})],
            ),
        )
        assert not matches_criteria(
            {"date_added": ""},
            Criteria(
                match="all",
                conditions=[Condition("date_added", "in_last", {"amount": 1, "unit": "day"})],
            ),
        )
        from datetime import date

        today = date.today().isoformat()
        assert matches_criteria(
            {"date_added": today},
            Criteria(
                match="all",
                conditions=[Condition("date_added", "in_last", {"amount": 1, "unit": "week"})],
            ),
        )
        assert matches_criteria(
            {"date_added": "2000-01-01"},
            Criteria(
                match="all",
                conditions=[Condition("date_added", "not_in_last", {"amount": 1, "unit": "day"})],
            ),
        )
        assert not matches_criteria(
            {"title": "x"},
            Criteria(match="all", conditions=[Condition("title", "unknown_op", "x")]),
        )
        assert matches_criteria(
            {"bpm": 128},
            Criteria(match="all", conditions=[Condition("bpm", "is", 128)]),
        )
        assert matches_criteria(
            {"title": None},
            Criteria(match="all", conditions=[Condition("title", "contains", "")]),
        )
        assert matches_criteria(
            {"missing": True},
            Criteria(match="all", conditions=[Condition("missing", "is", 1)]),
        )
        smarts = filter_smart_playlists(
            [SmartPlaylist("1", "auto", None, 1, "auto", [], None)],
            Criteria(match="all", conditions=[Condition("name", "is", "auto")]),
        )
        assert len(smarts) == 1
        session = HistorySession("h", "set", "f", 1, "2026 / set", "2026-08-01", [fast])
        found_sessions = filter_history_sessions(
            [session],
            Criteria(match="all", conditions=[Condition("track", "contains", "2")]),
        )
        assert found_sessions == [session]
        hist_folders = filter_history_folders(
            [HistoryFolder("hf", "2026", None, 1, "2026")],
            Criteria(match="all", conditions=[Condition("name", "is", "2026")]),
        )
        assert len(hist_folders) == 1


class TestContentHelpers:
    """Content field helpers."""

    def test_names(self):
        """Artist, key, color, and related names."""
        content = Mock()
        content.Artist = Mock(Name="Artist A")
        content.Key = Mock(ScaleName="8A")
        content.Color = Mock(Commnt="Pink", Name=None)
        assert artist_name(content) == "Artist A"
        assert key_name(content) == "8A"
        assert color_name(content) == "Pink"
        assert related_name(Mock(Name="Techno")) == "Techno"
        assert related_name(None) is None
        assert related_name(Mock(Name="")) is None
        empty = Mock()
        empty.Artist = None
        empty.Key = "Am"
        empty.Color = None
        assert artist_name(empty) == ""
        assert key_name(empty) == "Am"
        assert color_name(empty) is None
        assert key_name(Mock(Key=None)) is None
        no_scale = Mock()
        no_scale.Key = Mock(spec=[])
        assert key_name(no_scale) is None
        colorless = Mock()
        colorless.Color = Mock(spec=[])
        assert color_name(colorless) is None
        named = Mock()
        named.AlbumArtist = Mock(Name="AA")
        named.AlbumArtistName = None
        named.ReleaseYear = 2024
        assert related_or_attr(named, "AlbumArtist", "AlbumArtistName") == "AA"
        named.AlbumArtist = None
        named.AlbumArtistName = "FromCol"
        assert related_or_attr(named, "AlbumArtist", "AlbumArtistName") == "FromCol"
        assert release_year(named) == 2024
        named.ReleaseYear = 0
        assert release_year(named) is None
        named.ReleaseYear = "x"
        assert release_year(named) is None
