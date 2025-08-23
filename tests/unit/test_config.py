"""
Tests for configuration management functionality.

Tests the config module's ability to load, save, and create default configurations.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open
import pytest
import yaml

from fortherekord.config import (
    get_config_path,
    load_config,
    save_config,
    create_default_config,
    validate_config,
    ConfigValidationError,
)


# Helper functions to reduce repetition
def create_temp_config_file(content: dict) -> Path:
    """Helper function to create a temporary config file with given content."""
    temp_file = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
    yaml.safe_dump(content, temp_file)
    temp_file.close()
    return Path(temp_file.name)


def cleanup_temp_file(file_path: Path) -> None:
    """Helper function to clean up temporary files."""
    if file_path.exists():
        file_path.unlink()


class TestConfigPaths:
    """Test configuration path determination."""

    @patch("os.name", "nt")  # Windows
    @patch("fortherekord.config.Path.mkdir")
    def test_get_config_path_windows(self, mock_mkdir):
        """Test config path on Windows."""
        with patch("pathlib.Path.home") as mock_home:
            mock_home.return_value = Path("C:/Users/TestUser")
            config_path = get_config_path()
            expected = Path("C:/Users/TestUser/AppData/Local/fortherekord/config.yaml")
            assert config_path == expected
            mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

    @patch("os.environ.get")
    def test_get_config_path_env_override(self, mock_env_get):
        """Test config path with environment variable override."""
        mock_env_get.return_value = "/custom/test/config.yaml"
        config_path = get_config_path()
        assert config_path == Path("/custom/test/config.yaml")


class TestConfigLoading:
    """Test configuration loading functionality."""

    def test_load_config_file_exists(self):
        """Test loading config when file exists."""
        test_config = {"rekordbox_library_path": "/test/path"}
        temp_file = create_temp_config_file(test_config)

        try:
            with patch("fortherekord.config.get_config_path", return_value=temp_file):
                config = load_config()
                assert config == test_config
        finally:
            cleanup_temp_file(temp_file)

    def test_load_config_file_not_exists(self):
        """Test loading config when file doesn't exist."""
        non_existent_path = Path("/this/path/does/not/exist.yaml")
        with patch("fortherekord.config.get_config_path", return_value=non_existent_path):
            config = load_config()
            assert config == {}

    def test_load_config_invalid_yaml(self):
        """Test loading config with invalid YAML."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as temp_file:
            temp_file.write("invalid: yaml: content: [unclosed")
            temp_file_path = Path(temp_file.name)

        try:
            with patch("fortherekord.config.get_config_path", return_value=temp_file_path):
                config = load_config()
                assert config == {}
        finally:
            cleanup_temp_file(temp_file_path)

    def test_load_config_empty_file(self):
        """Test loading config from empty file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as temp_file:
            temp_file.write("")
            temp_file_path = Path(temp_file.name)

        try:
            with patch("fortherekord.config.get_config_path", return_value=temp_file_path):
                config = load_config()
                assert config == {}
        finally:
            cleanup_temp_file(temp_file_path)


class TestConfigSaving:
    """Test configuration saving functionality."""

    def test_save_config_success(self):
        """Test saving config successfully."""
        test_config = {"rekordbox_library_path": "/test/path"}

        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.yaml"
            with patch("fortherekord.config.get_config_path", return_value=config_path):
                save_config(test_config)

                # Verify file was created and content is correct
                assert config_path.exists()
                with open(config_path, "r", encoding="utf-8") as f:
                    saved_config = yaml.safe_load(f)
                assert saved_config == test_config

    def test_save_config_creates_directory(self):
        """Test that save_config creates parent directories."""
        test_config = {"test": "value"}

        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "subdir" / "config.yaml"
            with patch("fortherekord.config.get_config_path", return_value=config_path):
                # Mock the parent directory creation
                with patch("builtins.open", mock_open()) as mock_file:
                    save_config(test_config)

                    # Verify file was opened for writing
                    mock_file.assert_called_once_with(config_path, "w", encoding="utf-8")


class TestDefaultConfig:
    """Test default configuration creation."""

    @patch.dict(os.environ, {"APPDATA": "C:\\Users\\TestUser\\AppData\\Roaming"})
    def test_create_default_config_windows(self):
        """Test creating default config on Windows."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.yaml"
            with patch("fortherekord.config.get_config_path", return_value=config_path):
                create_default_config()

                # Verify config was created with correct default path
                assert config_path.exists()
                config = load_config()
                expected_path = (
                    "C:\\Users\\TestUser\\AppData\\Roaming\\Pioneer\\rekordbox\\master.db"
                )
                assert config["rekordbox"]["library_path"] == expected_path

    def test_create_default_config_no_appdata(self):
        """Test creating default config when APPDATA is not set."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.yaml"
            with patch("fortherekord.config.get_config_path", return_value=config_path):
                with patch.dict(os.environ, {}, clear=True):  # Clear APPDATA
                    create_default_config()

                    # Verify config was created with empty path
                    assert config_path.exists()
                    config = load_config()
                    assert config["rekordbox"]["library_path"] == ""


