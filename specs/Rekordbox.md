# Rekordbox Component Specification

## Scope

Connects to and processes Rekordbox database files to extract track and playlist information, and performs track property cleanup operations directly on the database.
Implements IMusicLibrary interface defined in [MusicLibraryInterface.md](MusicLibraryInterface.md) for use with [PlaylistSync.md](PlaylistSync.md) component.

## Out of Scope

- **Rekordbox Smart Playlist Creation**: Read-only access to existing playlists
- **Direct playlist synchronization logic**: (handled by PlaylistSync component)

## Technical Requirements

- **Database Access**: pyrekordbox library for encrypted SQLite database access
- **Version Support**: Rekordbox 5, 6, and 7 database formats (pyrekordbox tested: 5.8.6, 6.7.7, 7.0.9)
- **SQLCipher**: Automatic key extraction from local Rekordbox installation
- **Database Modifications**: Direct updates to track metadata in live database
- **Runtime Requirement**: Database access works while Rekordbox is running (shows warning but functions normally)
- **Key Extraction**: Automatic key download via `python -m pyrekordbox download-key` for Rekordbox >6.6.5
- **Database Location**: Windows: `%APPDATA%\Pioneer\rekordbox\master.db` (direct path, no datafiles subdirectory)

## Version Support Strategy

### Rekordbox 5/6/7 Compatibility
- **Current Implementation**: Rekordbox 6/7 support only (SQLite database via `Rekordbox6Database`)
- **pyrekordbox Support**: 
  - Rekordbox 5: XML format via `RekordboxXml` class
  - Rekordbox 6/7: SQLite database via `Rekordbox6Database` class
- **Future Enhancement**: Add Rekordbox 5 XML support with format detection
- **Implementation Strategy**: Detect database format (XML vs SQLite) and use appropriate API

## Function Points

### IMusicLibrary Implementation
- **GetPlaylists**: Extract hierarchical playlist structure from database, applying ignore_playlists filter
- **GetPlaylistTracks**: Load track associations for specified playlist
- **CreatePlaylist**: Not supported (read-only for playlists)
- **DeletePlaylist**: Not supported (read-only for playlists)
- **FollowArtist**: Not supported (source library only)
- **GetFollowedArtists**: Not supported (source library only)

### Database Connection
- Auto-detect Rekordbox installation and database location
  - Windows: `%APPDATA%\Pioneer\rekordbox\master.db`
  - macOS: `~/Library/Pioneer/rekordbox/master.db`
  - If not found, prompt user for database path
  - If found, confirm location with user before proceeding
- Extract encryption key from local Rekordbox files
- Establish secure database connection

### Track Operations
- Retrieve all tracks from collection with metadata
- Update track metadata in database

### Playlist Operations
- Extract hierarchical playlist structure from database
- Apply ignore_playlists configuration filter
- Load track associations for each playlist
