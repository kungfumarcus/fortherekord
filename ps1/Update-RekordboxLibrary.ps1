param (
    [switch]$All,
    [switch]$Load
)

$CONFIG_FILE_NAME = "Update-RekordboxLibrary.config"
$CONFIG_FILE_PATH = Join-Path -Path $PSScriptRoot -ChildPath $CONFIG_FILE_NAME
    
function Get-Configuration() {
    # Open the configuration file (in the same folder as this script), creating one if it doesn't exist
    if (-not (Test-Path $CONFIG_FILE_PATH)) {
        [xml]$configXml = New-Object xml
    } else {
        [xml]$configXml = Get-Content $CONFIG_FILE_PATH
    }

    # Load the config, creating any missing nodes as we go
    if (-not $configXml.SelectSingleNode("//config")) {
        $configNode = $configXml.CreateElement("config")
        $configXml.AppendChild($configNode) | Out-Null
    } else {
        $configNode = $configXml.SelectSingleNode("//config")
    }

    # Load the library path from the config, using the default if it doesn't exist
    $libraryPathNode = $configNode.SelectSingleNode("libraryPath")
    if (-not $libraryPathNode) {
        $libraryPathNode = $configXml.CreateElement("libraryPath")
        $configNode.AppendChild($libraryPathNode) | Out-Null
    }
    if (-not $libraryPathNode.InnerText) {
        $libraryPathNode.InnerText = Join-Path -Path $PSScriptRoot -ChildPath "rekordbox.xml"
    }

    # Load the replaceInTitle value from the config, using the default if it doesn't exist
    $replaceInTitleNode = $configNode.SelectSingleNode("replaceInTitle")
    if (-not $replaceInTitleNode) {
        $replaceInTitleNode = $configXml.CreateElement("replaceInTitle")
        $replaceInTitleNode.InnerText = " (Original Mix)"
        $configNode.AppendChild($replaceInTitleNode) | Out-Null
    }

    $ignorePlaylists = $configNode.SelectSingleNode("ignorePlaylists")
    if (-not $replaceInTitleNode) {
        $replaceInTitleNode = $configXml.CreateElement("ignorePlaylists")
        $configNode.AppendChild($ignorePlaylists) | Out-Null
    }

    $configXml
}

function Save-Configuration($config) {
    $config.Save($CONFIG_FILE_PATH) 
}

function Get-RekordboxLibraryPath($config) {
    $libraryPath = $config.config.libraryPath
    if (-not $config.config.libraryPath) {
        $libraryPathNode = $config.config.CreateElement("libraryPath")
        $config.config.AppendChild($libraryPathNode) | Out-Null
    }
    do {
        if (-not (Test-Path $libraryPath -PathType Leaf)) {
            [string]$libraryPath = Read-Host "Enter the path to your exported Rekordbox library XML file"
            $config.config.libraryPath = $libraryPath
        }
    } until (Test-Path $libraryPath -PathType Leaf)
    $libraryPath
}

function Load-RekordboxLibrary($libraryPath) {
    Write-Host "Loading library from '$libraryPath'..."
    $libraryXml = [xml]::new()
    $libraryXml.PreserveWhitespace = $true
    $libraryXml.Load($libraryPath)
    $libraryXml
}

