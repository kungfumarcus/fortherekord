"""
Configuration models and management for ForTheRekord.

Uses Pydantic for validation and YAML for configuration storage.
Environment variables can be loaded from .env.local for secrets.
"""

from typing import List, Dict, Optional
from pathlib import Path
import yaml
from pydantic import BaseModel, Field
import os

# Load environment variables from .env.local if it exists
try:
    from dotenv import load_dotenv
    load_dotenv('.env.local')  # Load secrets from .env.local
except ImportError:
    pass  # python-dotenv not installed, skip


class TextReplacement(BaseModel):
    """Configuration for text replacement rules."""
    from_text: str = Field(alias="from")
    to: str
    
    model_config = {"populate_by_name": True}


class RekordboxConfig(BaseModel):
    """Rekordbox-specific configuration."""
    library_path: str


class TextProcessingConfig(BaseModel):
    """Text processing configuration."""
    replace_in_title: List[TextReplacement] = Field(default_factory=list)


class PlaylistsConfig(BaseModel):
    """Playlist management configuration."""
    ignore: List[str] = Field(default_factory=list)
    prefix: str = "rb"


class SpotifyConfig(BaseModel):
    """Spotify API configuration."""
    client_id: str
    client_secret: str
    ignore_playlists: List[str] = Field(default_factory=list)
    exclude_from_names: List[str] = Field(default_factory=list)
    follow_threshold: int = 3
    replace_in_playlist_name: List[TextReplacement] = Field(default_factory=list)
    replace_in_title: List[TextReplacement] = Field(default_factory=list)


class MatchingConfig(BaseModel):
    """Track matching algorithm configuration."""
    similarity_threshold: float = 0.9
    boost_liked_tracks: float = 2.0


class Config(BaseModel):
    """Main configuration model."""
    rekordbox: RekordboxConfig
    text_processing: TextProcessingConfig = Field(default_factory=TextProcessingConfig)
    playlists: PlaylistsConfig = Field(default_factory=PlaylistsConfig)
    spotify: SpotifyConfig
    matching: MatchingConfig = Field(default_factory=MatchingConfig)


def get_config_path() -> Path:
    """Get the standard configuration file path."""
    if os.name == 'nt':  # Windows
        config_dir = Path(os.environ.get('APPDATA', '')) / 'fortherekord'
    else:  # macOS/Linux
        config_dir = Path.home() / '.config' / 'fortherekord'
    
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / 'config.yaml'


def load_config(config_path: Optional[Path] = None) -> Config:
    """Load configuration from YAML file, creating default if it doesn't exist."""
    if config_path is None:
        config_path = get_config_path()
    
    if not config_path.exists():
        # Auto-create default config using environment variables
        create_default_config(config_path)
        print(f"Created default configuration at: {config_path}")
        
        # If we have environment variables, the config might be ready to use
        if os.environ.get('SPOTIFY_CLIENT_ID') and os.environ.get('SPOTIFY_CLIENT_SECRET'):
            print("Using Spotify credentials from environment variables.")
        else:
            print("Please edit the configuration file with your settings before running again.")
        
        # Return a basic config with environment variables if available
        return Config(
            rekordbox=RekordboxConfig(
                library_path=os.environ.get('REKORDBOX_LIBRARY_PATH', "")
            ),
            spotify=SpotifyConfig(
                client_id=os.environ.get('SPOTIFY_CLIENT_ID', ""),
                client_secret=os.environ.get('SPOTIFY_CLIENT_SECRET', "")
            )
        )
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config_data = yaml.safe_load(f)
    
    return Config(**config_data)


def save_config(config: Config, config_path: Optional[Path] = None) -> None:
    """Save configuration to YAML file."""
    if config_path is None:
        config_path = get_config_path()
    
    # Ensure directory exists
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Convert to dict and handle aliases
    config_dict = config.model_dump(by_alias=True)
    
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)


def create_default_config(config_path: Optional[Path] = None) -> None:
    """Create a default configuration file using environment variables when available."""
    if config_path is None:
        config_path = get_config_path()
    else:
        config_path = Path(config_path)  # Ensure it's a Path object
    
    # Use environment variables from .env.local if available, otherwise use placeholders
    default_config = {
        'rekordbox': {
            'library_path': os.environ.get('REKORDBOX_LIBRARY_PATH', 'path/to/rekordbox/library.xml')
        },
        'text_processing': {
            'replace_in_title': [
                {'from': ' (Original Mix)', 'to': ''}
            ]
        },
        'playlists': {
            'ignore': ['playlist1', 'playlist2'],
            'prefix': 'rb'
        },
        'spotify': {
            'client_id': os.environ.get('SPOTIFY_CLIENT_ID', 'your_spotify_client_id'),
            'client_secret': os.environ.get('SPOTIFY_CLIENT_SECRET', 'your_spotify_client_secret'),
            'ignore_playlists': ['playlist1'],
            'exclude_from_names': ['mytags'],
            'follow_threshold': 3,
            'replace_in_playlist_name': [],
            'replace_in_title': [
                {'from': '(ext)', 'to': '(Extended Mix)'},
                {'from': '(Ext. Mix)', 'to': '(Extended Mix)'}
            ]
        },
        'matching': {
            'similarity_threshold': 0.9,
            'boost_liked_tracks': 2.0
        }
    }
    
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(default_config, f, default_flow_style=False, sort_keys=False)


def validate_config(config: Config) -> List[str]:
    """Validate configuration and return list of errors."""
    errors = []
    
    # Check if Rekordbox library path exists
    library_path = Path(config.rekordbox.library_path)
    if not library_path.exists():
        errors.append(f"Rekordbox library file not found: {library_path}")
    
    # Check Spotify credentials
    if not config.spotify.client_id or config.spotify.client_id == 'your_spotify_client_id':
        errors.append("Spotify client_id not configured")
    
    if not config.spotify.client_secret or config.spotify.client_secret == 'your_spotify_client_secret':
        errors.append("Spotify client_secret not configured")
    
    # Validate thresholds
    if not (0.0 <= config.matching.similarity_threshold <= 1.0):
        errors.append("similarity_threshold must be between 0.0 and 1.0")
    
    if config.matching.boost_liked_tracks < 1.0:
        errors.append("boost_liked_tracks must be >= 1.0")
    
    if config.spotify.follow_threshold < 1:
        errors.append("follow_threshold must be >= 1")
    
    return errors
