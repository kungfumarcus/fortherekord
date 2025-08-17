"""Configuration management for ForTheRekord."""

import os
from pathlib import Path
from typing import Dict, Any
import yaml


def get_config_path() -> Path:
    """Get the path to the configuration file."""
    if os.name == "nt":  # Windows
        config_dir = Path.home() / "AppData" / "Local" / "fortherekord"
    else:  # Unix-like  # pragma: no cover
        config_dir = Path.home() / ".config" / "fortherekord"  # pragma: no cover

    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / "config.yaml"


def load_config() -> Dict[str, Any]:
    """Load configuration from YAML file."""
    config_path = get_config_path()

    if not config_path.exists():
        return {}

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except (FileNotFoundError, yaml.YAMLError, OSError):
        return {}


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
        "replace_in_title": [
            " (Original Mix)",
            " (Extended Mix): (ext)"
        ],
        "ignore_playlists": []
    }
    save_config(default_config)