# Test fixtures for common setup
@pytest.fixture
def temp_config_dir():
    """Provide a temporary directory for config tests."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def sample_config():
    """Provide sample config data for tests."""
    return {
        "rekordbox_library_path": "/path/to/rekordbox/master.db",
        "spotify_client_id": "test_client_id",
        "ignore_playlists": ["test", "ignore"],
    }


# Example of using fixtures to reduce repetition
class TestConfigWithFixtures:
    """Example of using fixtures for config tests."""

    def test_save_and_load_config_roundtrip(self, temp_config_dir, sample_config):
        """Test that saving and loading config preserves data."""
        config_path = temp_config_dir / "config.yaml"
        with patch("fortherekord.config.get_config_path", return_value=config_path):
            save_config(sample_config)
            loaded_config = load_config()
            assert loaded_config == sample_config


class TestConfigValidation:
    """Test configuration validation functionality."""

    def test_validate_empty_config(self):
        """Test validation of empty config."""
        config = {}
        result = validate_config(config)
        assert result == {}

    def test_validate_valid_config(self):
        """Test validation of valid config."""
        config = {
            "rekordbox_library_path": "/path/to/library.db",
            "replace_in_title": [
                {"from": " (Original Mix)", "to": ""},
                {"from": " (Extended Mix)", "to": " (ext)"},
            ],
            "ignore_playlists": ["playlist1", "playlist2"],
        }
        result = validate_config(config)
        assert result == config

    def test_validate_invalid_library_path_type(self):
        """Test validation fails for non-string library path."""
        config = {"rekordbox_library_path": 123}

        with pytest.raises(
            ConfigValidationError, match="rekordbox_library_path must be a string, got int"
        ):
            validate_config(config)

    def test_validate_replace_in_title_invalid_list_items(self):
        """Test validation fails for invalid list items in replace_in_title."""
        config = {"replace_in_title": [" (Original Mix)", " (Extended Mix): (ext)"]}

        with pytest.raises(
            ConfigValidationError, match="replace_in_title\\[0\\] must be a dictionary"
        ):
            validate_config(config)

    def test_validate_replace_in_title_invalid_type(self):
        """Test validation fails for invalid replace_in_title type."""
        config = {"replace_in_title": "not a dict or list"}

        with pytest.raises(ConfigValidationError, match="replace_in_title must be a list"):
            validate_config(config)

    def test_validate_replace_in_title_missing_from_key(self):
        """Test validation fails for missing 'from' key in replace_in_title."""
        config = {"replace_in_title": [{"to": "value"}]}

        with pytest.raises(
            ConfigValidationError, match="replace_in_title\\[0\\] missing required 'from' key"
        ):
            validate_config(config)

    def test_validate_replace_in_title_missing_to_key(self):
        """Test validation fails for missing 'to' key in replace_in_title."""
        config = {"replace_in_title": [{"from": "key"}]}

        with pytest.raises(
            ConfigValidationError, match="replace_in_title\\[0\\] missing required 'to' key"
        ):
            validate_config(config)

    def test_validate_replace_in_title_invalid_from_type(self):
        """Test validation fails for non-string 'from' value in replace_in_title."""
        config = {"replace_in_title": [{"from": 123, "to": "value"}]}

        with pytest.raises(
            ConfigValidationError,
            match="replace_in_title\\[0\\]\\['from'\\] must be a string, got int",
        ):
            validate_config(config)

    def test_validate_replace_in_title_invalid_to_type(self):
        """Test validation fails for non-string 'to' value in replace_in_title."""
        config = {"replace_in_title": [{"from": "key", "to": 123}]}

        with pytest.raises(
            ConfigValidationError,
            match="replace_in_title\\[0\\]\\['to'\\] must be a string, got int",
        ):
            validate_config(config)

    def test_validate_replace_in_title_valid_list_format(self):
        """Test validation passes for valid list format replace_in_title."""
        config = {"replace_in_title": [{"from": "key", "to": ""}]}
        result = validate_config(config)
        assert result == config

    def test_validate_rekordbox_ignore_playlists_invalid_type(self):
        """Test validation fails for non-list ignore_playlists under rekordbox."""
        config = {"rekordbox": {"ignore_playlists": "not a list"}}

        # Since we don't validate hierarchical config yet, this should pass for now
        # This test documents the expected behavior when we add hierarchical validation
        result = validate_config(config)
        assert result == config

    def test_validate_rekordbox_ignore_playlists_invalid_item_type(self):
        """Test validation for non-string items in rekordbox ignore_playlists."""
        config = {"rekordbox": {"ignore_playlists": ["valid", 123, "also valid"]}}

        # Since we don't validate hierarchical config yet, this should pass for now
        # This test documents the expected behavior when we add hierarchical validation
        result = validate_config(config)
        assert result == config

    def test_validate_config_with_extra_fields(self):
        """Test validation passes through extra fields unchanged."""
        config = {
            "rekordbox_library_path": "/path/to/library.db",
            "extra_field": "extra_value",
            "nested": {"field": "value"},
        }
        result = validate_config(config)
        assert result == config

    def test_load_config_with_validation_error(self):
        """Test load_config when validation fails."""
        invalid_config = {"replace_in_title": ["invalid", "list", "format"]}

        with patch("fortherekord.config.get_config_path") as mock_path:
            mock_config_path = Path("test_config.yaml")
            mock_path.return_value = mock_config_path

            # Mock file exists and reading
            with patch("pathlib.Path.exists", return_value=True):
                with patch("builtins.open", mock_open()):
                    with patch("yaml.safe_load", return_value=invalid_config):
                        with pytest.raises(
                            ConfigValidationError,
                            match="Invalid configuration in.*replace_in_title\\[0\\] "
                            "must be a dictionary",
                        ):
                            load_config()
