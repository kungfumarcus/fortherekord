# tests/

Unit test suite for the ForTheRekord application.

## Purpose

Contains comprehensive unit tests for all modules and functions in the application. Tests are written using pytest framework following Python testing standards.

## Structure

Tests are organized to mirror the source code structure:
- `test_config.py` - Tests for configuration management
- `test_models.py` - Tests for data structures and models
- `test_rekordbox.py` - Tests for Rekordbox XML parsing
- `test_search_utils.py` - Tests for search text processing utilities
- `test_file_utils.py` - Tests for file operations and JSON handling
- `test_matching.py` - Tests for track matching algorithms
- `test_spotify.py` - Tests for Spotify API integration
- `test_main.py` - Tests for CLI interface
- `conftest.py` - Shared test fixtures and configuration

## Testing Approach

Tests focus on the simplified dictionary-based approach and verify:
- Configuration loading and validation
- XML parsing accuracy
- Text processing functions
- CLI flag handling
- Error conditions and edge cases

## Running Tests

```bash
pytest tests/
```
