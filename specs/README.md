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


## Specification Guidelines

**Note**: This README provides only an overview and implementation roadmap. All detailed technical requirements, function points, algorithms, and configuration schemas are contained in the individual specification files linked above. Avoid duplicating specification content in this README to maintain single sources of truth.

### Cross-Referencing
When specifications reference functionality handled by other components, always include hyperlinks to the relevant specification files using relative paths. This creates a navigable specification network that helps developers understand component relationships and dependencies.

### Development Approach
- **Scope Control**: Only build code or add configuration that is needed to implement the current agreed application scope
- **Phase Discipline**: Complete and test each phase fully before moving to the next
- **Scope-Driven Development**: Resist the temptation to add "future-proofing" or "nice-to-have" features
- **Incremental Complexity**: Each dependency, configuration option, and code component should serve the immediate scope
- **Progressive Enhancement**: Add complexity incrementally as scope expands, not speculatively
- **Avoid Temporary Logic**: When increasing scope, avoid/minimise implementing temporary logic that will be replaced soon
- **E2E Testable Scope**: When increasing scope, ensure the new scope is testable in e2e (this might require some temporary logic, minimise this!)
- **Important**: If unsure about any implementation decision, stop and ask the user for clarification

## Current Implementation Scope

**Implemented Components:**
- **Basic CLI Framework**: Click-based command-line interface with help and version support
- **Package Structure**: Standard Python src-layout with `src/fortherekord/` package structure  
- **Entry Points**: Both `python -m fortherekord` and console script support
- **Development Tools**: pytest testing framework with helper functions
- **Git Integration**: Proper `.gitignore` for Python projects
- **Simple YAML Configuration**: Basic config file with `rekordbox_library_path` setting
- **Config Management**: Load/save config in standard location (`~/.config/fortherekord/config.yaml`)
- **Basic Data Models**: Track and Playlist dataclasses with core fields (id, title, artist, key, bpm)
- **Rekordbox Library Access**: Use pyrekordbox to load Rekordbox 6/7 database and extract playlist information
- **Full tests**: unit and e2e tests for all implemented code

**Available Commands:**
```bash
# Display help
python -m fortherekord --help

# Show version
python -m fortherekord --version  

# Run sync command (loads Rekordbox library, displays playlists)
python -m fortherekord sync
```

**Test Coverage:**
- Aim for **100% test coverage** across all implemented components
- Use configuration to disable coverage for code we agree does not need it
- Unit tests for configuration management, Rekordbox integration, and CLI functionality
- pytest fixtures and helper functions to reduce repetition
- End-to-end test covering complete CLI workflow
- Cross-platform testing strategies (Windows development, macOS runtime support)
- Comprehensive error handling and edge case coverage
- Fast execution with proper mocking of external dependencies

**Current Scope Limitations:**
- No Spotify API functionality yet  
- No actual synchronization logic yet
- No logging or CI/CD yet (error handling is included)
- Sync command loads and displays Rekordbox data but doesn't sync to Spotify
- Rekordbox 6/7 database support only (Rekordbox 5 XML format deferred)

**Next Phase Ready:** Foundation established for Spotify API integration and actual playlist synchronization.
