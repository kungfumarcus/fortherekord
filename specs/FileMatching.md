# File Matching Specification

## Scope
Matching tracks between different music libraries using fuzzy text matching and metadata comparison.
Supports interactive mode for users to choose matches for hard-to-match tracks.

## Out of Scope
- Audio fingerprinting or acoustic analysis
- Machine learning or AI-based matching
- Rekordbox metadata processing (see [RekordboxMetadata.md](RekordboxMetadata.md))

## Technical Requirements
- **String Similarity**: Levenshtein distance using `python-Levenshtein` library (faster C implementation)
- **Text Normalization**: Convert to lowercase, remove extra whitespace, strip punctuation for comparison
- **CLI Progress**: Rich library for progress bars during batch processing
- **Interactive UI**: Simple input() prompts with numbered selection lists

## Why Levenshtein Distance
Levenshtein distance is ideal for track matching because:
- **Character-level edits**: Handles typos, extra spaces, different punctuation 
- **Similarity scoring**: Easy conversion to 0.0-1.0 similarity scores
- **Fast implementation**: `python-Levenshtein` C library provides good performance
- **Simple algorithm**: Straightforward to understand and debug
- **Proven effective**: Widely used for fuzzy text matching in music applications

## Function Points

### Search String Preparation Algorithm
Prepares clean strings for Spotify search API

#### Basic Text Cleaning
- Convert to lowercase
- Strip leading/trailing whitespace
- Normalize multiple spaces to single space

#### Artist Separation
- Split artist string on ", " and " & " to handle multiple artists
- Use full artist string for Spotify search (will iterate to optimize search strategy)

### Track Matching Algorithm

#### Basic Similarity Strategy
- Calculate Levenshtein distance for title strings
- Calculate Levenshtein distance for artist strings  
- Convert distances to similarity scores (0.0 to 1.0)
- Combined score = (title_similarity + artist_similarity) / 2
- **Liked Track Bonus**: If track is in user's Spotify liked tracks, add +0.4 to combined score (max 1.0)

#### Matching Thresholds
- Accept matches with combined score > 0.75
- **Note**: Algorithm will be refined based on real data analysis during implementation

#### Text Preparation
- Convert to lowercase
- Strip leading/trailing whitespace
- Normalize multiple spaces to single space

### Mapping Cache Algorithm

#### Cache Storage
- Store mapping for each source track ID (e.g., Rekordbox track ID)
- Save to **RekordBoxSpotifyMapping.json** file (in user config folder alongside config.yaml)
- Make data available to other components
- mapping data is:
  - **target_track_id**: Target platform track ID or null if unmapped
  - **algorithm_version**: String identifier for mapping algorithm used (e.g., "v1.0-basic")
  - **confidence_score**: Final confidence score of the match
  - **timestamp**: When mapping was created
  - **manual_override**: Boolean if user manually selected this match

#### Cache Operations
- Load existing mappings from RekordBoxSpotifyMapping.json on startup
- Skip remapping if cached entry exists (unless --remap flag used)
- Save new mappings to RekordBoxSpotifyMapping.json after each successful/failed match attempt
- Allow filtering by algorithm_version for selective remapping

### Interactive Matching Algorithm
- Present ambiguous matches when confidence below threshold
- Display source track with title, artist, duration
- Show numbered list of potential matches with confidence scores
- Accept user selection by number input or arrow keys with Enter
- Provide skip option for no match found
- Save user decisions for future matching improvements
- Continue processing after user input

### Batch Processing Algorithm
- Process tracks in parallel where possible
- Track progress with per-playlist status updates using Rich library
- Display updating progress bar showing current playlist being processed
- Handle rate limits with retry logic
- Cache results to avoid duplicate processing
- Generate match statistics summary report
