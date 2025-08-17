# ForTheRekord

A Python application that synchronizes Rekordbox DJ library with Spotify playlists and manages track matching between the two platforms.

## Architecture Overview

The application is built using a modular architecture with clear separation of concerns:

### Core Components

**[Application.md](Application.md)** - Main CLI application with command-line interface and orchestration logic

**[Rekordbox.md](Rekordbox.md)** - Direct database integration using pyrekordbox library for encrypted SQLite access

**[RekordboxMetadata.md](RekordboxMetadata.md)** - Track metadata processing and title enhancement in format "Title - Artist [Key]"

**[Spotify.md](Spotify.md)** - Spotify integration via spotipy library with console-based OAuth authentication

**[FileMatching.md](FileMatching.md)** - Track matching algorithms using Levenshtein distance with interactive mode support

**[Configuration.md](Configuration.md)** - YAML configuration management with flattened structure for simplicity

**[PlaylistSync.md](PlaylistSync.md)** - Generic playlist synchronization using adapter pattern for any music platform

**[FollowArtists.md](FollowArtists.md)** - Artist following based on track frequency analysis

**[MusicLibraryInterface.md](MusicLibraryInterface.md)** - Generic adapter interface for music platform abstraction

### Cross-cutting Concerns

**[common/Testing.md](common/Testing.md)** - Comprehensive testing strategy with unit, integration, and end-to-end tests

**[common/Logging.md](common/Logging.md)** - Structured logging with configurable levels and output formats

**[common/ErrorHandling.md](common/ErrorHandling.md)** - Centralized error handling and recovery strategies

**[common/CICD.md](common/CICD.md)** - GitHub Actions pipeline with code quality checks and multi-platform builds

**[common/Python.md](common/Python.md)** - Python development standards and AI-friendly coding practices

## Implementation Priority

1. **Phase 1**: Core infrastructure (config, CLI, data models)
2. **Phase 2**: Rekordbox database integration and data extraction  
3. **Phase 3**: Spotify authentication and API integration
4. **Phase 4**: Track matching engine with basic Levenshtein distance
5. **Phase 5**: Playlist synchronization and artist following

## Specification Guidelines

**Note**: This README provides only an overview and implementation roadmap. All detailed technical requirements, function points, algorithms, and configuration schemas are contained in the individual specification files linked above. Avoid duplicating specification content in this README to maintain single sources of truth.

### Cross-Referencing
When specifications reference functionality handled by other components, always include hyperlinks to the relevant specification files using relative paths. This creates a navigable specification network that helps developers understand component relationships and dependencies.

### Development Approach
- Start with identical functionality to PowerShell version
- Write code as simply as possible initially  
- Add logging, exception handling, and bells & whistles later
- Use YAML configuration with flattened structure
- **Important**: If unsure about any implementation decision, stop and ask the user for clarification
