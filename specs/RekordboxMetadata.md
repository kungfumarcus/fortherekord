# Rekordbox Metadata Processing Specification

## Scope
Processing and enhancing Rekordbox track metadata, specifically title field standardization in format: "Title - Artist [Key]"
Extract original metadata from previously processed tracks.

## Out of Scope
- Spotify integration or external API operations
- Track matching between platforms (see [filematching.md](filematching.md))

## Function Points

### Title Enhancement Algorithm
Enhances title field with artist name and key in format: "Title - Artist [Key]"

#### Extract Actual Title
- Remove existing artist suffix if present: split on " - " and take first part
- Remove existing key suffix if present: remove trailing "[Key]" pattern
- Apply configured text replacements (e.g., " (Original Mix)" → "")
- Tokenize and rejoin to normalize whitespace

#### Artist Field Processing
- If artist field empty and title contains " - ", extract artist from title second part
- Remove artist names from title text when they appear in parentheses (e.g., "(Marcus Remix)")
- Only remove if other artists would remain, otherwise keep all artists
- Tokenize artist field and remove duplicates

#### Title Reconstruction
- Combine cleaned title with processed artist: "Title - Artist"
- Append key if available: "Title - Artist [Key]"
- Normalize final whitespace

### Title Extraction Algorithm
Extracts original metadata from previously processed titles

#### Parse Enhanced Title
- Split on " - " to separate title and artist portions
- Extract key from trailing "[Key]" pattern if present
- Handle malformed titles gracefully

#### Restore Original Fields
- Set title field to extracted title portion
- Set artist field to extracted artist portion
- Preserve key field from bracket notation
- Validate extracted data makes sense
