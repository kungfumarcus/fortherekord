. .\Update-RekordboxLibrary.ps1 -Load

$config = Get-Configuration
$libraryPath = Get-RekordboxLibraryPath $config
$libraryXml = Load-RekordboxLibrary $libraryPath
$tracks = Get-Tracks $libraryXml $config

# Report on top artists by frequency of name as artist
function Write-TopArtists($tracks, $title) {
    $artistCount = @{}
    foreach ($track in $tracks) {
        $artists = $track.Artist -Split "," | ForEach-Object { $_.Trim() }
        foreach ($artist in $artists) {
            if ($artistCount.ContainsKey($artist)) {
                $artistCount[$artist]++
            } else {
                $artistCount[$artist] = 1
            }
        }
    }
    
    $report = $artistCount.GetEnumerator() | Where-Object { $_.Value -ge 2 } | Sort-Object -Property Value -Descending
    if ($report.Count -gt 0) {
        Write-Host
        Write-Host $title
        $rank = 1
        $report | ForEach-Object {
            Write-Host ("{0}. {1}: {2}" -f $rank, $_.Key, $_.Value)
            $rank++
        }
    }
}

Write-TopArtists $tracks.Values "Overall"

foreach ($genreGroup in $tracks.Values | Group-Object -Property Genre) {
    $genre = $genreGroup.Name
    $genreTracks = @()
    foreach ($track in $genreGroup.Group) {
        $genreTracks += $track
    }
    Write-TopArtists $genreTracks $genre
}

