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
# Rekordbox Configuration (MANDATORY)
rekordbox:
  library_path: "/path/to/rekordbox/master.db"  # MANDATORY: Path to Rekordbox database file
  ignore_playlists:                           # OPTIONAL: Playlists to skip during processing
    - "twiggy"
    - "intensity" 
    - "no rating"
    - "spacer"

# Music Library Processor Configuration (OPTIONAL)
processor:
  add_key_to_title: false                     # OPTIONAL: Add tonality (1A, 5B, etc.) to track title, defaults to false
  add_artist_to_title: false                  # OPTIONAL: Add artist name to track title, defaults to false
  remove_artists_in_title: false             # OPTIONAL: Remove duplicate artists from title, defaults to false
  replace_in_title:                           # OPTIONAL: Text cleaning rules for track titles
    " (Original Mix)": ""
    "(Extended Mix)": "(ext)"
    "(Ext. Mix)": "(ext)"

# Spotify Configuration (OPTIONAL)
spotify:
  client_id: "your_spotify_client_id"         # MANDATORY if spotify section exists: Spotify app client ID
  client_secret: "your_spotify_client_secret" # MANDATORY if spotify section exists: Spotify app client secret
  follow_threshold: 3                         # OPTIONAL: Follow artists if they appear in X or more liked tracks, defaults to 3

# Generic Playlist Sync Configuration (OPTIONAL)  
sync_playlists:
  ignore_playlists:                           # OPTIONAL: Playlists to exclude from sync
    - "old school"
  exclude_from_playlist_names:                # OPTIONAL: Remove these terms from playlist names
    - "mytags"
  replace_in_playlist_name:                   # OPTIONAL: Text replacements for playlist names
    - from: "something"
      to: "replacement"
  replace_in_title:                           # OPTIONAL: Text replacements for track titles in target platform
    - from: "(ext)"
      to: "(Extended Mix)"
    - from: "(Ext. Mix)"
      to: "(Extended Mix)"

# Application Settings (MANDATORY)
log_file: "data/fortherekord.log"            # MANDATORY: Log file location, defaults to data/fortherekord.log if not specified
```
