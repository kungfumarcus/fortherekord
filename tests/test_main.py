"""
Tests for main CLI interface.

Tests the simplified CLI without config creation flags.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from click.testing import CliRunner

from fortherekord.main import main, display_progress, interactive_mode


class MainTestBase:
    """Base class with shared test setup for main CLI tests."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
    
    def _create_mock_config(self):
        """Create a mock config object."""
        from fortherekord.config import Config, SpotifyConfig, RekordboxConfig
        return Config(
            rekordbox=RekordboxConfig(library_path="test_library.xml"),
            spotify=SpotifyConfig(client_id="test_id", client_secret="test_secret")
        )
    
    def _create_invalid_config(self):
        """Create an invalid config object."""
        from fortherekord.config import Config, SpotifyConfig, RekordboxConfig
        return Config(
            rekordbox=RekordboxConfig(library_path=""),
            spotify=SpotifyConfig(client_id="", client_secret="")
        )

    def _create_valid_config(self):
        """Create a valid config object."""
        from fortherekord.config import Config, SpotifyConfig, RekordboxConfig, MatchingConfig
        return Config(
            rekordbox=RekordboxConfig(library_path="/valid/path.xml"),
            spotify=SpotifyConfig(client_id="valid_id", client_secret="valid_secret"),
            matching=MatchingConfig(similarity_threshold=0.8, boost_liked_tracks=1.5)
        )


class TestDisplayProgress:
    """Test progress display functionality."""
    
    def test_display_progress_basic(self, capsys):
        """Test basic progress display."""
        display_progress(50, 100, "Processing")
        captured = capsys.readouterr()
        assert "Processing: 50/100 (50.0%)" in captured.out
    
    def test_display_progress_custom_prefix(self, capsys):
        """Test progress display with custom prefix."""
        display_progress(25, 50, "Loading")
        captured = capsys.readouterr()
        assert "Loading: 25/50 (50.0%)" in captured.out
    
    def test_display_progress_zero_total(self, capsys):
        """Test progress display with zero total."""
        display_progress(5, 0, "Counting")
        captured = capsys.readouterr()
        assert "Counting: 5" in captured.out
    
    def test_display_progress_complete(self, capsys):
        """Test progress display when complete."""
        display_progress(100, 100, "Done")
        captured = capsys.readouterr()
        assert "Done: 100/100 (100.0%)" in captured.out


class TestInteractiveMode:
    """Test interactive mode functionality."""
    
    def test_interactive_mode_placeholder(self):
        """Test interactive mode placeholder implementation."""
        result = interactive_mode()
        assert result is False


class TestMainCLI(MainTestBase):
    """Test main CLI command."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "config.yaml"
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_test_config(self, valid=True):
        """Create a test configuration file."""
        if valid:
            config_content = """
rekordbox:
  library_path: "/path/to/test.xml"
spotify:
  client_id: "test_client_id"
  client_secret: "test_client_secret"
matching:
  similarity_threshold: 0.8
  boost_liked_tracks: 1.5
"""
        else:
            config_content = """
