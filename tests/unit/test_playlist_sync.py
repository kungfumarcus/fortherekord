"""
Tests for playlist synchronization service.

Tests the sync logic between Rekordbox and Spotify.
"""

import pytest
from unittest.mock import Mock, patch

from fortherekord.playlist_sync import PlaylistSyncService
from fortherekord.models import Playlist
from .conftest import create_track, silence_click_echo


def create_mock_spotify():
    """Create a mock Spotify library."""
    return Mock()


def create_service_with_config(mock_rekordbox):
    """Create a PlaylistSyncService with proper config and optional Spotify mocking."""
    spotify = create_mock_spotify()

    spotify.sp = Mock()
    spotify.user_id = "test_user"

    config = {"spotify": {"playlist_prefix": "test_"}}

    # Mock the mapping cache to ensure clean test execution
    with patch("fortherekord.playlist_sync.MappingCache") as mock_cache_class:
        mock_cache = Mock()
        mock_cache.get_mapping.return_value = None  # Always miss cache for clean tests
        mock_cache.set_mapping.return_value = None
        mock_cache.save_cache.return_value = None
        mock_cache_class.return_value = mock_cache

        service = PlaylistSyncService(mock_rekordbox, spotify, config)

    # Return both service and sp mock for convenient access
    return service, spotify.sp


