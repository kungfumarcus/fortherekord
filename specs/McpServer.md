# MCP Server Specification

## Scope

An MCP server so an agent can inspect and clean a Rekordbox library. Domain types: **PlaylistFolder**, **Playlist**, **SmartPlaylist**, **Track**, **HistoryFolder**, **HistorySession**.

These are not variants of one “playlist row.” A folder contains things. A playlist is a curated track list. A smart playlist is a saved query whose results are derived. A track is a collection item.

The existing [models.py](../src/fortherekord/models.py) types are the Spotify-sync view. They are not this contract.

How the adapter persists these is [Rekordbox.md](Rekordbox.md)’s problem, not the API’s.

## Out of Scope

- Adding or removing tracks from the **collection** (import / delete file from library)
- Cues, beatgrids, analysis files
- Keyboard or MIDI mappings
- Filesystem copy/zip (the MCP host copies files; this server only reads and updates Rekordbox)
- Spotify sync

## Safety

- Writes require Rekordbox closed
- Mutations return a diff and apply only when confirmed
- Smart playlist **results** cannot be edited as a list; you change `criteria` and the results follow

## PlaylistFolder

A node in the playlist tree. It holds other folders, playlists, and smart playlists. It does not hold tracks.

```
id          string
name        string
parent      PlaylistFolder | null     # null = root
position    int                       # order among siblings
path        string                    # "bush techno / nights"
```

| Field | Editable | Notes |
|---|---|---|
| `id` | no | Assigned on create |
| `name` | yes | |
| `parent` | yes | Move; must be a folder or root |
| `position` | yes | Reorder among siblings |
| `path` | no | Derived from ancestor names |

Children are not a field you patch. You create, move, or delete the child entity.

**Create** a folder (`name`, optional `parent`, optional `position`).  
**Delete** fails if it still has children, unless recursive.

## Playlist

A named, ordered list of tracks the user curates.

```
id          string
name        string
folder      PlaylistFolder | null
position    int
path        string
tracks      Track[]                   # ordered; identity is enough on write
```

| Field | Editable | Notes |
|---|---|---|
| `id` | no | |
| `name` | yes | |
| `folder` | yes | Move |
| `position` | yes | |
| `path` | no | Derived |
| `tracks` | yes | Add, remove, replace, reorder |

A track’s place in a playlist is membership of this playlist, not a property of the track.

## SmartPlaylist

A saved query. The track list is the result of evaluating `criteria`, not a list anyone edits.

```
id          string
name        string
folder      PlaylistFolder | null
position    int
path        string
tracks      Track[]                   # current results
criteria    Criteria                  # required on create
```

| Field | Editable | Notes |
|---|---|---|
| `id` | no | |
| `name` | yes | |
| `folder` | yes | Move |
| `position` | yes | |
| `path` | no | Derived |
| `tracks` | no | Derived from `criteria` |
| `criteria` | yes | Replace the whole query |

**Create** requires `name` and `criteria`. An empty condition list is rejected.

You cannot turn a folder into a playlist or a playlist into a smart playlist. They are different types.

## Criteria

A value object: how to match, plus an ordered list of conditions. One level only — all conditions combined with `all` or `any`. No nested groups.

```
Criteria
  match         "all" | "any"
  conditions    Condition[]           # at least one

Condition
  field         Field
  operator      Operator
  value         Value
```

`Value` depends on the operator:

- single: a string or number (`"Techno"`, `128`, `4`)
- range: `{ min, max }` for `between`
- period: `{ amount, unit }` for `in_last` / `not_in_last` — `unit` is `day` or `week`

### Fields

Names match Track where the same fact exists.

| Field | Kind | Operators |
|---|---|---|
| `title` | text | is, is_not, contains, not_contains, starts_with, ends_with |
| `artist` | text | same |
| `album` | text | same |
| `album_artist` | text | same |
| `original_artist` | text | same |
| `remixer` | text | same |
| `composer` | text | same |
| `genre` | text | same |
| `label` | text | same |
| `comments` | text | same |
| `key` | text | same |
| `filename` | text | same |
| `tags` | tag | contains, not_contains |
| `bpm` | number | is, is_not, greater, less, between |
| `rating` | number | same |
| `duration` | number | same |
| `year` | number | same |
| `play_count` | number | same |
| `bitrate` | number | is, is_not, greater, less, between |
| `file_type` | text | is, is_not, contains, not_contains, starts_with, ends_with |
| `date_added` | date | is, is_not, greater, less, between, in_last, not_in_last |
| `date_created` | date | same |
| `date_released` | date | same |
| `color` | text | is, is_not |
| `location` | text | is, is_not, contains, starts_with |
| `missing` | flag | is |

