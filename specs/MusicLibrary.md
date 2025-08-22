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

```csharp
interface IMusicLibrary 
{
    IMusicLibraryCollection GetCollection();
    void CreatePlaylist(string name, List<IMusicLibraryTrack> tracks);
    void DeletePlaylist(string playlistId);
    void FollowArtist(string artistId);
    List<IMusicLibraryArtist> GetFollowedArtists();
}

interface IMusicLibraryCollection
{
    List<IMusicLibraryPlaylist> Playlists { get; }
    List<IMusicLibraryTrack> GetAllTracks();
}

interface IMusicLibraryTrack 
{
    string Id { get; }
    string Title { get; }
    string Artist { get; }
    string ArtistId { get; }
}

interface IMusicLibraryPlaylist 
{
    string Id { get; }
    string Name { get; }
    List<IMusicLibraryTrack> Tracks { get; }
}

interface IMusicLibraryArtist 
{
    string Id { get; }
    string Name { get; }
}
```
