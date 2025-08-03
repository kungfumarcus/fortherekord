"""
Unit tests for Rekordbox XML parsing.

Tests for rekordbox.py module functions.
"""

import pytest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch, mock_open

from fortherekord.models import RekordboxTrack, RekordboxPlaylist
from fortherekord.rekordbox import (
    load_rekordbox_library, parse_track_from_xml, get_collection_tracks,
    get_playlists, get_tracks_from_playlist, process_tracks_for_playlists,
    clean_track_title, clean_artist_name, normalize_track_metadata
)


class RekordboxTestBase:
    """Base class with shared XML creation helpers."""
    
    def _create_track_xml(self, **attrs):
        """Helper to create track XML element."""
        track_elem = ET.Element("TRACK")
        for key, value in attrs.items():
            track_elem.set(key, str(value))
        return track_elem

    def _create_collection_xml(self, tracks_data):
        """Helper to create collection XML."""
        root = ET.Element("DJ_PLAYLISTS")
        collection = ET.SubElement(root, "COLLECTION", Entries=str(len(tracks_data)))
        
        for track_data in tracks_data:
            track_elem = ET.SubElement(collection, "TRACK")
            for key, value in track_data.items():
                track_elem.set(key, str(value))
        
        return ET.ElementTree(root)

    def _create_basic_library_xml(self):
        """Helper to create a basic library XML structure."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <DJ_PLAYLISTS Version="1.0.0">
            <COLLECTION Entries="0"/>
        </DJ_PLAYLISTS>"""
        return xml_content


class TestLibraryLoading(RekordboxTestBase):
    """Test library file loading functions."""
    
    def test_load_rekordbox_library_file_not_found(self):
        """Test loading non-existent library file."""
        with pytest.raises(FileNotFoundError):
            load_rekordbox_library(Path("nonexistent.xml"))
    
    @patch("builtins.open", side_effect=ET.ParseError("Invalid XML"))
    @patch("pathlib.Path.exists", return_value=True)
    def test_load_rekordbox_library_invalid_xml(self, mock_exists, mock_file):
        """Test loading invalid XML file."""
        with pytest.raises(ET.ParseError):
            load_rekordbox_library(Path("invalid.xml"))
    
    @patch("pathlib.Path.exists", return_value=True)
    def test_load_rekordbox_library_success(self, mock_exists):
        """Test successful library loading."""
        xml_content = self._create_basic_library_xml()
        
        with patch("builtins.open", mock_open(read_data=xml_content)):
            tracks, playlists = load_rekordbox_library(Path("test.xml"))
            assert tracks is not None
            assert playlists is not None
            assert isinstance(tracks, list)
            assert isinstance(playlists, list)


class TestTrackParsing(RekordboxTestBase):
    """Test track metadata parsing functions."""
    
    def test_parse_track_from_xml_minimal(self):
        """Test parsing track with minimal data."""
        track_elem = self._create_track_xml(TrackID="1", Name="Test Song")
        track = parse_track_from_xml(track_elem)
        assert track is not None
        assert track.track_id == "1"
        assert track.title == "Test Song"
        assert track.artist == ""
    
    def test_parse_track_from_xml_complete(self):
        """Test parsing track with complete data."""
        track_elem = self._create_track_xml(
            TrackID="1",
            Name="Test Song",
            Artist="Test Artist",
            Album="Test Album",
            TotalTime="180",
            AverageBpm="128.5",
            Year="2023",
            Tonality="Am",
            Genre="House",
            PlayCount="5",
            Rating="4",
            Location="file:///music/test.mp3",
            Comments="Test comment",
            Grouping="Test group",
            Mix="Original",
            Label="Test Label",
            Remixer="Test Remixer"
        )
        track = parse_track_from_xml(track_elem)
        assert track is not None
        assert track.track_id == "1"
        assert track.title == "Test Song"
        assert track.artist == "Test Artist"
        assert track.album == "Test Album"
        assert track.duration == 180
        assert track.bpm == 128.5
        assert track.year == 2023
        assert track.key == "Am"
        assert track.genre == "House"
    
    def test_parse_track_from_xml_no_track_id(self):
        """Test parsing track without TrackID still works."""
        track_elem = self._create_track_xml(Name="Test Song")
        track = parse_track_from_xml(track_elem)
        assert track is not None
        assert track.title == "Test Song"
        assert track.track_id is None
    
    def test_parse_track_from_xml_invalid_numbers(self):
        """Test parsing track with invalid numeric values."""
        track_elem = self._create_track_xml(
            TrackID="1",
            Name="Test Song",
            TotalTime="invalid",
            AverageBpm="not_a_number",
            Year="bad_year",
            PlayCount="invalid_count",
            Rating="bad_rating"
        )
        track = parse_track_from_xml(track_elem)
        assert track is not None
        assert track.duration is None
        assert track.bpm is None
        assert track.year is None
    
    def test_parse_track_from_xml_file_path(self):
        """Test file path parsing from Location."""
        track_elem = self._create_track_xml(
            TrackID="1",
            Name="Test Song",
            Location="file:///Users/test/Music/song.mp3"
        )
        track = parse_track_from_xml(track_elem)
        assert track is not None
        assert track.file_path == Path("/Users/test/Music/song.mp3")


