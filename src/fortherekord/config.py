"""Configuration management for ForTheRekord."""

import os
from pathlib import Path
from typing import Dict, Any
import yaml


class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""


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
                f"rekordbox_library_path must be a string, got "
                f"{type(config['rekordbox_library_path']).__name__}"
            )

    # Validate replace_in_title - must be a list of dictionaries
    if "replace_in_title" in config:
        replace_config = config["replace_in_title"]

        if not isinstance(replace_config, list):
            raise ConfigValidationError(
                f'replace_in_title must be a list of dictionaries with "from"/"to" keys, '
                f"got {type(replace_config).__name__}. "
                f'Example: [{{"from": " (Original Mix)", "to": ""}}, '
                f'{{"from": " (Extended Mix)", "to": " (ext)"}}]'
            )

        # Validate list contents
        for i, replacement in enumerate(replace_config):
            if not isinstance(replacement, dict):
                raise ConfigValidationError(
                    f"replace_in_title[{i}] must be a dictionary with 'from'/'to' keys, "
                    f"got {type(replacement).__name__}"
                )

            if "from" not in replacement:
                raise ConfigValidationError(f"replace_in_title[{i}] missing required 'from' key")

            if "to" not in replacement:
                raise ConfigValidationError(f"replace_in_title[{i}] missing required 'to' key")

            if not isinstance(replacement["from"], str):
                raise ConfigValidationError(
                    f"replace_in_title[{i}]['from'] must be a string, "
                    f"got {type(replacement['from']).__name__}"
                )

            if not isinstance(replacement["to"], str):
                raise ConfigValidationError(
                    f"replace_in_title[{i}]['to'] must be a string, "
                    f"got {type(replacement['to']).__name__}"
                )

    return config


def get_config_path() -> Path:
    """Get the path to the configuration file."""
    # Check for test config path first
    test_config_path = os.environ.get("FORTHEREKORD_CONFIG_PATH")
    if test_config_path:
        return Path(test_config_path)

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
        "rekordbox": {
            "library_path": default_path,
            "ignore_playlists": [],
        },
        "processor": {
            "add_key_to_title": False,
            "add_artist_to_title": False,
            "remove_artists_in_title": False,
            "replace_in_title": [
                {"from": " (Original Mix)", "to": ""},
                {"from": " (Extended Mix)", "to": " (ext)"},
            ],
        },
        "spotify": {
            "client_id": "",
            "client_secret": "",
        },
    }
    save_config(default_config)