class TestPlaylistSyncService:

    def test_comprehensive_playlist_sync(self, mock_rekordbox):
        """Test complete playlist sync including deletion,
        name cleaning, exclusion, and creation."""
        service, sp_mock = create_service_with_config(mock_rekordbox)
        service.exclude_from_playlist_names = ["mytags", "excluded"]

        # Mock existing Spotify playlists - one to delete, one to update
        empty_playlist = Mock()
        empty_playlist.name = "test_Delete Me"
        empty_playlist.id = "delete_me_id"

        existing_playlist = Mock()
        existing_playlist.name = "test_normal playlist"
        existing_playlist.id = "existing_id"

        service.spotify.get_playlists.return_value = [empty_playlist, existing_playlist]
        service.spotify.get_playlist_tracks.return_value = [create_track("old_track")]

        # Mock Rekordbox collection with various playlist scenarios
        # This track will have no matches and should cause deletion
        no_match_track = create_track("no_match_track")
        no_match_track.title = "no_match"
        no_match_track.artists = "no_match_artist"

        # This track will have matches
        match_track = create_track("match_track")
        match_track.title = "good_match"
        match_track.artists = "good_artist"

        # This playlist doesn't exist in Spotify and has no matches (should skip)
        skip_track = create_track("skip_track")
        skip_track.title = "skip_this"
        skip_track.artists = "skip_artist"

        playlist_to_delete = Playlist(id="1", name="Delete Me", tracks=[no_match_track])
        playlist_normal = Playlist(id="3", name="normal playlist", tracks=[match_track])
        playlist_to_skip = Playlist(id="4", name="Skip This", tracks=[skip_track])

        collection = Mock()
        collection.playlists = [playlist_to_delete, playlist_normal, playlist_to_skip]

        # Mock search results - no match for no_match and skip_this, matches for others
        def search_side_effect(title, artist, interactive=False):
            if title == "no_match" or title == "skip_this":
                return None
            return f"spotify_{title}"

        service.spotify.search_track.side_effect = search_side_effect
        sp_mock.user_playlist_create.return_value = {"id": "new_playlist_id"}
        service.spotify.sp.current_user_unfollow_playlist = Mock()

        # Test dry-run mode first (covers skip messages)
        with silence_click_echo():
            service.sync_collection(collection, dry_run=True)

        # Test normal mode
        with silence_click_echo():
            service.sync_collection(collection, dry_run=False)

        # Should delete playlist with no matches
        service.spotify.sp.current_user_unfollow_playlist.assert_called_with("delete_me_id")

        # Should not create new playlists since they exist and have matches, or should be skipped
        sp_mock.user_playlist_create.assert_not_called()

        # Should update existing playlists
        sp_mock.playlist_add_items.assert_called()

    def test_name_cleaning_and_creation(self, mock_rekordbox):
        """Test playlist name cleaning during creation."""
        service, sp_mock = create_service_with_config(mock_rekordbox)
        # Don't set exclusion terms here - just test the cleaning function directly

        # No existing playlists
        service.spotify.get_playlists.return_value = []

        # Normal playlist that won't be excluded
        normal_playlist = Playlist(id="1", name="deep house", tracks=[create_track("track1")])
        collection = Mock()
        collection.playlists = [normal_playlist]

        # Mock successful search
        service.spotify.search_track.return_value = "spotify_track_id"
        sp_mock.user_playlist_create.return_value = {"id": "new_playlist_id"}

        with silence_click_echo():
            service.sync_collection(collection)

        # Should create playlist normally (no cleaning needed)
        sp_mock.user_playlist_create.assert_called_once_with(
            user="test_user", name="test_deep house", public=False
        )

    def test_name_cleaning_functionality(self, mock_rekordbox):
        """Test playlist name cleaning with various scenarios."""
        service, _ = create_service_with_config(mock_rekordbox)
        service.exclude_from_playlist_names = ["mytags", "test"]

        # Test various cleaning scenarios
        assert service._clean_playlist_name("deep house mytags") == "deep house"
        assert service._clean_playlist_name("mytags deep house") == "deep house"
        assert service._clean_playlist_name("deep mytags house") == "deep house"
        assert service._clean_playlist_name("deep house mytags test") == "deep house"
        assert service._clean_playlist_name("deep house") == "deep house"
        assert service._clean_playlist_name("deep  house   mytags") == "deep house"

    def test_recursive_playlist_collection_and_exclusion(self, mock_rekordbox):
        """Test recursive playlist collection with filtering and exclusion."""
        service, _ = create_service_with_config(mock_rekordbox)
        service.exclude_from_playlist_names = ["exclude"]

        # Create nested playlist structure
        child1 = Playlist(id="child1", name="Child 1", tracks=[create_track("track1")])
        child2 = Playlist(id="child2", name="Child 2 exclude", tracks=[create_track("track2")])
        child3 = Playlist(id="child3", name="Empty Child", tracks=[])

        parent1 = Playlist(
            id="parent1", name="Parent exclude", tracks=[create_track("track3")], children=[child1]
        )
        parent2 = Playlist(id="parent2", name="Empty Parent", tracks=[], children=[child2, child3])
        parent3 = Playlist(id="parent3", name="Normal Parent", tracks=[create_track("track4")])

        playlists = [parent1, parent2, parent3]
        result = service._get_all_playlists_recursive(playlists)

        # Should include: child1 (normal), parent3 (normal)
        # Should exclude: child2 (excluded term), child3 (empty),
        # parent1 (excluded term), parent2 (empty)
        assert len(result) == 2
        playlist_names = [p.name for p in result]
        assert "Child 1" in playlist_names
        assert "Normal Parent" in playlist_names

    def test_comprehensive_dry_run_mode(self, mock_rekordbox, sample_collection):
        """Test all dry-run functionality in one comprehensive test."""
        service, sp_mock = create_service_with_config(mock_rekordbox)

        # Mock existing Spotify playlist
        existing_playlist = Mock()
        existing_playlist.name = "test_Test Playlist"
        existing_playlist.id = "existing_playlist_id"
        existing_playlist.tracks = []
        service.spotify.get_playlists.return_value = [existing_playlist]
        service.spotify.get_playlist_tracks.return_value = []
        service.spotify.search_track.return_value = "spotify_track_id"

        with silence_click_echo():
            # Test collection sync in dry-run
            service.sync_collection(sample_collection, dry_run=True)

            # Test individual methods in dry-run
            service._create_spotify_playlist("Test Playlist", ["track1"], dry_run=True)
            service._update_spotify_playlist(existing_playlist, ["track1"], dry_run=True)
            result = service._find_spotify_matches([create_track("track1")], "", dry_run=True)

        # Verify search still works but no API calls are made
        assert result == ["spotify_track_id"]
        service.spotify.get_playlists.assert_called()  # Should still check playlists
        # Should not make any modification calls
        sp_mock.user_playlist_create.assert_not_called()
        sp_mock.playlist_add_items.assert_not_called()
        sp_mock.playlist_remove_all_occurrences_of_items.assert_not_called()

    def test_playlist_deletion_scenarios(self, mock_rekordbox):
        """Test playlist deletion in dry-run and normal modes."""
        service, sp_mock = create_service_with_config(mock_rekordbox)

        # Mock existing playlist to delete
        existing_playlist = Mock()
        existing_playlist.name = "test_Delete Me"
        existing_playlist.id = "delete_me_id"
        service.spotify.get_playlists.return_value = [existing_playlist]

        # Playlist with no matching tracks
        no_match_track = create_track("no_match")
        no_match_track.title = "no_match"
        no_match_track.artists = "no_artist"
        playlist_no_matches = Playlist(id="1", name="Delete Me", tracks=[no_match_track])

        collection = Mock()
        collection.playlists = [playlist_no_matches]

        # Test dry-run deletion message
        service.spotify.search_track.return_value = None
        service.spotify.sp.current_user_unfollow_playlist = Mock()

        with silence_click_echo():
            service.sync_collection(collection, dry_run=True)

        # Should not actually delete in dry-run
        service.spotify.sp.current_user_unfollow_playlist.assert_not_called()

        # Test actual deletion
        with silence_click_echo():
            service.sync_collection(collection, dry_run=False)

        # Should delete in normal mode
        service.spotify.sp.current_user_unfollow_playlist.assert_called_once_with("delete_me_id")

        # Test authentication error during deletion
        service.spotify.sp = None  # Simulate unauthenticated state
        service.spotify.get_playlists.return_value = [existing_playlist]  # Reset
        service.spotify.sp = Mock()
        service.spotify.sp.current_user_unfollow_playlist = Mock()
        service.spotify.user_id = None  # No user_id

        collection.playlists = [playlist_no_matches]  # Reset
        service.spotify.search_track.return_value = None  # No matches

        with pytest.raises(RuntimeError, match="Spotify client not authenticated"):
            with silence_click_echo():
                service.sync_collection(collection, dry_run=False)

    def test_track_matching_detailed_output(self, mock_rekordbox):
        """Test track matching with detailed error output for non-dry-run and small playlists."""
        service, _ = create_service_with_config(mock_rekordbox)

        # Test 1: Large playlist (>5 tracks) with progress bar
        large_tracks = []
        for i in range(7):  # 7 tracks to trigger progress bar
            track = create_track(f"track{i}")
            track.title = f"Song {i}"
            track.artists = f"Artist {i}"
            large_tracks.append(track)

        # Mock search - some match, some don't
        def search_side_effect(title, artist, interactive=False):
            if "Song 0" in title or "Song 1" in title:
                return f"spotify_{title.replace(' ', '_')}"
            return None

        service.spotify.search_track.side_effect = search_side_effect

        with silence_click_echo():
            result = service._find_spotify_matches(large_tracks, "", dry_run=False)

        # Should return only matching tracks
        assert len(result) == 2
        assert "spotify_Song_0" in result
        assert "spotify_Song_1" in result

        # Test 2: Small playlist (≤5 tracks) without progress bar and with detailed errors
        small_tracks = []
        for i in range(3):  # 3 tracks to avoid progress bar
            track = create_track(f"small_track{i}")
            track.title = f"Small Song {i}"
            track.artists = f"Small Artist {i}"
            small_tracks.append(track)

        # Reset mock and make only first track match
        service.spotify.search_track.reset_mock()

        def small_search_side_effect(title, artist, interactive=False):
            if "Small Song 0" in title:
                return "spotify_small_song_0"
            return None  # No matches for others

        service.spotify.search_track.side_effect = small_search_side_effect

        # Test with detailed error output (not dry-run) for small playlist
        with silence_click_echo():
            result = service._find_spotify_matches(small_tracks, "", dry_run=False)

        # Should return only the matching track
        assert result == ["spotify_small_song_0"]

        # Test 3: Same small playlist in dry-run (no detailed errors)
        service.spotify.search_track.reset_mock()
        service.spotify.search_track.side_effect = small_search_side_effect

        with silence_click_echo():
            result = service._find_spotify_matches(small_tracks, "", dry_run=True)

        # Should still return only matching tracks
        assert result == ["spotify_small_song_0"]

    def test_spotify_matching_and_batching(self, mock_rekordbox):
        """Test Spotify track matching and batch operations."""
        service, sp_mock = create_service_with_config(mock_rekordbox)

        # Test track matching
        tracks = [
            create_track(track_id="1", title="Found Song", artists="Found Artist"),
            create_track(track_id="2", title="Lost Song", artists="Lost Artist"),
        ]
        service.spotify.search_track.side_effect = ["spotify_id_1", None]

        with silence_click_echo():
            result = service._find_spotify_matches(tracks, base_line="")

        assert result == ["spotify_id_1"]
        assert service.spotify.search_track.call_count == 2

        # Test batch adding (150 tracks = 2 batches)
        track_ids = [f"track_{i}" for i in range(150)]
        service._add_tracks_to_playlist("playlist_id", track_ids)
        assert sp_mock.playlist_add_items.call_count == 2
        assert len(sp_mock.playlist_add_items.call_args_list[0][0][1]) == 100
        assert len(sp_mock.playlist_add_items.call_args_list[1][0][1]) == 50

        # Reset mock for batch removal test
        sp_mock.reset_mock()

        # Test batch removal
        service._remove_tracks_from_playlist("playlist_id", track_ids)
        assert sp_mock.playlist_remove_all_occurrences_of_items.call_count == 2

    def test_playlist_updates_and_creation(self, mock_rekordbox, sample_collection):
        """Test playlist creation and updating logic."""
        service, sp_mock = create_service_with_config(mock_rekordbox)

        # Test creating new playlist
        sp_mock.user_playlist_create.return_value = {"id": "new_playlist_id"}
        track_ids = ["track_1", "track_2", "track_3"]

        with silence_click_echo():
            service._create_spotify_playlist("New Playlist", track_ids)

        sp_mock.user_playlist_create.assert_called_once_with(
            user="test_user", name="New Playlist", public=False
        )
        sp_mock.playlist_add_items.assert_called_once_with("new_playlist_id", track_ids)

        # Test updating existing playlist
        sp_mock.reset_mock()
        existing_playlist = Playlist(id="existing_id", name="Existing Playlist", tracks=[])
        current_tracks = [
            create_track(track_id="keep_track", title="Keep", artists="Artist"),
            create_track(track_id="remove_track", title="Remove", artists="Artist"),
        ]
        service.spotify.get_playlist_tracks.return_value = current_tracks
        new_track_ids = ["keep_track", "add_track"]

        with silence_click_echo():
            service._update_spotify_playlist(existing_playlist, new_track_ids)

        sp_mock.playlist_remove_all_occurrences_of_items.assert_called_once_with(
            "existing_id", ["remove_track"]
        )
        sp_mock.playlist_add_items.assert_called_once_with("existing_id", ["add_track"])

        # Test syncing when playlist already exists
        sp_mock.reset_mock()
        existing_spotify = Mock()
        existing_spotify.name = "test_Test Playlist"
        existing_spotify.id = "existing_spotify_id"
        service.spotify.get_playlists.return_value = [existing_spotify]
        service.spotify.get_playlist_tracks.return_value = []

        with silence_click_echo():
            service.sync_collection(sample_collection)

        sp_mock.user_playlist_create.assert_not_called()  # Should update, not create

    def test_initialization_and_configuration(self, mock_rekordbox):
        """Test service initialization and configuration validation."""
        # Test successful initialization
        service, _ = create_service_with_config(mock_rekordbox)
        assert service.rekordbox == mock_rekordbox
        assert service.spotify is not None
        assert service.playlist_prefix == "test_"

        # Test missing prefix
        spotify = create_mock_spotify()
        config = {"spotify": {}}
        with pytest.raises(ValueError, match="spotify.playlist_prefix is required"):
            PlaylistSyncService(mock_rekordbox, spotify, config)

        # Test None config
        with pytest.raises(ValueError, match="spotify.playlist_prefix is required"):
            PlaylistSyncService(mock_rekordbox, spotify, None)