function Get-RekordboxCollectionTracks($libraryXml) {
    return $libraryXml.DJ_PLAYLISTS.COLLECTION.TRACK | `
        ForEach-Object -Begin { $ht = @{} } -Process { $ht[$_.TrackID] = $_ } -End { return $ht } 
}

function Get-TracksFromPlaylist($playlist, $collectionTracks, $ignorePlaylists = @(), [switch]$recurse) {
    if ($playlist.Name -in $ignorePlaylists) {
        return @()
    }

    $playlistTracks = $playlist.SelectNodes("TRACK")
    Write-host "Processing playlist '$($playlist.Name)' with $($playlistTracks.Count) tracks"
    $tracks = $playlistTracks | ForEach-Object { $collectionTracks[$_.Key] }
    
    if ($recurse) {
        foreach ($childPlaylist in $playlist.SelectNodes("NODE")) {
            $tracks += Get-TracksFromPlaylist $childPlaylist $collectionTracks $ignorePlaylists -recurse:$recurse
        }
    }
    
    return $tracks
}

function Get-Tracks($libraryXml, $config, [switch]$All) {
    $collectionTracks = Get-RekordboxCollectionTracks $libraryXml    
    
    if ($All) {
        $tracks = $collectionTracks 
    
    } else {
        $tracks = @{}
        $ignorePlaylists = $config.config.ignorePlaylists -split "," | ForEach-Object { $_.Trim() }
        
        Write-Host "Processing playlists..."
        foreach ($playlist in $libraryXml.SelectNodes("DJ_PLAYLISTS/PLAYLISTS/NODE")) {
            $playlistTracks = Get-TracksFromPlaylist $playlist $collectionTracks $ignorePlaylists -recurse
            foreach ($playlistTrack in $playlistTracks) {
                if (-not $tracks.ContainsKey($playlistTrack.TrackID)) {
                    $tracks[$playlistTrack.TrackID] = $playlistTrack
                }
            }
        }
    }

    Write-Host "Found $($tracks.Count) tracks to process"
    Write-Host
    $tracks
}

function Update-MemoryQueues($track) {

    # Copy hot cues as memory cues
    $hotCues = $track.SelectNodes("POSITION_MARK[@Num!=-1]")
    $memoryCues = $track.SelectNodes("POSITION_MARK[@Num=-1]")
    $memoryCueMap = @{} # Dictionary to track existing memory cues
    foreach ($memoryCue in $memoryCues) {
        $memoryCueMap[$memoryCue.OuterXml] = $memoryCue
    }

    # Add or update memory cues based on hot cues
    $memoryCuesAdded = 0
    foreach ($hotCue in $hotCues) {
        $memoryCue = $track.OwnerDocument.CreateElement("POSITION_MARK")
        $memoryCue.SetAttribute("Name", $hotCue.Name)
        $memoryCue.SetAttribute("Start", $hotCue.Start)
        $memoryCue.SetAttribute("Type", $hotCue.Type)    
        $memoryCue.SetAttribute("Num", "-1")
        if (!$memoryCueMap.ContainsKey($memoryCue.OuterXml)) {
            $track.AppendChild($memoryCue) | Out-Null
            $memoryCuesAdded++
        }
    }

    # Remove any memory cues that were not updated
    $memoryCuesDeleted = 0
    foreach ($unusedMemoryCue in $memoryCueMap.Values) {
        $track.RemoveChild($unusedMemoryCue) | Out-Null
        $memoryCuesDeleted++
    }

    $updated = $false
    if ($memoryCuesAdded -gt 0) {
        Write-Host "Copied $memoryCuesAdded hot cues as memory cues for title '$title'"
        $updated = $true
    }
    if ($memoryCuesDeleted -gt 0) {
        Write-Host "Deleted $memoryCuesDeleted memory cues for title '$title'"
        $updated = $true
    }
    $updated    
}

function Update-Tracks($tracks, $config) {
    Write-Host "Updating tracks,..."
    $updatedTrackIDs = @{}
    foreach ($track in $tracks.Values) {
        $title = $track.Name.Trim() -Replace '\s+', ' '
        if ($title -ne $track.Name) {
            Write-Host "Removed whitespace from title '$($track.Name)'"
        }
        $title = $title -Replace '\s\[..?.?\]$', ''
        
        if ($track.Artist) {
            $artist = $track.Artist.Trim() -Replace '\s+', ' '
            if ($artist -ne $track.Artist) {
                Write-Host "Removed whitespace from artist '$($track.Artist)'"
            }
        } elseif ($title -like "* - *") {
            # Set the artist if it is missing but present in the title                
            $artist = ($title -split " - ")[1]
            if (-not $title.EndsWith("- $($track.Artist)")) {
                Write-Host "Set artist name for '$title' to '$artist' by '$artist'"
            } else {
                Write-Host "Set artist name for '$title' to '$artist'"
            }
        } else {
            Write-Host "WARNING: Track '$title' has no artist name"
            $artist = ""
        }

        # Remove any configured text from the track title
        $replaceInTitle = [string]$config.config.replaceInTitle -Split "," | Where-Object { $_ -ne ' ' }
        foreach ($replaceText in $replaceInTitle) {
            if ($replaceText.Contains(":")) {
                $textFrom, $textTo = $replaceText -Split ":"
            } else {
                $textFrom = $replaceText
                $textTo = ""
            }
            if ($title.Contains($textFrom)) {
                $title = $title.Replace($textFrom, $textTo).Trim()
                if ($textTo) {
                    Write-Host "Replaced text '$textFrom' with '$textTo' in title '$title'"
                } else {
                    Write-Host "Removed text '$textFrom' from title '$title'"
                }
            }
            if ($artist -and $artist.Contains($textFrom)) {
                $artist = $artist.Replace($textFrom, $textTo).Trim()
                if ($textTo) {
                    Write-Host "Replaced text '$textFrom' with '$textTo' in artist '$artist'"
                } else {
                    Write-Host "Removed text '$textFrom' from artist '$artist'"
                }
            }
        }

        if ($artist) {
            # Remove any artists from $artist if they appear in the title (unless they all do)
            $titleMinusArtist = $title.Replace(" - $artist", "")
            $artists = $artist -split '\s*,\s*'
            $removedArtists = @()
            $retainedArtists = @()
            foreach ($individualArtist in $artists) {
                if ($titleMinusArtist.Contains($individualArtist)) {
                    $removedArtists += $individualArtist
                } else {
                    $retainedArtists += $individualArtist
                }
            }
            if ($removedArtists.Count -gt 0 -and $retainedArtists.Count -gt 0) {
                $artist = $retainedArtists -join ", "
                Write-Host "Removed artist(s) '$($removedArtists -join ", ")' from title '$titleMinusArtist' with artists '$artist'"
            }

            # Update the track title to include the artist name
            $artistSuffix = " - $artist"
            if ($title.Contains($artistSuffix)) {
                $title = $title.Replace($artistSuffix, "")
            } else {
                Write-Host "Added artist name to title '$title'"
            }
            $title =  "$title$artistSuffix"
        }

        # Add the key to the track title
        if ($track.Tonality) {
            $keySuffix = " [$($track.Tonality)]"
            if ($title.Contains($keySuffix)) {
                $title = $title.Replace($keySuffix, "")
            }
            $title = "$title [$($track.Tonality)]"
        }

        $updated = $false #Update-MemoryQueues $track 
        if ($track.Name -ne $title) {
            $track.SetAttribute("Name", $title)
            $updated = $true
        }
        if ($track.Artist -ne $artist) {
            $track.SetAttribute("Artist", $artist)
            $updated = $true
        }
        if ($updated) {
            $updatedTrackIDs[$track.TrackID] = $track
        }
    }
    Write-Host
    Write-Host "Modified $($updatedTrackIds.Count) tracks"
    Write-Host
    $updatedTrackIDs
}

function Remove-OtherTracksFromCollection($libraryXml, $trackIDs) {
    # NOTE: There were performance issues manually removing each track node from the original collection node, so we
    # instead create a new collection node and add the old nodes to it.
    $collection = $libraryXml.DJ_PLAYLISTS.COLLECTION
    $trackCount = $collection.TRACK.Count
    $removedTrackCount = 0

    $newCollection = $libraryXml.CreateElement("COLLECTION")
    foreach ($track in $collection.TRACK) {
        if ($trackIDs.ContainsKey($track.TrackID)) {
            #$track.ParentNode.RemoveChild($track) | Out-Null
            $newCollection.AppendChild($track) | Out-Null
        } else {
            $removedTrackCount++
        }
    }
    $newCollection.SetAttribute("Entries", $trackIDs.Count)
    $libraryXml.DJ_PLAYLISTS.ReplaceChild($newCollection, $collection) | Out-Null
    Write-Host "Removed $($removedTrackCount) tracks from the collection of $($trackCount) tracks"
}

function Remove-Playlists($libraryXml) {
    foreach ($playlist in $libraryXml.DJ_PLAYLISTS.PLAYLISTS) {
        $playlist.ParentNode.RemoveChild($playlist) | Out-Null
    }

    Write-Host "Removed all playlists from library"
}

function Test-TrackDuplicates($tracks) {
    Write-Host "Checking for duplicates..."
    $titles = @{}
    foreach ($track in $tracks.Values) {
        $title = $track.Name
        if ($titles.ContainsKey($title)) {
            $titles[$title] += 1
        } else {
            $titles[$title] = 1
        }
    }
    foreach ($title in $titles.Keys) {
        if ($titles[$title] -gt 1) {
            Write-Host "WARNING: Duplicate track found: $title"
        }
    }    
    Write-Host
}

function Save-RekordboxLibrary($libraryPath, $newLibraryPath, $newLibraryXml) {
    [xml]$libraryXml = Get-Content $libraryPath
    if ($newLibraryXml.OuterXml -ne $libraryXml.OuterXml) {
        Write-Host "Saving updated library to '$newLibraryPath'..."
        $utf8WithoutBom = New-Object System.Text.UTF8Encoding
        $streamWriter = New-Object System.IO.StreamWriter($newLibraryPath, $false, $utf8WithoutBom)
        $newLibraryXml.Save($streamWriter) | Out-Null
        $streamWriter.Close()
    } else {
        Write-Host "No changes needed"
    }
}

function Run() {
    $config = Get-Configuration
    $libraryPath = Get-RekordboxLibraryPath $config
    $libraryXml = Load-RekordboxLibrary $libraryPath
    Save-Configuration $config
    $tracks = Get-Tracks $libraryXml $config
    $updatedTracks = Update-Tracks $tracks $config
    Test-TrackDuplicates $tracks
    Remove-OtherTracksFromCollection $libraryXml $updatedTracks
    Remove-Playlists $libraryXml
    Save-RekordboxLibrary $libraryPath ($libraryPath -Replace '\.xml$', '-import.xml') $libraryXml
}

if (-not $Load) {
    Run
}