class TestCollectionTracks(RekordboxTestBase):
    """Test collection track extraction functions."""
    
    def test_get_collection_tracks_empty(self):
        """Test getting tracks from empty collection."""
        xml = self._create_collection_xml([])
        tracks = get_collection_tracks(xml)
        assert tracks == {}
    
    def test_get_collection_tracks_success(self):
        """Test successful track collection extraction."""
        tracks_data = [
            {"TrackID": "1", "Name": "Song 1", "Artist": "Artist 1"},
            {"TrackID": "2", "Name": "Song 2", "Artist": "Artist 2"}
        ]
        xml = self._create_collection_xml(tracks_data)
        tracks = get_collection_tracks(xml)
        assert len(tracks) == 2
        assert "1" in tracks
        assert "2" in tracks
        assert tracks["1"].title == "Song 1"
        assert tracks["2"].artist == "Artist 2"
    
    def test_get_collection_tracks_no_collection(self):
        """Test getting tracks when no COLLECTION element exists."""
        root = ET.Element("DJ_PLAYLISTS")
        xml = ET.ElementTree(root)
        tracks = get_collection_tracks(xml)
        assert tracks == {}


class TestPlaylistExtraction:
    """Test playlist extraction functions."""
    
    def create_playlist_xml(self):
        """Create playlist XML structure."""
        xml_content = """
        <DJ_PLAYLISTS>
            <PLAYLISTS>
                <NODE Name="Folder1" Type="0">
                    <NODE Name="Playlist1" Type="1" KeyID="1" Entries="2">
                        <TRACK Key="1"/>
                        <TRACK Key="2"/>
                    </NODE>
                    <NODE Name="Playlist2" Type="1" KeyID="2" Entries="1">
                        <TRACK Key="1"/>
                    </NODE>
                </NODE>
                <NODE Name="IgnoreMe" Type="1" KeyID="3" Entries="1">
                    <TRACK Key="3"/>
                </NODE>
            </PLAYLISTS>
        </DJ_PLAYLISTS>"""
        
        return ET.fromstring(xml_content)
    
    def test_get_playlists_success(self):
        """Test successful playlist extraction."""
        root = self.create_playlist_xml()
        xml = ET.ElementTree(root)
        
        playlists = get_playlists(xml)
        
        assert len(playlists) == 3
        assert "Playlist1" in playlists
        assert "Playlist2" in playlists
        assert "IgnoreMe" in playlists
        
        playlist1 = playlists["Playlist1"]
        assert playlist1.name == "Playlist1"
        assert playlist1.key_id == "1"
        assert playlist1.entries == 2
    
    def test_get_playlists_with_ignore_list(self):
        """Test playlist extraction with ignore list."""
        root = self.create_playlist_xml()
        xml = ET.ElementTree(root)
        
        playlists = get_playlists(xml, ignore_playlists=["IgnoreMe"])
        
        assert len(playlists) == 2
        assert "Playlist1" in playlists
        assert "Playlist2" in playlists
        assert "IgnoreMe" not in playlists
    
    def test_get_playlists_no_playlists_element(self):
        """Test playlist extraction when no PLAYLISTS element exists."""
        root = ET.Element("DJ_PLAYLISTS")
        xml = ET.ElementTree(root)
        
        playlists = get_playlists(xml)
        assert playlists == {}