class TestPlaylistSyncServiceErrorConditions:
    """Test error conditions in playlist sync service."""

    def test_authentication_errors(self, mock_rekordbox):
        """Test all authentication error scenarios."""
        service, _ = create_service_with_config(mock_rekordbox)
        service.spotify.sp = None  # Not authenticated
        service.spotify.user_id = None

        # Test playlist creation
        with pytest.raises(RuntimeError, match="Spotify client not authenticated"):
            service._create_spotify_playlist("Test Playlist", ["track1", "track2"])

        # Test adding tracks
        with pytest.raises(RuntimeError, match="Spotify client not authenticated"):
            service._add_tracks_to_playlist("playlist_id", ["track1", "track2"])

        # Test removing tracks
        with pytest.raises(RuntimeError, match="Spotify client not authenticated"):
            service._remove_tracks_from_playlist("playlist_id", ["track1", "track2"])

    def test_sync_single_playlist_with_progress(self, mock_rekordbox):
        """Test _sync_single_playlist with Progress object."""
        service, sp_mock = create_service_with_config(mock_rekordbox)

        # Create a simple playlist with one track
        playlist = Playlist(id="playlist1", name="test", tracks=[])
        track = create_track("track1")
        track.title = "Test Song"
        track.artists = "Test Artist"
        playlist.tracks = [track]

        # Mock Spotify search to return a track
        service.spotify.search_track.return_value = "spotify_track_id"

        # Mock existing Spotify playlists
        spotify_playlists = {}

        # Create progress object
        from fortherekord.playlist_sync import Progress

        progress = Progress(1, 2)

        with silence_click_echo():
            # Call with explicit progress object
            service._sync_single_playlist(playlist, spotify_playlists, progress, dry_run=True)

        # Verify the search was called
        service.spotify.search_track.assert_called_once_with("Test Song", "Test Artist", False)

    def test_find_spotify_matches_cached_not_found(self, mock_rekordbox):
        """Test _find_spotify_matches with cached 'not found' entries to cover cache miss."""
        service, sp_mock = create_service_with_config(mock_rekordbox)

        # Create tracks
        track1 = create_track("track1")
        track1.title = "Found Song"
        track1.artists = "Found Artist"

        track2 = create_track("track2")
        track2.title = "Not Found Song"
        track2.artists = "Not Found Artist"

        track3 = create_track("track3")
        track3.title = "Cached Not Found Song"
        track3.artists = "Cached Not Found Artist"

        tracks = [track1, track2, track3]

        # Mock the cache to return different scenarios
        def mock_should_remap(track_id, force):
            return track_id == "track2"  # Only track2 needs remapping

        def mock_get_mapping(track_id):
            if track_id == "track1":
                # Mock a cached successful mapping
                mock_entry = Mock()
                mock_entry.target_track_id = "spotify_track1"
                return mock_entry
            elif track_id == "track3":
                # Mock a cached "not found" entry (target_track_id is None)
                mock_entry = Mock()
                mock_entry.target_track_id = None
                return mock_entry
            return None  # track2 not in cache

        service.mapping_cache.should_remap.side_effect = mock_should_remap
        service.mapping_cache.get_mapping.side_effect = mock_get_mapping

        # Mock search to return None for track2 (not found)
        service.spotify.search_track.return_value = None

        with silence_click_echo():
            result = service._find_spotify_matches(tracks, dry_run=True, base_line="test")

        # Should only return track1 (from cache), track3 should be skipped due to cached "not found"
        assert result == ["spotify_track1"]

        # Verify search was called only for track2
        service.spotify.search_track.assert_called_once_with(
            "Not Found Song", "Not Found Artist", False
        )


