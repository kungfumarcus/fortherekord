"""Configuration management for ForTheRekord."""

import os
from pathlib import Path
from typing import Dict, Any, List, Union
import yaml


class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""
    pass


def validate_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate configuration values.
    
    Args:
        config: Raw configuration dictionary
        
    Returns:
        The same configuration if valid
        
    Raises:
        ConfigValidationError: If configuration is invalid
    """
    # Validate rekordbox_library_path
    if "rekordbox_library_path" in config:
        if not isinstance(config["rekordbox_library_path"], str):
            raise ConfigValidationError(
                f"rekordbox_library_path must be a string, got {type(config['rekordbox_library_path']).__name__}"
            )
    
    # Validate replace_in_title - must be a dictionary
    if "replace_in_title" in config:
        replace_config = config["replace_in_title"]
        
        if not isinstance(replace_config, dict):
            raise ConfigValidationError(
                f"replace_in_title must be a dictionary ({{\"from\": \"to\"}}), got {type(replace_config).__name__}. "
                f"Example: {{\" (Original Mix)\": \"\", \" (Extended Mix)\": \" (ext)\"}}"
            )
        
        # Validate dictionary contents
        for key, value in replace_config.items():
            if not isinstance(key, str):
                raise ConfigValidationError(
                    f"replace_in_title keys must be strings, got {type(key).__name__}"
                )
            if value is not None and not isinstance(value, str):
                raise ConfigValidationError(
                    f"replace_in_title values must be strings or None, got {type(value).__name__}"
                )
    
    # Validate ignore_playlists
    if "ignore_playlists" in config:
        ignore_playlists = config["ignore_playlists"]
        if not isinstance(ignore_playlists, list):
            raise ConfigValidationError(
                f"ignore_playlists must be a list, got {type(ignore_playlists).__name__}"
            )
        for item in ignore_playlists:
            if not isinstance(item, str):
                raise ConfigValidationError(
                    f"ignore_playlists items must be strings, got {type(item).__name__}"
                )
    
    return config


def get_config_path() -> Path:
    """Get the path to the configuration file."""
    if os.name == "nt":  # Windows
        config_dir = Path.home() / "AppData" / "Local" / "fortherekord"
    else:  # Unix-like  # pragma: no cover
        config_dir = Path.home() / ".config" / "fortherekord"  # pragma: no cover

    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / "config.yaml"


def load_config() -> Dict[str, Any]:
    """Load and validate configuration from YAML file."""
    config_path = get_config_path()

    if not config_path.exists():
        return {}

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            raw_config = yaml.safe_load(f) or {}
        
        # Validate the configuration (throws error if invalid)
        validate_config(raw_config)
        return raw_config
        
    except (FileNotFoundError, yaml.YAMLError, OSError):
        return {}
    except ConfigValidationError as e:
        # Re-raise with context about the config file
        raise ConfigValidationError(f"Invalid configuration in {config_path}: {e}") from e


def save_config(config: Dict[str, Any]) -> None:
    """Save configuration to YAML file."""
    config_path = get_config_path()

    with open(config_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(config, f, default_flow_style=False)


def create_default_config() -> None:
    """Create a default configuration file with Windows default path."""
    # Use standard Windows Rekordbox database location
    appdata = os.environ.get("APPDATA", "")
    default_path = str(Path(appdata) / "Pioneer" / "rekordbox" / "master.db") if appdata else ""

    default_config = {
        "rekordbox_library_path": default_path,
        "replace_in_title": {
            " (Original Mix)": "",
            " (Extended Mix)": " (ext)"
        },
        "ignore_playlists": []
    }
    save_config(default_config)
