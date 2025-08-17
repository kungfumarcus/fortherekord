# Music Library Interface Specification

## Scope
Defines the generic adapter interface for music platform integration, enabling components to work with any music service through a common contract.

## Out of Scope
- Platform-specific implementation details
- Direct music service integrations

## Function Points

### Library Interface Definition
Provides the contract that all music platform libraries must implement.

```csharp
interface IMusicLibrary 
{
    List<IMusicLibraryPlaylist> GetPlaylists();
    List<IMusicLibraryTrack> GetPlaylistTracks(string playlistId);
    void CreatePlaylist(string name, List<IMusicLibraryTrack> tracks);
    void DeletePlaylist(string playlistId);
    void FollowArtist(string artistId);
    List<IMusicLibraryArtist> GetFollowedArtists();
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
