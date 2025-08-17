# Follow Artists Specification

## Scope
Analyze successfully matched tracks to identify popular artists and automatically follow them using any music platform adapter.

## Out of Scope
- Artist analysis from unmatched tracks
- Manual artist selection or curation
- Artist unfollowing functionality

## Function Points

### Configuration Inputs
- **artist_follow_threshold**: Minimum number of unique tracks required to follow an artist

### Artist Analysis Algorithm
- Load track mapping data from RekordBoxSpotifyMapping.json created by [FileMatching.md](FileMatching.md)
- Extract successfully matched tracks (target_track_id not null)
- Count unique track occurrences per target platform artist
- Identify artists meeting the configured threshold

### Following Operations
- Retrieve currently followed artists using target platform adapter (see [MusicLibraryInterface.md](MusicLibraryInterface.md))
- Filter candidate artists to exclude already followed artists
- Follow qualifying artists using target platform adapter
- Log newly followed artists and skip already followed artists
- Report follow statistics: candidates analyzed, already followed, newly followed
