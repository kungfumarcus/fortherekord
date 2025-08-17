# ForTheRekord

A Python application that synchronizes Rekordbox DJ library with Spotify playlists and manages track matching between the two platforms.

## Architecture Overview

The application is built using a modular architecture with clear separation of concerns:

### Core Components

**[Application.md](specs/Application.md)** - Main CLI application with command-line interface and orchestration logic

**[Rekordbox.md](specs/Rekordbox.md)** - Direct database integration using pyrekordbox library for encrypted SQLite access

**[RekordboxMetadata.md](specs/RekordboxMetadata.md)** - Track metadata processing and title enhancement in format "Title - Artist [Key]"

**[Spotify.md](specs/Spotify.md)** - Spotify Web API integration for authentication, search, and playlist management

**[FileMatching.md](specs/FileMatching.md)** - Track matching algorithms with progressive search and interactive mode support

**[Configuration.md](specs/Configuration.md)** - YAML configuration management with secure credential storage

### Cross-cutting Concerns

**[common/Testing.md](specs/common/Testing.md)** - Comprehensive testing strategy with unit, integration, and end-to-end tests

**[common/Logging.md](specs/common/Logging.md)** - Structured logging with configurable levels and output formats

**[common/ErrorHandling.md](specs/common/ErrorHandling.md)** - Centralized error handling and recovery strategies

## Key Features

- **Direct Database Access**: Uses pyrekordbox library to read/write Rekordbox SQLite databases directly
- **Smart Playlist Creation**: Converts Rekordbox folder structure to Spotify playlists
- **Progressive Track Matching**: Raw text first, then cleaned text with liked track prioritization
- **Interactive Mode**: User-guided matching for ambiguous tracks
- **Title Enhancement**: Standardizes track titles to "Title - Artist [Key]" format
- **Mapping Cache**: Persistent storage of track mappings with algorithm versioning

## Specification Guidelines

### Cross-Referencing
When specifications reference functionality handled by other components, always include hyperlinks to the relevant specification files using relative paths:
- `[ComponentName.md](ComponentName.md)` for same-directory references
- `[subdirectory/ComponentName.md](subdirectory/ComponentName.md)` for nested directories

This creates a navigable specification network that helps developers understand component relationships and dependencies.

### Development Approach
- Start with identical functionality to PowerShell version
- Write code as simply as possible initially
- Add logging, exception handling, and bells & whistles later
- Use YAML configuration instead of XML
- **Important**: If unsure about any implementation decision, stop and ask the user for clarification
```yaml
rekordbox:
  library_path: "path/to/library.xml"
  
text_processing:
  replace_in_title:
    - from: " (Original Mix)"
      to: ""
    - from: "(Extended Mix)"
      to: "(ext)"
      
playlists:
  ignore: ["playlist1", "playlist2"]
  prefix: "rb"
  
spotify:
  client_id: "spotify_client_id"
  client_secret: "spotify_client_secret"
  ignore_playlists: ["old school"]
  exclude_from_names: ["mytags"]
  follow_threshold: 3
  
matching:
  similarity_threshold: 0.9
  boost_liked_tracks: 2.0
```

### Core Function Points Identified

**Configuration Management**: load_config, save_config, validate_config, get_config_path

**Rekordbox Data Access**: load_rekordbox_library, get_collection_tracks, get_playlists, get_tracks_from_playlist, parse_track_metadata

**Text Processing**: clean_track_title, clean_artist_name, extract_search_title, normalize_search_string

**Spotify Authentication**: authenticate_spotify, refresh_token, get_user_id

**Spotify API Operations**: search_spotify_tracks, get_user_playlists, create_playlist, delete_playlist, get_playlist_tracks, add_tracks_to_playlist, remove_tracks_from_playlist, get_saved_tracks, follow_artist

**Track Matching Engine**: calculate_similarity, score_track_match, find_best_match, interactive_track_selection

**Data Persistence**: load_track_mappings, save_track_mappings, load_liked_tracks_cache, save_liked_tracks_cache

**Playlist Synchronization**: sync_single_playlist, sync_all_playlists, compare_playlists, build_rekordbox_playlist_tree

**Artist Following**: count_artist_occurrences, follow_popular_artists

**CLI Interface**: main, parse_arguments, interactive_mode

**Utilities**: display_progress, calculate_match_percentage, validate_file_paths

### Rekordbox Database Access Future Enhancement

Python can access Rekordbox's SQLite databases directly (.edb files) for real-time data:
- **Location**: `%APPDATA%\Pioneer\rekordbox\datafiles\` (Windows)
- **Key Files**: `master.db`, `m.edb`, `p.edb`, `s.edb`
- **Libraries**: `sqlite3`, `rekordbox-xml`, `djanalytics`, `sqlalchemy`
- **Advantages**: Real-time data, performance data access, faster than XML parsing

### Original PowerShell Functionality

The application performs these key operations:
1. **Library Processing**: Loads Rekordbox XML, extracts tracks and playlists
2. **Text Cleaning**: Removes/replaces configured text from titles and artists
3. **Spotify Integration**: OAuth authentication, playlist management, track searching
4. **Track Matching**: Multi-stage fuzzy matching with scoring algorithm
5. **Caching**: Saves track mappings and liked tracks to JSON files
6. **Interactive Mode**: Allows manual track selection when automatic matching fails
7. **Artist Following**: Automatically follows artists with multiple liked tracks
8. **Playlist Sync**: Creates/updates/deletes Spotify playlists to match Rekordbox

### Implementation Priority

1. **Phase 1**: Core infrastructure (config, CLI, data models)
2. **Phase 2**: Rekordbox XML parsing and data extraction  
3. **Phase 3**: Spotify authentication and API integration
4. **Phase 4**: Track matching engine with fuzzy logic
5. **Phase 5**: Playlist synchronization and artist following

The user wants to maintain identical functionality first, then enhance with Python's superior libraries and features.
