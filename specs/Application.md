# ForTheRekord Application Specification

## Scope

A command-line application that provides additional functionality for Rekordbox DJs.
* Update Rekordbox track properties such as title and artist, cleaning up unneeded text and adding extra information in titles (see [RekordboxMetadata.md](RekordboxMetadata.md))
* Create and synchronize Spotify playlists matching your Rekordbox playlists. This requires fuzzy matching logic to match tracks with different text in title and artist (see [filematching.md](filematching.md) and [Spotify.md](Spotify.md))
* Follow artists found in multiple tracks in your Rekordbox playlists
* Create Rekordbox smart playlists based on playlist track MyTag values
* Rich configuration allowing custom behavior to suit the user's requirements

The application integrates directly with the Rekordbox database for real-time access and updates (see [Rekordbox.md](Rekordbox.md)).

## Out of Scope

The following features are explicitly not included in this initial implementation:

- **Performance Requirements**: No specific performance targets defined (implement efficiently but no quantified metrics)
- **GUI Interface**: Command-line only

## Technical Requirements

- **Platform**: Python 3.8+ console application
- **Package Management**: pyproject.toml with modern Python packaging

## Function Points

### Command Line Interface

**Basic Usage:**
- `fortherekord` - Standard usage, processes Rekordbox database and implements configured behaviors
- `fortherekord --remap` - Clear existing track mappings and then run as normal
- `fortherekord --spoify-cache` - Use cached liked tracks instead of fetching from Spotify
- `fortherekord --interactive` - Enable interactive track matching mode

**Options:**
- `--verbose` - Enable Information level logging output
- `--debug` - Enable Debug level logging output (includes Information level)
- `--help` - Display usage information

**Exit Codes:**
- `0` - Success
- `1` - Error

### Main Flow
- Load user configuration
- Connect to Rekordbox database
- Library Cleanup
  - Cleanup and update track name and artist properties directly in database
  - Create smart playlists based on MyTag values
- Sync Spotify
  - Authenticate with Spotify using OAuth
  - Load Spotify liked tracks
  - Sync Spotify Playlists
    - Load cached track mappings
    - Execute playlist synchronization
    - Save updated mappings
  - Follow popular artists based on threshold
