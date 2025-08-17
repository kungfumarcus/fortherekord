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
  # Database access configuration
  ignore_playlists:                           # OPTIONAL: Playlists to skip during processing
    - "twiggy"
    - "intensity" 
    - "no rating"
    - "spacer"
  enhance_title:
    include_artist: false                     # OPTIONAL: Add artist name to track title, defaults to false
    include_tonality: false                   # OPTIONAL: Add tonality (1A, 5B, etc.) to track title, defaults to false
    replace:                                  # OPTIONAL: Text cleaning rules for track titles
      - from: " (Original Mix)"
        to: ""
      - from: "(Extended Mix)"
        to: "(ext)"
      - from: "(Ext. Mix)"  
        to: "(ext)"
  enhance_artist:
    replace:                                  # OPTIONAL: Text cleaning rules for artist names
      - from: "feat."
        to: "ft."

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

### Configuration Field Documentation

**MANDATORY Fields:**
- `spotify.client_id`: Spotify application client ID string (if spotify section exists)
- `spotify.client_secret`: Spotify application client secret string (if spotify section exists)
- `log_file`: Log file path string (default: "data/fortherekord.log")
- `replace[].from`: Original text string (if replace sections exist)
- `replace[].to`: Replacement text string (if replace sections exist)

**OPTIONAL Fields with Defaults:**
- `rekordbox.ignore_playlists`: Array of playlist names to skip (default: empty)
- `rekordbox.enhance_title.include_artist`: Boolean flag (default: false)
- `rekordbox.enhance_title.include_tonality`: Boolean flag (default: false)
- `spotify.follow_threshold`: Integer 0+ (default: 3)
- `sync_playlists.ignore_playlists`: Array of playlist names to exclude from sync (default: empty)
- `sync_playlists.exclude_from_playlist_names`: Array of terms to remove from playlist names (default: empty)
