# Rekordbox Database Architecture Notes

## Overview
Rekordbox 6 uses a SQLCipher-encrypted SQLite database (`master.db`) to store library information. The database is accessed via the `pyrekordbox` library which handles decryption and provides an ORM interface.

## Key Tables

### djmdPlaylist
Stores playlist definitions including smart playlists.
- `ID`: Unique playlist identifier
- `Name`: Playlist name
- `Attribute`: Playlist type (0=normal, 1=folder, 4=smart playlist)
- `ParentID`: Parent playlist ID for hierarchy
- `SmartList`: XML string containing smart playlist criteria (only for smart playlists)
- `UUID`: Universal unique identifier

### djmdContent
Stores track metadata.
- `ID`: Unique track identifier (ContentID)
- `Title`: Track title
- `GenreID`: Reference to djmdGenre table (not GenreName!)
- Note: MyTag associations are NOT stored directly in this table

### djmdMyTag
Stores MyTag definitions.
- `ID`: MyTag identifier (can be positive or negative in different contexts)
- `Name`: MyTag name (e.g., "deep", "intro", "bush")
- `ParentID`: Parent MyTag for hierarchy
- `Attribute`: MyTag type

### djmdSongMyTag
Junction table linking tracks to MyTags (many-to-many relationship).
- `ContentID`: Reference to djmdContent
- `MyTagID`: Reference to djmdMyTag
- This is the ground truth for which tracks have which MyTags

### djmdCloudFilterPlaylist
Stores smart playlist filter metadata (NOT the actual filter criteria).
- `PlaylistUUID`: Links to djmdPlaylist.UUID
- `ParentID`: Can reference parent filter for hierarchical conditions
- Note: The actual filter criteria are stored in the SmartList XML in djmdPlaylist

## Smart Playlist Architecture

### SmartList XML Format
Smart playlists store their criteria in an XML format in djmdPlaylist.SmartList:
```xml
<NODE Id="..." LogicalOperator="1" AutomaticUpdate="0">
  <CONDITION PropertyName="genre" Operator="1" ValueUnit="" ValueLeft="Techno" ValueRight=""/>
  <CONDITION PropertyName="myTag" Operator="8" ValueUnit="" ValueLeft="-1712882025" ValueRight=""/>
  <CONDITION PropertyName="myTag" Operator="8" ValueUnit="" ValueLeft="287726657" ValueRight=""/>
</NODE>
```

- `LogicalOperator`: 1=ALL conditions must match (AND), 0=ANY condition (OR)
- `Operator`: 1=EQUAL, 8=CONTAINS, etc.
- `PropertyName`: Field to filter on (genre, myTag, bpm, etc.)

### MyTag ID Encoding
**CRITICAL**: MyTag IDs in SmartList XML can be negative or positive:
- **Negative IDs** (e.g., `-1712882025`): Need bit-shift transformation via `id + 2^32` to get actual djmdMyTag.ID
- **Positive IDs** (e.g., `287726657`): Used directly, no transformation needed

This appears to be related to how Rekordbox stores IDs internally vs. in smart playlists.

## pyrekordbox Library Details

### ORM Model
- `DjmdContent.MyTagIDs`: An `association_proxy` that provides access to related MyTag IDs
- Returns a list of MyTag IDs by traversing: `DjmdContent` → `djmdSongMyTag` → `MyTag.ID`

### Known Bugs/Limitations

#### 1. Smart Playlist MyTag Filtering
**Issue**: Some smart playlists with multiple MyTag CONTAINS conditions return 0 tracks despite tracks existing that match all conditions.

**Root Cause**: The pyrekordbox smartlist evaluation uses `.contains()` on the `MyTagIDs` association proxy:
```python
DjmdContent.MyTagIDs.contains(mytag_id)
```

This doesn't generate correct SQL for checking MyTag membership through the junction table. The correct approach would be:
```python
DjmdContent.MyTags.any(DjmdSongMyTag.MyTagID == mytag_id)
```

**Impact**: Affects playlists with LogicalOperator=1 (ALL) and multiple MyTag conditions. Single MyTag conditions often work by chance.

**Workaround**: 
1. Recreate the smart playlist in Rekordbox (may assign positive IDs that work better)
2. Use the warning system to alert users about empty smart playlists
3. Manually verify in Rekordbox if tracks should be in the playlist

#### 2. Month-Based Date Filters
**Issue**: Smart playlists using month-based date filters (e.g., "tracks added in last 3 months") fail with attribute errors.

**Root Cause**: pyrekordbox doesn't properly handle the month-based date filter evaluation.

**Workaround**: Change smart playlists to use week-based filters instead (e.g., "last 12 weeks").

## Debugging Tips

### Check if MyTag Assignment Exists
```python
# Query tracks with both MyTag1 and MyTag2
query = """
SELECT c.ID, c.Title
FROM djmdContent c
JOIN djmdSongMyTag smt1 ON c.ID = smt1.ContentID AND smt1.MyTagID = 'mytag1_id'
JOIN djmdSongMyTag smt2 ON c.ID = smt2.ContentID AND smt2.MyTagID = 'mytag2_id'
"""
```

### Transform Negative MyTag IDs
```python
def right_bitshift(x: int, nbit: int = 32) -> int:
    return int(x + 2**nbit)

# If SmartList has ValueLeft="-1712882025"
actual_id = right_bitshift(-1712882025)  # Returns 2582085271
```

### Check Smart Playlist Attributes
- `djmdPlaylist.Attribute == 4`: Smart playlist
- Empty `djmdSongPlaylist` entries for smart playlists is NORMAL (they're computed, not stored)
- Check `djmdPlaylist.SmartList` XML for actual criteria

## References
- pyrekordbox GitHub: https://github.com/dylanljones/pyrekordbox
- Known issue with MyTag smart playlists: PR #142
- Database encryption uses device-specific keys stored in system registry/config