class TestPlaylistTrackResolution:
    """Test playlist track resolution functions."""
    
    def test_get_tracks_from_playlist(self):
        """Test getting tracks from playlist."""
        # Create a playlist with track IDs
        playlist = RekordboxPlaylist(
            name="Test", 
            tracks=[], 
            entries=2,
            track_ids=["1", "2", "3"]  # Track 3 won't be found
        )
        
        # Create collection tracks
        collection_tracks = {
            "1": RekordboxTrack(title="Song 1", artist="Artist 1", track_id="1"),
            "2": RekordboxTrack(title="Song 2", artist="Artist 2", track_id="2")
        }
        
        tracks = get_tracks_from_playlist(playlist, collection_tracks)
        
        assert len(tracks) == 2
        assert tracks[0].title == "Song 1"
        assert tracks[1].title == "Song 2"
    
    def test_process_tracks_for_playlists(self):
        """Test processing tracks for multiple playlists."""
        # Create playlists
        playlist1 = RekordboxPlaylist(name="Test1", tracks=[], entries=1, track_ids=["1"])
        playlist2 = RekordboxPlaylist(name="Test2", tracks=[], entries=1, track_ids=["2"])
        
        playlists = {"Test1": playlist1, "Test2": playlist2}
        
        # Create collection tracks
        collection_tracks = {
            "1": RekordboxTrack(title="Song 1", artist="Artist 1", track_id="1"),
            "2": RekordboxTrack(title="Song 2", artist="Artist 2", track_id="2")
        }
        
        process_tracks_for_playlists(playlists, collection_tracks)
        
        assert len(playlist1.tracks) == 1
        assert len(playlist2.tracks) == 1
        assert playlist1.tracks[0].title == "Song 1"
        assert playlist2.tracks[0].title == "Song 2"


class TestTrackNormalization:
    """Test track metadata normalization functions."""
    
    def test_normalize_track_metadata_title_replacement(self):
        """Test title replacement normalization."""
        track = RekordboxTrack(
            title="Song (Original Mix)",
            artist="Artist",
            track_id="1"
        )
        
        config = type('Config', (), {
            'title_replacements': {'(Original Mix)': ''},
            'artist_exclusions': [],
            'extract_artist_from_title': False,
            'add_key_to_title': False,
            'remove_artist_from_title': False
        })()
        
        normalized = normalize_track_metadata(track, config)
        assert normalized.title == "Song"
    
    def test_normalize_track_metadata_artist_exclusion(self):
        """Test artist exclusion normalization."""
        track = RekordboxTrack(
            title="Song",
            artist="Artist feat. Someone",
            track_id="1"
        )
        
        config = type('Config', (), {
            'title_replacements': {},
            'artist_exclusions': ['feat.'],
            'extract_artist_from_title': False,
            'add_key_to_title': False,
            'remove_artist_from_title': False
        })()
        
        normalized = normalize_track_metadata(track, config)
        assert "feat." not in normalized.artist
    
    def test_normalize_track_metadata_artist_from_title(self):
        """Test extracting artist from title."""
        track = RekordboxTrack(
            title="Artist - Song Title",
            artist="",
            track_id="1"
        )
        
        config = type('Config', (), {
            'title_replacements': {},
            'artist_exclusions': [],
            'extract_artist_from_title': True,
            'add_key_to_title': False,
            'remove_artist_from_title': False
        })()
        
        normalized = normalize_track_metadata(track, config)
        assert normalized.artist == "Artist"
        assert normalized.title == "Song Title"
    
    def test_normalize_track_metadata_key_addition(self):
        """Test adding key to title."""
        track = RekordboxTrack(
            title="Song",
            artist="Artist",
            key="Am",
            track_id="1"
        )
        
        config = type('Config', (), {
            'title_replacements': {},
            'artist_exclusions': [],
            'extract_artist_from_title': False,
            'add_key_to_title': True,
            'remove_artist_from_title': False
        })()
        
        normalized = normalize_track_metadata(track, config)
        assert "Am" in normalized.title
    
    def test_normalize_track_metadata_artist_removal_from_title(self):
        """Test removing artist name from title."""
        track = RekordboxTrack(
            title="Artist - Song Title",
            artist="Artist",
            track_id="1"
        )
        
        config = type('Config', (), {
            'title_replacements': {},
            'artist_exclusions': [],
            'extract_artist_from_title': False,
            'add_key_to_title': False,
            'remove_artist_from_title': True
        })()
        
        normalized = normalize_track_metadata(track, config)
        assert normalized.title == "Song Title"


