# End-to-End Tests

This folder contains comprehensive E2E tests that validate complete user workflows by running the application exactly as users would - through the CLI interface with real configuration files.

**⚠️ URGENT ISSUE**: Current E2E tests use fake test tracks that won't match in Spotify, making Spotify integration tests incomplete. Additionally, they use real Spotify credentials which could pollute the user's account. This needs to be redesigned before these tests can be considered fully functional.

## Test Structure

### Core E2E Tests
- **`test_basic_library_parsing_without_spotify.py`**: Tests core XML parsing functionality without requiring Spotify credentials
- **`test_full_spotify_sync_workflow.py`**: Complete Spotify integration workflow with real API credentials (requires .env.local)
- **`test_caching_behavior_and_performance.py`**: Cache creation and loading behavior using --use-cache flag
- **`test_text_processing_and_normalization_workflow.py`**: Comprehensive text cleaning and normalization rules
- **`test_playlist_remapping_and_management_workflow.py`**: Playlist remapping functionality using --remap flag

### Test Infrastructure
- **`e2e_test_utils.py`**: Centralized utilities providing:
  - `temporary_config()`: Context manager for realistic config file placement
  - `run_fortherekord()`: Consistent CLI command execution
  - `get_test_library_path()`: Test library file path management
  - `assert_test_library_exists()`: Test library validation

### Test Data
- **`test_library.xml`**: Sample Rekordbox library XML with 30 tracks and 3 playlists for testing

## Testing Philosophy

**Realistic User Simulation**: E2E tests run exactly like real users by:
- Using subprocess to execute CLI commands
- Creating temporary config files in the application's expected location
- Testing actual command-line flags and arguments
- Validating real output and return codes

**Environment Integration**: Tests support:
- Real Spotify API credentials via .env.local file (same file used for general application configuration)
- Temporary cache directories for caching tests
- Config file backup and restore for safe testing

## Running E2E Tests

```bash
# Run all E2E tests (requires .env.local for Spotify tests)
pytest tests/e2e/

# Run individual test
pytest tests/e2e/test_basic_library_parsing_without_spotify.py

# Run only tests that don't require Spotify
pytest tests/e2e/test_basic_library_parsing_without_spotify.py tests/e2e/test_caching_behavior_and_performance.py
```

## Requirements

- **For basic tests**: Only test_library.xml (included)
- **⚠️ For Spotify integration tests**: Currently problematic - uses real credentials but fake tracks that won't match
- **For all tests**: fortherekord package installed in development mode

**Next Session Priority**: Redesign Spotify E2E testing to use either:
1. Separate test Spotify account with controlled test data
2. Mocked Spotify responses while testing real CLI workflows
3. Safe, real track examples that can be tested without account pollution

These tests ensure the application works correctly from the user's perspective, complementing the unit tests that focus on individual components.
