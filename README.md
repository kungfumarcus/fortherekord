# ForTheRekord

A Python application that synchronizes Rekordbox DJ library with Spotify playlists and manages track matching between the two platforms.

## Architecture Overview

The application is built using a modular architecture with clear separation of concerns:

### Core Components

**[Application.md](specs/Application.md)** - Main CLI application with command-line interface and orchestration logic

**[Rekordbox.md](specs/Rekordbox.md)** - Direct database integration using pyrekordbox library for encrypted SQLite access

**[RekordboxMetadata.md](specs/RekordboxMetadata.md)** - Track metadata processing and title enhancement in format "Title - Artist [Key]"

**[Spotify.md](specs/Spotify.md)** - Spotify integration via spotipy library with console-based OAuth authentication

**[FileMatching.md](specs/FileMatching.md)** - Track matching algorithms using Levenshtein distance with interactive mode support

**[Configuration.md](specs/Configuration.md)** - YAML configuration management with flattened structure for simplicity

**[PlaylistSync.md](specs/PlaylistSync.md)** - Generic playlist synchronization using adapter pattern for any music platform

**[FollowArtists.md](specs/FollowArtists.md)** - Artist following based on track frequency analysis

**[MusicLibraryInterface.md](specs/MusicLibraryInterface.md)** - Generic adapter interface for music platform abstraction

### Cross-cutting Concerns

**[common/Testing.md](specs/common/Testing.md)** - Comprehensive testing strategy with unit, integration, and end-to-end tests

**[common/Logging.md](specs/common/Logging.md)** - Structured logging with configurable levels and output formats

**[common/ErrorHandling.md](specs/common/ErrorHandling.md)** - Centralized error handling and recovery strategies

**[common/CICD.md](specs/common/CICD.md)** - GitHub Actions pipeline with code quality checks and multi-platform builds

**[common/Python.md](specs/common/Python.md)** - Python development standards and AI-friendly coding practices

## Key Features

- **Direct Database Access**: Uses pyrekordbox library to read/write Rekordbox SQLite databases directly
- **Simple Track Matching**: Levenshtein distance-based matching with liked track prioritization
- **Interactive Mode**: User-guided matching for ambiguous tracks
- **Title Enhancement**: Standardizes track titles to "Title - Artist [Key]" format
- **Mapping Cache**: Persistent storage of track mappings with algorithm versioning
- **Console-based OAuth**: No browser required for Spotify authentication
- **Progress Reporting**: Rich CLI progress bars with per-playlist updates
- **Generic Sync Architecture**: Adapter pattern supports future music platforms

## Technical Stack

- **CLI Framework**: Click for command-line interface
- **Configuration**: PyYAML for YAML configuration files  
- **Database Access**: pyrekordbox library for Rekordbox database integration
- **Spotify Integration**: spotipy library for OAuth and API operations
- **String Matching**: python-Levenshtein for fast text similarity
- **Progress UI**: Rich library for progress bars and formatted output
- **Testing**: pytest with comprehensive mocking
- **CI/CD**: GitHub Actions with code quality checks (flake8, pylint, mypy)

## File Organization

All application data is stored in a `data/` subfolder with the executable:
- **Configuration**: `data/config.yaml`
- **Mapping Cache**: `data/RekordBoxSpotifyMapping.json`
- **Log File**: `data/fortherekord.log`

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
- Use YAML configuration with flattened structure
- **Important**: If unsure about any implementation decision, stop and ask the user for clarification

```yaml
rekordbox:
  ignore_playlists: ["playlist1", "playlist2"]
  enhance_title:
    include_artist: false
    include_tonality: false
    replace:
      - from: " (Original Mix)"
        to: ""
      - from: "(Extended Mix)"
        to: "(ext)"
  
spotify:
  client_id: "spotify_client_id"
  client_secret: "spotify_client_secret"
  follow_threshold: 3
  
sync_playlists:
  ignore_playlists: ["old school"]
  exclude_from_playlist_names: ["mytags"]
  replace_in_title:
    - from: "(ext)"
      to: "(Extended Mix)"

log_file: "data/fortherekord.log"
```

### Core Function Points Identified

**Configuration Management**: load_config, save_config, validate_config, get_config_path

**Rekordbox Data Access**: connect_database, get_collection_tracks, get_playlists, get_tracks_from_playlist, parse_track_metadata

**Metadata Processing**: rekordbox_metadata_processor module handles title enhancement, artist processing, and text replacements

**Text Processing**: clean_track_title, clean_artist_name, extract_search_title, normalize_search_string

**Spotify Authentication**: authenticate_spotify, refresh_token, get_user_id

**Spotify API Operations**: search_spotify_tracks, get_user_playlists, create_playlist, delete_playlist, get_playlist_tracks, add_tracks_to_playlist, remove_tracks_from_playlist, get_saved_tracks, follow_artist

**Track Matching Engine**: calculate_similarity, score_track_match, find_best_match, interactive_track_selection

**Data Persistence**: load_track_mappings, save_track_mappings, load_liked_tracks_cache, save_liked_tracks_cache

**Playlist Synchronization**: sync_single_playlist, sync_all_playlists, compare_playlists, build_rekordbox_playlist_tree

**Artist Following**: count_artist_occurrences, follow_popular_artists

**CLI Interface**: main, parse_arguments, interactive_mode

**Utilities**: display_progress, calculate_match_percentage, validate_file_paths

### Rekordbox Database Access

Python accesses Rekordbox's SQLite databases directly (.edb files) for real-time data:
- **Location**: `%APPDATA%\Pioneer\rekordbox\datafiles\` (Windows), `~/Library/Pioneer/rekordbox/datafiles/` (macOS)
- **Auto-detection**: Confirms location with user, prompts if not found
- **Library**: pyrekordbox for encrypted database access
- **Advantages**: Real-time data, performance data access, faster than XML parsing

### Original PowerShell Functionality

The application performs these key operations:
1. **Library Processing**: Loads Rekordbox database, extracts tracks and playlists
2. **Text Cleaning**: Removes/replaces configured text from titles and artists
3. **Spotify Integration**: Console-based OAuth authentication, playlist management, track searching
4. **Track Matching**: Simple Levenshtein distance with liked track prioritization
5. **Caching**: Saves track mappings and liked tracks to JSON files
6. **Interactive Mode**: Allows manual track selection when automatic matching fails
7. **Artist Following**: Automatically follows artists with multiple liked tracks
8. **Playlist Sync**: Creates/updates/deletes Spotify playlists to match Rekordbox

### Implementation Priority

1. **Phase 1**: ✅ **COMPLETED** - Core infrastructure (config, CLI, data models, comprehensive testing with 100% coverage)
2. **Phase 2**: 🚧 **CURRENT** - Rekordbox database integration and data extraction  
3. **Phase 3**: Spotify authentication and API integration
4. **Phase 4**: Track matching engine with basic Levenshtein distance
5. **Phase 5**: Playlist synchronization and artist following

**Current Focus**: Building Rekordbox database connectivity using pyrekordbox library to read encrypted SQLite databases, extract track metadata, and retrieve playlist structures. This phase will establish the foundation for all music library operations.

The approach emphasizes simplicity initially, with algorithm refinement based on real data analysis during development.