def test_sync_collection_orphaned_playlist_cleanup(mock_rekordbox):
    """Test orphaned playlist cleanup functionality."""
    service, sp_mock = create_service_with_config(mock_rekordbox)

    # Create a collection with one playlist
    playlist = Playlist(id="1", name="Existing Playlist", tracks=[])
    collection = Mock()
    collection.playlists = [playlist]

    # Mock Spotify playlists - include one orphaned playlist with our prefix
    existing_playlist = Playlist(id="sp1", name="test_Existing Playlist", tracks=[])
    orphaned_playlist = Playlist(id="orphaned_id", name="test_Orphaned Playlist", tracks=[])
    non_prefix_playlist = Playlist(id="sp3", name="Other Playlist", tracks=[])

    service.spotify.get_playlists.return_value = [
        existing_playlist,
        orphaned_playlist,
        non_prefix_playlist,
    ]

    # Test dry run - no actual deletion
    with silence_click_echo():
        service.sync_collection(collection, dry_run=True)
    sp_mock.current_user_unfollow_playlist.assert_not_called()

    # Test real run - should delete orphaned playlist
    service.spotify.sp = sp_mock
    service.spotify.user_id = "test_user"

    with silence_click_echo():
        service.sync_collection(collection, dry_run=False)

    # Verify both orphaned playlists were deleted
    # (existing_playlist doesn't match any rekordbox playlist)
    assert sp_mock.current_user_unfollow_playlist.call_count == 2
    sp_mock.current_user_unfollow_playlist.assert_any_call("sp1")
    sp_mock.current_user_unfollow_playlist.assert_any_call("orphaned_id")

    # Test authentication error case - reset mock and remove auth
    sp_mock.reset_mock()
    service.spotify.sp = None
    service.spotify.user_id = None

    with silence_click_echo():
        with pytest.raises(RuntimeError, match="Spotify client not authenticated"):
            service.sync_collection(collection, dry_run=False)