invalid_yaml: [
"""
        
        with open(self.config_path, 'w') as f:
            f.write(config_content)
    
    def test_main_help(self):
        """Test main command help."""
        result = self.runner.invoke(main, ['--help'])
        assert result.exit_code == 0
        assert "ForTheRekord" in result.output
    
    def test_main_version(self):
        """Test main command version."""
        result = self.runner.invoke(main, ['--version'])
        assert result.exit_code == 0
    
    @patch('fortherekord.main.load_config')
    def test_main_auto_creates_config(self, mock_load_config):
        """Test that main auto-creates config if it doesn't exist."""
        mock_load_config.return_value = self._create_invalid_config()
        
        result = self.runner.invoke(main, ['--verbose'])
        assert result.exit_code == 1  # Should exit due to invalid config
        assert mock_load_config.called
    
    @patch('fortherekord.main.validate_config')
    @patch('fortherekord.main.load_config')
    def test_main_with_invalid_config(self, mock_load_config, mock_validate_config):
        """Test main command with invalid configuration."""
        mock_load_config.return_value = self._create_invalid_config()
        mock_validate_config.return_value = ["Missing client_id", "Missing library_path"]
        
        result = self.runner.invoke(main, ['--verbose'])
        assert result.exit_code == 1
        assert "Configuration errors found" in result.output
    
    @patch('fortherekord.main.load_rekordbox_library')
    @patch('fortherekord.main.SpotifyClient')
    @patch('fortherekord.main.validate_config')
    @patch('fortherekord.main.load_config')
    def test_main_with_valid_config(self, mock_load_config, mock_validate_config, 
                                   mock_spotify_client, mock_parse_library):
        """Test main command with valid configuration."""
        # Mock valid config
        mock_load_config.return_value = self._create_valid_config()
        mock_validate_config.return_value = []  # No errors
        
        # Mock library parsing
        mock_parse_library.return_value = ([], [])  # Empty tracks and playlists
        
        # Mock Spotify client
        mock_client = Mock()
        mock_client.user_id = "test_user"
        mock_client.get_saved_tracks.return_value = []
        mock_client.get_user_playlists.return_value = []
        mock_spotify_client.return_value = mock_client
        
        result = self.runner.invoke(main, ['--verbose'])
        assert result.exit_code == 0
        assert "Starting ForTheRekord synchronization" in result.output
    
    def test_main_with_flags(self):
        """Test main command with various flags."""
        result = self.runner.invoke(main, [
            '--unmapped',
            '--remap',
            '--use-cache',
            '--interactive',
            '--verbose'
        ])
        # Should still try to load config and fail with validation errors
        assert result.exit_code == 1
    
    @patch('fortherekord.main.validate_config')
    @patch('fortherekord.main.load_config')
    def test_main_verbose_output(self, mock_load_config, mock_validate_config):
        """Test verbose output includes additional information."""
        from fortherekord.config import Config, SpotifyConfig, RekordboxConfig
        mock_load_config.return_value = Config(
            rekordbox=RekordboxConfig(library_path=""),
            spotify=SpotifyConfig(client_id="", client_secret="")
        )
        mock_validate_config.return_value = ["Test error"]
        
        result = self.runner.invoke(main, ['--verbose'])
        assert result.exit_code == 1
        assert "Loaded configuration" in result.output
    
    @patch('fortherekord.main.SpotifyClient')
    @patch('fortherekord.main.load_rekordbox_library')
    @patch('fortherekord.main.validate_config')
    @patch('fortherekord.main.load_config')
    def test_main_keyboard_interrupt(self, mock_load_config, mock_validate_config,
                                   mock_parse_library, mock_spotify_client):
        """Test main command with keyboard interrupt."""
        from fortherekord.config import Config, SpotifyConfig, RekordboxConfig, MatchingConfig
        
        mock_load_config.return_value = Config(
            rekordbox=RekordboxConfig(library_path="/valid/path.xml"),
            spotify=SpotifyConfig(client_id="valid_id", client_secret="valid_secret"),
            matching=MatchingConfig(similarity_threshold=0.8, boost_liked_tracks=1.5)
        )
        mock_validate_config.return_value = []
        
        # Make load_rekordbox_library raise KeyboardInterrupt
        mock_parse_library.side_effect = KeyboardInterrupt()
        
        result = self.runner.invoke(main, [])
        assert result.exit_code == 1
        assert "Synchronization cancelled by user" in result.output
    
    @patch('fortherekord.main.SpotifyClient')
    @patch('fortherekord.main.load_rekordbox_library')
    @patch('fortherekord.main.validate_config')
    @patch('fortherekord.main.load_config')
    def test_main_exception_handling(self, mock_load_config, mock_validate_config,
                                   mock_parse_library, mock_spotify_client):
        """Test main command handles general exceptions."""
        from fortherekord.config import Config, SpotifyConfig, RekordboxConfig, MatchingConfig
        
        mock_load_config.return_value = Config(
            rekordbox=RekordboxConfig(library_path="/valid/path.xml"),
            spotify=SpotifyConfig(client_id="valid_id", client_secret="valid_secret"),
            matching=MatchingConfig(similarity_threshold=0.8, boost_liked_tracks=1.5)
        )
        mock_validate_config.return_value = []
        
        # Make load_rekordbox_library raise a general exception
        mock_parse_library.side_effect = Exception("Test error")
        
        result = self.runner.invoke(main, ['--verbose'])
        assert result.exit_code == 1
        assert "Error during synchronization" in result.output


class TestCLIWorkflow(MainTestBase):
    """Test complete CLI workflows."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
    
    @patch('fortherekord.main.validate_config')
    @patch('fortherekord.main.load_config')
    def test_config_auto_creation_workflow(self, mock_load_config, mock_validate_config):
        """Test that config is auto-created and user is prompted to edit."""
        from fortherekord.config import Config, SpotifyConfig, RekordboxConfig
        
        # Simulate auto-creation returning basic config
        mock_load_config.return_value = Config(
            rekordbox=RekordboxConfig(library_path=""),
            spotify=SpotifyConfig(client_id="", client_secret="")
        )
        mock_validate_config.return_value = ["Configuration needs to be edited"]
        
        result = self.runner.invoke(main, [])
        assert result.exit_code == 1
        assert mock_load_config.called
    
    def test_help_and_version_commands(self):
        """Test basic help and version commands work."""
        # Test help
        help_result = self.runner.invoke(main, ['--help'])
        assert help_result.exit_code == 0
        assert "Usage:" in help_result.output
        
        # Test version
        version_result = self.runner.invoke(main, ['--version'])
        assert version_result.exit_code == 0


class TestMainWorkflow(MainTestBase):
    """Test the main synchronization workflow."""
    
    @patch('fortherekord.main.load_config')
    @patch('fortherekord.main.validate_config')
    @patch('fortherekord.main.load_rekordbox_library')
    @patch('fortherekord.main.SpotifyClient')
    def test_main_workflow_execution_success(self, mock_spotify_client, mock_load_library,
                                           mock_validate_config, mock_load_config):
        """Test successful execution of main sync workflow."""
        # Setup mocks
        mock_load_config.return_value = self._create_valid_config()
        mock_validate_config.return_value = []  # No validation errors
        
        # Mock library data
        mock_load_library.return_value = (
            [{'track_id': '1', 'title': 'Test Track', 'artist': 'Test Artist'}],
            [{'name': 'Test Playlist', 'track_ids': ['1']}]
        )
        
        # Mock Spotify client
        mock_client_instance = MagicMock()
        mock_client_instance.get_saved_tracks.return_value = []
        mock_client_instance.get_user_playlists.return_value = []
        mock_client_instance.create_playlist.return_value = {'playlist_id': 'test_id', 'name': 'rb_Test Playlist'}
        mock_client_instance.replace_playlist_tracks.return_value = None
        mock_spotify_client.return_value = mock_client_instance
        
        # Run main workflow
        result = self.runner.invoke(main, [])
        
        # Should complete successfully
        if result.exit_code != 0:
            print(f"Command failed with exit code {result.exit_code}")
            print(f"Output: {result.output}")
            print(f"Exception: {result.exception}")
        
        assert result.exit_code == 0
        assert "Sync completed" in result.output
    
    @patch('fortherekord.main.load_config')
    @patch('fortherekord.main.validate_config')
    def test_main_workflow_keyboard_interrupt(self, mock_validate_config, mock_load_config):
        """Test that KeyboardInterrupt is handled gracefully."""
        mock_load_config.return_value = self._create_valid_config()
        mock_validate_config.return_value = []
        
        # Mock library loading to raise KeyboardInterrupt
        with patch('fortherekord.main.load_rekordbox_library', side_effect=KeyboardInterrupt):
            result = self.runner.invoke(main, [])
            
            assert result.exit_code == 1
            assert "cancelled by user" in result.output
    
    @patch('fortherekord.main.load_config')
    @patch('fortherekord.main.validate_config')
    def test_main_workflow_exception_handling(self, mock_validate_config, mock_load_config):
        """Test that general exceptions are handled properly."""
        mock_load_config.return_value = self._create_valid_config()
        mock_validate_config.return_value = []
        
        # Mock library loading to raise a general exception
        with patch('fortherekord.main.load_rekordbox_library', side_effect=Exception("Test error")):
            result = self.runner.invoke(main, [])
            
            assert result.exit_code == 1
            assert "Error during synchronization" in result.output
    
    @patch('fortherekord.main.load_config')
    @patch('fortherekord.main.validate_config')
    def test_main_workflow_exception_handling_verbose(self, mock_validate_config, mock_load_config):
        """Test that verbose mode shows full traceback on errors."""
        mock_load_config.return_value = self._create_valid_config()
        mock_validate_config.return_value = []
        
        # Mock library loading to raise a general exception
        with patch('fortherekord.main.load_rekordbox_library', side_effect=Exception("Test error")):
            result = self.runner.invoke(main, ['--verbose'])
            
            assert result.exit_code == 1
            assert "Error during synchronization" in result.output
    
    @patch('fortherekord.main.load_config')
    @patch('fortherekord.main.validate_config')
    @patch('fortherekord.main.load_rekordbox_library')
    @patch('fortherekord.main.SpotifyClient')
    def test_playlist_processing_with_ignore_list(self, mock_spotify_client, mock_load_library,
                                                mock_validate_config, mock_load_config):
        """Test that ignored playlists are skipped."""
        # Create config with ignored playlists
        config = self._create_valid_config()
        config.spotify.ignore_playlists = ['ignored_playlist']
        mock_load_config.return_value = config
        mock_validate_config.return_value = []
        
        # Mock library with ignored playlist
        mock_load_library.return_value = (
            [{'track_id': '1', 'title': 'Test Track', 'artist': 'Test Artist'}],
            [
                {'name': 'ignored_playlist', 'track_ids': ['1']},
                {'name': 'normal_playlist', 'track_ids': ['1']}
            ]
        )
        
        # Mock Spotify client
        mock_client_instance = MagicMock()
        mock_client_instance.get_saved_tracks.return_value = []
        mock_client_instance.get_user_playlists.return_value = []
        mock_client_instance.create_playlist.return_value = {'playlist_id': 'test_id', 'name': 'rb_normal_playlist'}
        mock_spotify_client.return_value = mock_client_instance
        
        result = self.runner.invoke(main, [])
        
        # Should only process the non-ignored playlist
        assert result.exit_code == 0
        assert "normal_playlist" in result.output
        # The ignored playlist should not trigger a create_playlist call
        mock_client_instance.create_playlist.assert_called_once()
