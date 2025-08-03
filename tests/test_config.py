"""
Unit tests for configuration management.

Tests for config.py module functions.
"""

import pytest
import tempfile
import yaml
from pathlib import Path
from unittest.mock import patch, mock_open

from fortherekord.config import (
    Config, RekordboxConfig, SpotifyConfig, TextProcessingConfig,
    PlaylistsConfig, MatchingConfig, TextReplacement,
    get_config_path, load_config, save_config, create_example_config,
    validate_config
)


class TestConfigModels:
    """Test configuration model classes."""
    
    def test_text_replacement_creation(self):
        """Test TextReplacement model creation."""
        replacement = TextReplacement(from_text=" (Original Mix)", to="")
        assert replacement.from_text == " (Original Mix)"
        assert replacement.to == ""
    
    def test_text_replacement_with_alias(self):
        """Test TextReplacement with field alias."""
        data = {"from": " (Original Mix)", "to": ""}
        replacement = TextReplacement(**data)
        assert replacement.from_text == " (Original Mix)"
        assert replacement.to == ""
    
    def test_rekordbox_config_creation(self):
        """Test RekordboxConfig model creation."""
        config = RekordboxConfig(library_path="/path/to/library.xml")
        assert config.library_path == "/path/to/library.xml"
    
    def test_spotify_config_creation(self):
        """Test SpotifyConfig model creation."""
        config = SpotifyConfig(
            client_id="test_id",
            client_secret="test_secret",
            ignore_playlists=["test"],
            follow_threshold=5
        )
        assert config.client_id == "test_id"
        assert config.client_secret == "test_secret"
        assert config.ignore_playlists == ["test"]
        assert config.follow_threshold == 5
    
    def test_config_defaults(self):
        """Test Config model with defaults."""
        config = Config(
            rekordbox=RekordboxConfig(library_path="/test/path"),
            spotify=SpotifyConfig(client_id="id", client_secret="secret")
        )
        assert config.text_processing.replace_in_title == []
        assert config.playlists.prefix == "rb"
        assert config.matching.similarity_threshold == 0.9


class TestConfigPaths:
    """Test configuration path functions."""
    
    @patch('os.name', 'nt')
    @patch.dict('os.environ', {'APPDATA': r'C:\Users\Test\AppData\Roaming'})
    def test_get_config_path_windows(self):
        """Test config path on Windows."""
        with patch('pathlib.Path.mkdir'):
            path = get_config_path()
            expected = Path(r'C:\Users\Test\AppData\Roaming\fortherekord\config.yaml')
            assert path == expected
    



class TestConfigFileOperations:
    """Test configuration file operations."""
    
    def test_load_config_file_not_found(self):
        """Test loading config when file doesn't exist - should auto-create."""
        config_path = Path("nonexistent.yaml")
        
        # Auto-creation should create a default config instead of raising FileNotFoundError
        config = load_config(config_path)
        assert config is not None
        assert hasattr(config, 'rekordbox')
        assert hasattr(config, 'spotify')
        
        # Clean up the created file
        if config_path.exists():
            config_path.unlink()
    
    def test_load_config_success(self):
        """Test successful config loading."""
        config_data = {
            'rekordbox': {'library_path': '/test/path'},
            'spotify': {'client_id': 'test_id', 'client_secret': 'test_secret'}
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = Path(f.name)
        
        try:
            config = load_config(config_path)
            assert config.rekordbox.library_path == '/test/path'
            assert config.spotify.client_id == 'test_id'
        finally:
            config_path.unlink()
    
    def test_save_config(self):
        """Test saving configuration to file."""
        config = Config(
            rekordbox=RekordboxConfig(library_path="/test/path"),
            spotify=SpotifyConfig(client_id="test_id", client_secret="test_secret")
        )
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            config_path = Path(f.name)
        
        try:
            save_config(config, config_path)
            assert config_path.exists()
            
            # Verify content
            with open(config_path, 'r') as f:
                data = yaml.safe_load(f)
            assert data['rekordbox']['library_path'] == '/test/path'
        finally:
            config_path.unlink()
    
    def test_create_example_config(self):
        """Test creating example configuration."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            config_path = Path(f.name)
        
        try:
            create_example_config(config_path)
            assert config_path.exists()
            
            with open(config_path, 'r') as f:
                data = yaml.safe_load(f)
            assert 'rekordbox' in data
            assert 'spotify' in data
            assert data['spotify']['client_id'] == 'your_spotify_client_id'
        finally:
            config_path.unlink()


class TestConfigValidation:
    """Test configuration validation."""
    
    def test_validate_config_missing_library(self):
        """Test validation with missing library file."""
        config = Config(
            rekordbox=RekordboxConfig(library_path="/nonexistent/path"),
            spotify=SpotifyConfig(client_id="test_id", client_secret="test_secret")
        )
        
        errors = validate_config(config)
        assert any("library file not found" in error.lower() for error in errors)
    
    def test_validate_config_invalid_spotify_credentials(self):
        """Test validation with invalid Spotify credentials."""
        with tempfile.NamedTemporaryFile(suffix='.xml') as f:
            config = Config(
                rekordbox=RekordboxConfig(library_path=f.name),
                spotify=SpotifyConfig(
                    client_id="your_spotify_client_id",
                    client_secret="your_spotify_client_secret"
                )
            )
        
        errors = validate_config(config)
        assert any("client_id not configured" in error for error in errors)
        assert any("client_secret not configured" in error for error in errors)
    
    def test_validate_config_invalid_thresholds(self):
        """Test validation with invalid threshold values."""
        with tempfile.NamedTemporaryFile(suffix='.xml') as f:
            config = Config(
                rekordbox=RekordboxConfig(library_path=f.name),
                spotify=SpotifyConfig(
                    client_id="valid_id",
                    client_secret="valid_secret",
                    follow_threshold=0
                ),
                matching=MatchingConfig(
                    similarity_threshold=1.5,
                    boost_liked_tracks=0.5
                )
            )
        
        errors = validate_config(config)
        assert any("similarity_threshold must be between 0.0 and 1.0" in error for error in errors)
        assert any("boost_liked_tracks must be >= 1.0" in error for error in errors)
        assert any("follow_threshold must be >= 1" in error for error in errors)
    
    def test_validate_config_success(self):
        """Test successful config validation."""
        with tempfile.NamedTemporaryFile(suffix='.xml', delete=False) as f:
            config = Config(
                rekordbox=RekordboxConfig(library_path=f.name),
                spotify=SpotifyConfig(client_id="valid_id", client_secret="valid_secret")
            )
            
            errors = validate_config(config)
            assert errors == []
        
        # Clean up
        import os
        os.unlink(f.name)
