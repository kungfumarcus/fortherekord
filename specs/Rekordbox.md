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
- **Database Lock Detection**: Detect if database is locked during save operations and provide clear error message
- **Key Extraction**: Automatic key download via `python -m pyrekordbox download-key` for Rekordbox >6.6.5
- **Database Location**: Windows: `%APPDATA%\Pioneer\rekordbox\master.db` (direct path, no datafiles subdirectory)

## Function Points

### IMusicLibrary Implementation
- **GetPlaylists**: Extract hierarchical playlist structure from database, applying ignore_playlists filter. Returns only top-level playlists (no parent). Each playlist object contains references to parent and children playlists for tree traversal.
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
- **Track Change Detection**: Compare enhanced track title AND artist with original values to determine if modification is needed
- **Conditional Updates**: Only call update_track_metadata() for tracks where enhanced title OR artist differs from original
- **Modified Tracks Only**: Only save tracks that have actually been modified - never save unchanged tracks
- **Accurate Reporting**: Report exact count of tracks that were actually updated and saved to database
- **Save Error Handling**: Detect "Rekordbox is running" errors and provide actionable error messages

### Playlist Operations
- Extract hierarchical playlist structure from database
- Apply ignore_playlists configuration filter
- Load track associations for each playlist
- **Output Filtering**: Only show output for playlists that contain tracks (skip empty playlists)
- **Database Lock Detection**: Capture pyrekordbox warning messages during database initialization to detect if Rekordbox is running

### Playlist Hierarchy Display

#### Requirements
- **Hierarchical Structure**: Display playlists in their natural parent-child tree structure from Rekordbox
- **Visual Indentation**: Show hierarchy depth through consistent indentation (2 spaces per level)
- **Track Count Information**: Display track counts only for playlists that contain tracks
- **Rekordbox Ordering**: Preserve the original playlist order from Rekordbox using the `Seq` property for sorting

#### Output Format
```
- breaks
- bush techno
  - 130+
  - all
  - mytags
    - 128+
    - dark (15 tracks)
    - deep (23 tracks)
```