def test_interactive_save_command_handling(mock_rekordbox):
    """Test that save command in interactive mode is handled correctly."""
    service, _ = create_service_with_config(mock_rekordbox)

    # Create a track to search
    track = create_track("test_track")
    track.title = "Test Song"
    track.artists = "Test Artist"

    # Mock search_track to return save command first, then normal result
    service.spotify.search_track.side_effect = ["__SAVE_CACHE__", "spotify_id_123"]

    # Ensure the track will be searched (force should_remap to return True)
    service.mapping_cache.should_remap.return_value = True

    result = service._find_spotify_matches(
        [track], dry_run=False, base_line="Testing", interactive=True
    )

    # Should have processed the save command and then returned the track ID
    assert result == ["spotify_id_123"]

    # Should have called search_track twice (once for save, once for actual selection)
    assert service.spotify.search_track.call_count == 2

    # Should have called save_cache twice (once for save command, once at end)
    assert service.mapping_cache.save_cache.call_count == 2


class TestCacheClearance:
    """Test cache clearing functionality."""

    def test_clear_cache_all_mappings(self, mock_rekordbox):
        """Test clearing all mappings from cache."""
        service, _ = create_service_with_config(mock_rekordbox)
        service.mapping_cache.clear_all_mappings.return_value = 5

        with silence_click_echo():
            service.clear_cache()

        service.mapping_cache.clear_all_mappings.assert_called_once()

    def test_clear_cache_by_algorithm(self, mock_rekordbox):
        """Test clearing mappings by specific algorithm."""
        service, _ = create_service_with_config(mock_rekordbox)
        service.mapping_cache.clear_mappings_by_algorithm.return_value = 3

        with silence_click_echo():
            service.clear_cache("fuzzy")

        service.mapping_cache.clear_mappings_by_algorithm.assert_called_once_with("fuzzy")


class TestInteractiveMode:
    """Test interactive mode functionality."""

    def test_sync_collection_interactive_display(self, mock_rekordbox):
        """Test interactive mode display in sync_collection."""
        service, sp_mock = create_service_with_config(mock_rekordbox)

        # Create a simple collection with one playlist
        from fortherekord.models import Collection, Playlist

        track = create_track("test_track")
        playlist = Playlist("Test Playlist", "PL1", [track])
        collection = Collection.from_playlists([playlist])

        # Mock Spotify responses
        service.spotify.get_playlists.return_value = []
        sp_mock.user_playlist_create.return_value = {"id": "new_playlist_id"}

        # Mock search to return a result immediately
        service.spotify.search_track.return_value = "spotify_track_id"

        # Call sync_collection in interactive mode
        with silence_click_echo():
            service.sync_collection(collection, dry_run=False, interactive=True)

        # Verify that the sync completed (this covers the interactive display code)
        sp_mock.user_playlist_create.assert_called_once()
