# ForTheRekord Application Specification

## Scope

A command-line application that provides additional functionality for Rekordbox DJs.
* Update Rekordbox track properties such as title and artist, cleaning up unneeded text and adding extra information in titles (see [RekordboxMetadata.md](RekordboxMetadata.md))
* Create and synchronize Spotify playlists matching your Rekordbox playlists. This requires fuzzy matching logic to match tracks with different text in title and artist (see [filematching.md](filematching.md) and [Spotify.md](Spotify.md))
* Follow artists found in multiple tracks in your Rekordbox playlists
* Rich configuration allowing custom behavior to suit the user's requirements

The application integrates directly with the Rekordbox database for real-time access and updates (see [Rekordbox.md](Rekordbox.md)).

## Out of Scope

The following features are explicitly not included in this initial implementation:

- **Performance Requirements**: No specific performance targets defined (implement efficiently but no quantified metrics)
- **GUI Interface**: Command-line only
- **Smart Playlist Creation**: Create Rekordbox smart playlists based on playlist track MyTag values (future enhancement)

## Technical Requirements

- **Platform**: Python 3.8+ console application
- **Package Management**: pyproject.toml with modern Python packaging
- **CLI Framework**: Click for command-line interface with Rich for styled output
- **Configuration**: PyYAML for YAML configuration files with Pydantic validation
- **Logging**: Python standard logging module with Rich handler for console output
- **Progress UI**: Rich library for progress bars and formatted output
- **String Similarity**: python-Levenshtein for fast text matching
- **Spotify Integration**: spotipy library for OAuth and API operations
- **Database Access**: pyrekordbox library for Rekordbox database integration

## Function Points

### Command Line Interface

**Basic Usage:**
- `fortherekord` - Standard usage, processes Rekordbox database and implements configured behaviors
- `fortherekord --dry-run` - Preview changes without making them to the database
- `fortherekord --remap` - Clear existing track mappings and then run as normal
- `fortherekord --spoify-cache` - Use cached liked tracks instead of fetching from Spotify
- `fortherekord --interactive` - Enable interactive track matching mode

**Options:**
- `--verbose` - Enable Information level logging output
- `--debug` - Enable Debug level logging output (includes Information level)
- `--help` - Display usage information

**Exit Codes:**
- `0` - Success (even if some tracks remain unmapped)
- `1` - Error (authentication failures, file access errors, critical failures only)

### Main Flow
- Load user configuration
- Connect to Rekordbox database
- **Early Validation**: Check if Rekordbox is running and save operations will be needed
  - If Rekordbox is running and metadata changes are planned, exit with error message
  - Provide clear instructions to close Rekordbox before running
- Library Cleanup
  - Load Collection from Rekordbox (contains all playlists and tracks with filtering applied)
  - Display playlist hierarchy with track counts
  - Cleanup and update track name and artist properties directly in database
- Sync Spotify
  - Authenticate with Spotify using OAuth
  - Load Spotify liked tracks
  - Sync Spotify Playlists
    - Use Collection for efficient access to Rekordbox playlists and tracks
    - Load cached track mappings
    - Execute playlist synchronization
    - Save updated mappings
  - Follow popular artists based on threshold

### Output Requirements
- **Playlist Processing**: Only show output for playlists that contain tracks (skip empty playlists)
- **Playlist Names**: Display target/destination playlist names, not source Rekordbox playlist names
- **Progress Reporting**: Clear indication of processing status and track counts
