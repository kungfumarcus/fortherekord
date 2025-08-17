# File Matching Specification

## Scope
Matching tracks between different music libraries using fuzzy text matching and metadata comparison.
Supports interactive mode for users to choose matches for hard-to-match tracks.

## Out of Scope
- Audio fingerprinting or acoustic analysis
- Machine learning or AI-based matching
- Rekordbox metadata processing (see [RekordboxMetadata.md](RekordboxMetadata.md))

## Function Points

### Search String Preparation Algorithm
Prepares clean strings for Spotify search API

#### Title Tokenization
- Split on whitespace and normalize to single spaces
- Convert to lowercase for comparison

#### Artist Tokenization
- Split on ", " and " & " to separate multiple artists
- Convert to lowercase for comparison

### Track Matching Algorithm

#### Progressive Search Strategy
- **Phase 1**: Raw text search using original title and artist strings
- **Phase 2**: If no good match (score < 0.75), retry with cleaned/tokenized strings
- **Phase 3**: Combine results from both phases, select best overall match
- **Phase 4**: If still no match above threshold, mark as unmapped

#### Similarity Scoring
- Calculate Levenshtein distance for title strings
- Calculate Levenshtein distance for artist strings
- Convert distances to similarity scores (0.0 to 1.0)
- Base score = (title_similarity + artist_similarity) / 2
- **Liked Track Bonus**: If track is in user's Spotify liked tracks, add +0.4 to base score (max 1.0)

#### Matching Logic
- Accept matches with overall score > 0.75 (or > 0.35 for liked tracks due to bonus)
- Prioritize liked tracks even with moderate text similarity
- Return highest scoring match above threshold
- Mark as unmapped if no matches above threshold

### Mapping Cache Algorithm

#### Cache Storage
- Store mapping for each source track ID (e.g., Rekordbox track ID)
- **target_track_id**: Target platform track ID or null if unmapped
- **algorithm_version**: String identifier for mapping algorithm used (e.g., "v1.0-progressive")
- **confidence_score**: Final confidence score of the match
- **timestamp**: When mapping was created
- **manual_override**: Boolean if user manually selected this match

#### Cache Operations
- Load existing mappings on startup
- Skip remapping if cached entry exists (unless --remap flag used)
- Save new mappings after each successful/failed match attempt
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
- Track progress with status updates
- Handle rate limits with retry logic
- Cache results to avoid duplicate processing
- Generate match statistics summary report
