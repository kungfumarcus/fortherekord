# Playlist Synchronization Specification

## Scope
Generic playlist synchronization between different music platforms using adapter interfaces.
Creates and manages playlists with configurable prefix, deleting only prefixed playlists for safety.
Reads sync_playlist configuration section for platform-agnostic settings.

## Out of Scope
NOTE: remove this section once the corresponding specs are created for these two items
- Smart playlist creation based on MyTag values (separate component)
- Artist following functionality (separate component) 

## Function Points

### Configuration Inputs
- **sync_playlist.playlist_prefix**: Prefix for created playlists (minimum 2 characters, must contain space/hyphen/underscore)
- **sync_playlist.playlist_separator**: Character between prefix and playlist name (default: space)
- **ignore_playlists**: List of playlist names to exclude from synchronization
- **exclude_playlist_names**: Source playlist names to exclude when generating target playlist names

### Adapter Interface
Uses the generic music platform interface defined in [MusicLibraryInterface.md](MusicLibraryInterface.md) to work with any music service.

### Playlist Synchronization Algorithm

#### Source Playlist Processing
- Load all playlists from source library adapter (filtering handled by source adapter)
- For each source playlist:
  - Generate target playlist name: prefix + separator + source_name
  - Clean target playlist name by removing patterns from exclude_playlist_names
  - Load all tracks from source playlist

#### Target Platform Analysis
- Load existing playlists from target library adapter that match the configured prefix
- Build mapping from generated target playlist names to existing target playlist IDs

#### Track Matching Phase
- For each track in source playlists:
  - Use FileMatching component to find corresponding target platform track
  - Build list of matched tracks for each playlist
  - Track unmapped tracks for reporting

#### Playlist Creation/Update
- For each source playlist:
  - Check if target playlist exists (by name)
  - If not exists: create new playlist with prefix + separator + name
  - If exists: replace all tracks in existing playlist with new track list (this is faster than updating tracks individually)
  - Only operate on target playlists matching the configured prefix

#### Cleanup Phase
- Identify target playlists with prefix that no longer exist in source
- Delete these target playlists (safety: only those with matching prefix)
- Generate sync statistics: playlists created, updated, deleted, tracks matched/unmatched, total processing time
- Report results to user with summary of changes made
