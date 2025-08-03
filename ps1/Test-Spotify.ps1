. .\Update-Spotify.ps1 -Load

$config = Get-Configuration
$accessToken, $refreshToken = Authenticate-Spotify `
    -clientId $config.config.spotifyClientId `
    -clientSecret $config.config.spotifyClientSecret `
    -scope "playlist-read-private playlist-modify-private user-library-read"
$libraryPath = Get-RekordboxLibraryPath $config
# $libraryXml = Load-RekordboxLibrary $libraryPath
# $likedTracks = Get-LikedTracks $accessToken -fromCache:$true

$collectionTracks = Get-RekordboxCollectionTracks $libraryXml
$unmappedTrackIds = (Get-MappedTracks).GetEnumerator() | Where-Object { -not $_.Value } | ForEach-Object { $_.Key }
$unmappedTracks = $collectionTracks.GetEnumerator() | Where-Object { $unmappedTrackIds -contains $_.Key } | ForEach-Object { $_.Value }   

foreach ($track in $unmappedTracks) {
    $title = Get-SearchTitle $track
    $artist = $track.Artist
    Write-Host "[ Searching for track: '$title' by '$artist' ]"
    $spotifyTracks = Find-SpotifyTrack $accessToken "track:$title artist:$artist" -verbose:$true
    Write-Host "Found $($spotifyTracks.Count) matches."
    if ($spotifyTracks.Count -ne 0) {
        $index = 1
        foreach ($spotifyTrack in $spotifyTracks) {
            Write-Host "($($index++)) $($spotifyTrack.Name) by $($spotifyTrack.Artists.Name)"
        }
        
        $index = Get-SelectionIndex "Enter the index of the correct track to match:", 1, $spotifyTracks.Count, "Enter an index between 1 and $($spotifyTracks.Count) or nothing to exit"
    }
}