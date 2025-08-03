# fortherekord/

Main Python package for the ForTheRekord application.

## Modules

- `__init__.py` - Package initialization and metadata
- `__main__.py` - CLI entry point for python -m execution
- `main.py` - CLI interface using Click framework
- `config.py` - Configuration management with Pydantic and YAML
- `models.py` - Data model classes (RekordboxTrack, RekordboxPlaylist) with dot notation access
- `rekordbox.py` - Rekordbox XML parsing and data extraction
- `spotify.py` - Spotify Web API integration using spotipy
- `matching.py` - Track matching algorithms with fuzzy string matching
- `search_utils.py` - Text processing and search utilities
- `file_utils.py` - File operations and JSON handling with proper error handling
- `utils.py` - Backward compatibility imports from split utility modules

## Architecture

The package uses a modular approach with clean separation of concerns:
- Class-based data models for clean dot notation access (`track.title` vs `track['title']`)
- Specialized utility modules for different functions
- Direct XML attribute access for efficient parsing
- Comprehensive error handling and validation
- Click-based CLI with proper argument handling

## Design Philosophy

Code follows modern Python practices while maintaining simplicity:
- Clean, readable class-based models replacing dictionary structures
- Modular utility organization for better maintainability
- Comprehensive test coverage for all components
- Clear separation between unit and end-to-end testing
