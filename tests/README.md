# tests/

Test suite for the ForTheRekord application with both unit and end-to-end tests.

## Purpose

Contains comprehensive tests for all modules and functions in the application. Tests are written using pytest framework following Python testing standards.

## Structure

### Unit Tests
Unit tests focus on testing individual classes and functions in isolation:
- `test_config.py` - Tests for configuration management classes
- `test_models.py` - Tests for data structures and model classes
- `test_rekordbox.py` - Tests for Rekordbox XML parsing functions
- `test_search_utils.py` - Tests for search text processing utilities
- `test_file_utils.py` - Tests for file operations and JSON handling
- `test_matching.py` - Tests for track matching algorithms
- `test_spotify.py` - Tests for Spotify API integration classes
- `test_main.py` - Tests for CLI interface functions
- `conftest.py` - Shared test fixtures and configuration

### End-to-End Tests (e2e/)
E2E tests run complete user workflows through the CLI interface. Each file contains exactly one focused test:
- `test_basic_library_parsing_without_spotify.py` - Library parsing without Spotify credentials
- `test_full_spotify_sync_workflow.py` - Complete Spotify API integration workflow  
- `test_caching_behavior_and_performance.py` - Caching functionality and performance testing
- `test_text_processing_and_normalization_workflow.py` - Text cleaning and normalization workflows
- `test_playlist_remapping_and_management_workflow.py` - Playlist management and remapping with --remap flag

**Note**: E2E test files use descriptive names that clearly indicate their purpose and contain a single focused test each, rather than multiple test methods per file.

## Testing Philosophy

**Unit Tests**: Focus on testing individual classes and functions in isolation using mocks and fixtures. Test specific behaviors, edge cases, and error conditions. Each test file may contain multiple test methods covering different aspects of the module.

**End-to-End Tests**: Test complete user workflows exactly as users would experience them, including CLI execution, real file operations, and actual API integrations (where configured). Each E2E test file contains exactly one focused test to keep workflows simple and clear.

## Testing Approach

Unit tests focus on isolated components and verify:
- Configuration loading and validation
- XML parsing accuracy
- Text processing functions
- CLI flag handling
- Error conditions and edge cases

E2E tests focus on complete workflows and verify:
- Full CLI command execution
- Real file system operations
- Integration between components
- User experience scenarios

## Running Tests

### Unit Tests Only
```bash
pytest tests/ --ignore=tests/e2e/
```
Or use the provided batch file:
```bash
test.bat
```

### E2E Tests Only  
```bash
pytest tests/e2e/
```
Or use the provided batch file:
```bash
test_e2e.bat
```

**Note**: E2E tests that require Spotify integration need credentials configured in a `.env.local` file (which is also used for general application configuration). See the E2E README for details.

### All Tests
```bash
pytest tests/
```

**Note**: E2E tests are excluded from the main `test.bat` file to keep unit test runs fast and avoid dependencies on external services or test data setup.