Illegal field/operator pairs are rejected. `tags` values are tag **names**; the adapter resolves IDs. `in_last` / `not_in_last` with `month` is not in the contract (known broken evaluation). `bitrate` and `file_type` are search-only (Rekordbox smart-list XML has no matching properties).

Examples the agent should be able to say:

- genre is Techno **and** bpm between 126–132
- tags contain `dark` **or** tags contain `deep`
- date_added in the last 14 days
- rating ≥ 4 and key is 8A
- location starts with `D:\Aug - 2026`

## Track

A collection item. You patch properties; you do not create or delete the track in this slice.

```
id            string

title         string
artist        string
album         string | null
genre         string | null
label         string | null
comments      string | null
rating        int | null              # 0–5 stars
color         string | null           # e.g. "Pink"
tags          string[]

key           string | null           # e.g. "8A", "Am"
bpm           number | null           # 128.0

duration      Duration                # playback length
location      FileLocation | null     # where the audio file is
missing       bool                    # file not at location
date_added    Date | null
bitrate       int | null              # kbps from Rekordbox analysis (e.g. 320)
file_type     string | null           # mp3, wav, flac, aiff, m4a
play_count    int | null              # Rekordbox DJPlayCount

```

| Field | Editable | Why |
|---|---|---|
| `id` | no | Identity |
| `title` | yes | Catalog |
| `artist` | yes | Catalog |
| `album` | yes | Catalog |
| `genre` | yes | Catalog |
| `label` | yes | Catalog |
| `comments` | yes | Catalog |
| `rating` | yes | Catalog |
| `color` | yes | Catalog |
| `tags` | yes | Catalog (Rekordbox My Tags) |
| `key` | yes | DJs correct this |
| `bpm` | yes | DJs correct this |
| `duration` | no | From the file |
| `location` | no | Change via a relocate command, not a property patch |
| `missing` | no | Observed from disk |
| `date_added` | no | Library history |
| `bitrate` | no | Rekordbox `BitRate` column, as kbps |
| `file_type` | no | From Rekordbox `FileType` |
| `play_count` | no | Rekordbox `DJPlayCount` |

`location` is shown so an agent can see the path and whether the file is `missing`. Rewriting the path is a relocate use case, not “edit location like a title.”

List tools return summaries (id, name, path; or id, title, artist, key, bpm, location, missing). Get-by-id returns the full entity.

## HistoryFolder

A node in the Rekordbox **History** tree. It holds other history folders and sessions. Read-only.

```
id          string
name        string
parent      HistoryFolder | null
position    int
path        string
```

## HistorySession

A recorded performance. Tracks are the running order (`TrackNo`), so neighbours are what was mixed in sequence. Read-only. No mix-in points or per-track play duration.

```
id          string
name        string
folder      HistoryFolder | null
position    int
path        string
date        Date | null               # session DateCreated
tracks      Track[]                   # ordered setlist
```

**list_history_tree** returns folder/session summaries. **get_history** returns a session with ordered track summaries. **get_history_folder** returns a folder.

Search history sessions by id, name, path, folder, position, date, or contained track.

## Running

Install extras and start from this repo:

```bash
pip install -e ".[mcp]"
fortherekord-mcp
```

Cursor MCP config (stdio). Use the venv that has this package installed:

```json
{
  "mcpServers": {
    "rekordbox": {
      "command": "fortherekord-mcp"
    }
  }
}
```

The server only reads and updates Rekordbox. The host copies files.

## Search

Every entity can be found by its properties. Search is a query, not a filesystem walk.

**Tracks** use the same `Criteria` value object as a smart playlist — an unsaved query. `search_tracks(criteria)` is how you review “everything under `D:\Aug - 2026`” (`location` starts with that prefix). The host copies files if it needs to.

**PlaylistFolder**, **Playlist**, **SmartPlaylist**, **HistoryFolder**, and **HistorySession** each have their own search, same shape (`match` + conditions):

| Field | Folder | Playlist | Smart playlist | History folder | History session | Kind |
|---|---|---|---|---|---|---|
| `id` | yes | yes | yes | yes | yes | id (`is`, `is_not`) |
| `name` | yes | yes | yes | yes | yes | text |
| `path` | yes | yes | yes | yes | yes | text |
| `parent` | yes | no | no | yes | no | id |
| `folder` | no | yes | yes | no | yes | id |
| `position` | yes | yes | yes | yes | yes | number |
| `date` | no | no | no | no | yes | date |
| `track` | no | yes | no | no | yes | id (`contains`, `not_contains`) |

`track` means “this playlist or history session contains that track,” not a property of the track.

You do not search smart playlists by the contents of `criteria` in this slice (that is a saved query, not a filter field). You search them by name, path, folder, position, id.

Results are summaries. Combine conditions with `all` or `any` the same way as `Criteria`.
