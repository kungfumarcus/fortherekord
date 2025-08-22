# Configuration Specification

## Scope
YAML-based configuration management for API credentials, user preferences, and processing settings.

## Out of Scope
- **Cache directory*: Automatically set to same folder as executable
- *OAuth redirect URI*: Handled internally by application

## Technical Requirements
- **YAML Format**: Human-readable configuration files with .yaml or .yml extension

## Function Points

### Configuration Management
- **Load Configuration**: Read and parse YAML file from data/config.yaml (in data subfolder with executable), return Configuration object that supports property access via get/set methods
- **Validate Configuration**: Check all mandatory fields are present and values are in valid format, throw detailed error for missing/invalid entries
- **Save Configuration**: Write current Configuration object state back to data/config.yaml file, preserving formatting and comments where possible

## Configuration Template

```yaml
# Application Settings (MANDATORY)
log_file: "data/fortherekord.log"            # MANDATORY: Log file location, defaults to data/fortherekord.log if not specified

# Rekordbox Configuration (MANDATORY)
rekordbox_library_path: "/path/to/rekordbox/database.edb"  # MANDATORY: Path to Rekordbox database file
rekordbox:
  # Database access configuration
  ignore_playlists: []                        # OPTIONAL: Playlists to skip during processing
  # Enhancement feature flags (current implementation)
  add_key_to_title: true                      # OPTIONAL: Add key (e.g., [Am]) to track title, defaults to false
  add_artist_to_title: true                   # OPTIONAL: Add artist name to track title, defaults to false
  remove_artists_in_title: true               # OPTIONAL: Remove duplicate artists from title, defaults to false
  # Legacy structure (deprecated but supported for backward compatibility)
  enhance_title:
    include_artist: false                     # OPTIONAL: Legacy flag, superseded by add_artist_to_title
    include_tonality: false                   # OPTIONAL: Legacy flag, superseded by add_key_to_title
    replace: []                               # OPTIONAL: Legacy array structure
  enhance_artist:
    replace: []                               # OPTIONAL: Legacy array structure for artist replacements

# Spotify Configuration (OPTIONAL)
spotify:
  client_id: "your_spotify_client_id"         # MANDATORY if spotify section exists: Spotify app client ID
  client_secret: "your_spotify_client_secret" # MANDATORY if spotify section exists: Spotify app client secret
  follow_threshold: 3                         # OPTIONAL: Follow artists if they appear in X or more liked tracks, defaults to 3

# Generic Playlist Sync Configuration (OPTIONAL)  
sync_playlists:
  ignore_playlists: []                        # OPTIONAL: Playlists to exclude from sync
  exclude_from_playlist_names: []             # OPTIONAL: Remove these terms from playlist names
  replace_in_playlist_name: []                # OPTIONAL: Text replacements for playlist names
  replace_in_title: []                        # OPTIONAL: Text replacements for track titles in target platform
```

### Configuration Field Documentation

**MANDATORY Fields:**
- `rekordbox_library_path`: Path to Rekordbox database file (.edb)
- `spotify.client_id`: Spotify application client ID string (if spotify section exists)
- `spotify.client_secret`: Spotify application client secret string (if spotify section exists)
- `log_file`: Log file path string (default: "data/fortherekord.log")

**OPTIONAL Fields with Defaults:**
- `rekordbox.ignore_playlists`: Array of playlist names to skip (default: empty)
- `rekordbox.add_key_to_title`: Boolean flag to add key to title (default: false)
- `rekordbox.add_artist_to_title`: Boolean flag to add artist to title (default: false) 
- `rekordbox.remove_artists_in_title`: Boolean flag to remove duplicate artists (default: false)
- `rekordbox.replace_in_title`: Dictionary of text replacements (default: empty)
- `rekordbox.enhance_title.include_artist`: Boolean flag (default: false) [LEGACY]
- `rekordbox.enhance_title.include_tonality`: Boolean flag (default: false) [LEGACY]
- `spotify.follow_threshold`: Integer 0+ (default: 3)
- `sync_playlists.ignore_playlists`: Array of playlist names to exclude from sync (default: empty)
- `sync_playlists.exclude_from_playlist_names`: Array of terms to remove from playlist names (default: empty)