class TestRekordboxErrorHandling(RekordboxTestBase):
    """Test error handling in rekordbox functions."""
    
    @patch("pathlib.Path.exists", return_value=True)
    def test_load_rekordbox_library_permission_error(self, mock_exists):
        """Test load_rekordbox_library handling permission errors."""
        with patch('builtins.open', side_effect=PermissionError("Permission denied")):
            with pytest.raises(PermissionError):
                load_rekordbox_library(Path("test.xml"))
    
    @patch("pathlib.Path.exists", return_value=True)
    def test_load_rekordbox_library_corrupted_xml(self, mock_exists):
        """Test load_rekordbox_library handling corrupted XML."""
        corrupted_xml = "<INVALID><XML>Not closed properly"
        
        with patch('builtins.open', mock_open(read_data=corrupted_xml)):
            with pytest.raises(ET.ParseError):
                load_rekordbox_library(Path("corrupted.xml"))
    
    @patch("pathlib.Path.exists", return_value=True)
    def test_load_rekordbox_library_empty_file(self, mock_exists):
        """Test load_rekordbox_library handling empty files."""
        with patch('builtins.open', mock_open(read_data="")):
            with pytest.raises(ET.ParseError):
                load_rekordbox_library(Path("empty.xml"))
    
    def test_parse_track_from_xml_missing_required_fields(self):
        """Test parsing track with missing critical fields."""
        # Track without TrackID
        track_elem = ET.Element("TRACK")
        track_elem.set("Name", "Test Track")
        
        # Should handle missing TrackID gracefully
        track = parse_track_from_xml(track_elem)
        assert track.track_id is None  # Default value for missing attribute
    
    def test_get_collection_tracks_no_collection_element(self):
        """Test getting tracks when COLLECTION element is missing."""
        root = ET.Element("DJ_PLAYLISTS")
        # No COLLECTION element
        library_xml = ET.ElementTree(root)
        
        tracks = get_collection_tracks(library_xml)
        assert tracks == {}
    
    def test_get_playlists_no_playlists_element(self):
        """Test getting playlists when PLAYLISTS element is missing."""
        root = ET.Element("DJ_PLAYLISTS")
        # No PLAYLISTS element
        library_xml = ET.ElementTree(root)
        
        playlists = get_playlists(library_xml, [])
        assert playlists == {}
    
    def test_process_tracks_for_playlists_missing_track_ids(self):
        """Test processing playlists with missing track references."""
        collection_tracks = {
            "1": RekordboxTrack(track_id="1", title="Track 1", artist="Artist 1"),
            "2": RekordboxTrack(track_id="2", title="Track 2", artist="Artist 2")
        }
        
        playlists = {
            "test": RekordboxPlaylist(name="Test Playlist", track_ids=["1", "999"])  # 999 doesn't exist
        }
        
        # Function doesn't return anything, it modifies playlists in place
        process_tracks_for_playlists(playlists, collection_tracks)
        
        # Should only include existing tracks
        test_playlist = playlists["test"]
        assert len(test_playlist.tracks) == 1
        assert test_playlist.tracks[0].track_id == "1"
    
    def test_normalize_track_metadata_edge_cases(self):
        """Test track normalization with edge case data."""
        # Track with None/empty values
        track = RekordboxTrack(
            title="",
            artist=None,
            track_id="1"
        )
        
        config = type('Config', (), {
            'title_replacements': {},
            'artist_exclusions': [],
            'extract_artist_from_title': True,
            'add_key_to_title': True,
            'remove_artist_from_title': True
        })()
        
        # Should not crash with empty/None values
        normalized = normalize_track_metadata(track, config)
        assert normalized.title == ""
        assert normalized.artist == ""