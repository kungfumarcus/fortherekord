# Rekordbox Component Specification

## Scope

Connects to and processes Rekordbox database files to extract track and playlist information, and performs track property cleanup operations directly on the database.

## Out of Scope

- **XML Processing**: Uses direct database access only via pyrekordbox library
- **Rekordbox Smart Playlist Creation**: Read-only access to existing playlists
- **Multiple Database Versions**: Supports Rekordbox v6/v7 databases only

## Technical Requirements

- **Database Access**: pyrekordbox library for encrypted SQLite database access
- **SQLCipher**: Automatic key extraction from local Rekordbox installation
- **Database Modifications**: Direct updates to track metadata in live database

## Function Points

### Database Connection
- Auto-detect Rekordbox installation and database location
- Extract encryption key from local Rekordbox files
- Establish secure database connection

### Track Operations
- Retrieve all tracks from collection with metadata
- Update track metadata in database

### Playlist Operations
- Extract hierarchical playlist structure from database
- Load track associations for each playlist
