# Music Library Interface Specification

## Scope
Defines the generic adapter interface for music platform integration, enabling components to work with any music service through a common contract.

## Out of Scope
- Platform-specific implementation details
- Direct music service integrations

## Function Points

### Library Interface Definition
Provides the contract that all music platform libraries must implement.

### Collection Concept
A Collection represents a complete snapshot of a music library's playlists and tracks at a point in time. Collections provide efficient access to all tracks across multiple playlists while avoiding duplicate database queries. The Collection automatically handles track deduplication when tracks appear in multiple playlists.

Collections are returned by source music libraries (like Rekordbox) to enable efficient processing of large music libraries without repeated database access.

**Music Library Interface:**
- `get_collection()` - Returns a Collection containing all playlists and tracks
- `save_changes(tracks, dry_run=False)` - Saves track modifications, returns count of changed tracks
- `get_playlists()` - Returns list of all playlists
- `get_playlist_tracks(playlist_id)` - Returns tracks for a specific playlist
- `create_playlist(name, tracks)` - Creates new playlist with given tracks
- `delete_playlist(playlist_id)` - Removes a playlist
- `follow_artist(artist_name)` - Follows an artist, returns success status
- `get_followed_artists()` - Returns list of currently followed artists

**Collection Interface:**
- `playlists` - Property containing list of all playlists
- `get_all_tracks()` - Returns deduplicated list of all tracks across playlists

**Track Interface:**
- `id` - Unique track identifier
- `title` - Track title (may be enhanced with metadata)
- `artist` - Primary artist name
- `duration_ms` - Track duration in milliseconds (optional)
- `key` - Musical key notation like "Am", "5B" (optional)
- `original_title` - Original title before enhancement (optional)
- `original_artist` - Original artist before enhancement (optional)

**Playlist Interface:**
- `id` - Unique playlist identifier  
- `name` - Display name of the playlist
- `tracks` - List of Track objects in this playlist
- `parent_id` - Parent playlist ID for hierarchical organization (optional)
- `children` - List of child playlists (optional)

**Artist Interface:**
- `id` - Unique artist identifier
- `name` - Artist display name
