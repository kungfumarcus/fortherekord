param (
    [switch]$Load,
    [switch]$Unmapped,
    [switch]$Remap,
    [switch]$UseLikedCache,
    [switch]$Interactive
)

$LoadParam = $Load
. .\Update-RekordboxLibrary.ps1 -Load
$Load = $LoadParam
$ErrorActionPreference = "Stop"

$MappedTracksFile = "RekordboxToSpotifyTracks.json"
$LikedTracksFile = "SpotifyLikedTracks.json"

function Get-OAuthResponse($oAuthUrl, $params, $redirectUrl) {

    <# Include statements for .net Assemblies #>
    Add-Type -AssemblyName System.Web
    Add-Type -AssemblyName System.Runtime

    <# Start up our lightweight HTTP Listener for the OAuth Response #>
    $redirectUri = New-Object System.UriBuilder -ArgumentList $redirectUrl
    $redirectUri.Path = "/"
    $listener = New-Object System.Net.HttpListener
    $listener.Prefixes.Add($redirectUri.Uri)
    $listener.Start()

    <# Build our OAuth Query string #>
    $uri = New-Object System.UriBuilder -ArgumentList $oAuthUrl
    $query = [System.Web.HttpUtility]::ParseQueryString($uri.Query)
    foreach ($param in $params.GetEnumerator()) {
        $query[$param.Key] = $param.Value
    }
    $uri.Query = $query.ToString()


    <# Open up the browser for the User to OAuth in #>
    Start-Process $uri.Uri
    
    <# Waits for a response from the OAuth website#>
    $context = $listener.GetContext()

    <# Respond to the User with a simple HTML page #>
    $webPageResponse = "AUTHENTICATED WITH SPOTIFY"
    $webPageResponseEncoded =  [System.Text.Encoding]::UTF8.GetBytes($webPageResponse)
    $webPageResponseLength = $webPageResponseEncoded.Length
    $response = $context.response
    $response.ContentLength64 = $webPageResponseLength
    $response.ContentType = "text/html; charset=UTF-8"
    $response.OutputStream.Write($webPageResponseEncoded, 0, $webPageResponseLength)
    $response.OutputStream.Close()

    <# Stop the listener and return the incoming request #>
    $listener.Stop()
    $queryString = $context.Request.QueryString
    $responses = @{}
    foreach ($key in $queryString.AllKeys) {
        $responses[$key] = $queryString[$key]
    }
    return $responses
}

function Authenticate-Spotify($clientId, $clientSecret, $scope) {
    $oauthUrl = "https://accounts.spotify.com/authorize"
    $redirectUrl = "http://127.0.0.1:8888/callback"
    $params = @{
        response_type = "code";
        client_id = $clientId;
        scope = $scope;
        redirect_uri = $redirectUrl;
        state = (-join ((97..122) | Get-Random -Count 16 | ForEach-Object {[char]$_}));
    }
    $oauthResponse = Get-OAuthResponse $oauthUrl $params $redirectUrl
    $code = $oauthResponse["code"]

    $tokenUrl = "https://accounts.spotify.com/api/token"
    $authHeader = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("$($clientId):$clientSecret"))
    $body = [System.Web.HttpUtility]::ParseQueryString([String]::Empty)
    $body["grant_type"] = "authorization_code"
    $body["code"] = $code
    $body["redirect_uri"] = $redirectUrl

    $response = Invoke-RestMethod -Method Post -Uri $tokenUrl -Headers @{Authorization = "Basic $authHeader"} `
        -ContentType "application/x-www-form-urlencoded" -Body $body.ToString()
    return $response.access_token, $response.refresh_token
}

function Get-SpotifyUserId($accessToken) {
    $response = Invoke-RestMethod -Method Get -Uri "https://api.spotify.com/v1/me" -Headers @{Authorization = "Bearer $accessToken"}
    return $response.id
}

function Find-SpotifyTrack($accessToken, $query) {
    $searchUrl = "https://api.spotify.com/v1/search"
    $query = [System.Web.HttpUtility]::UrlEncode($query)
    $uri = "https://api.spotify.com/v1/search?q=$query&type=track&limit=10"

    return(Invoke-RestMethod -Method Get -Uri $uri -Headers @{Authorization = "Bearer $accessToken"}).tracks.items
}

function Get-SpotifyPlaylists($accessToken) {
    $playlists = @()
    $url = "https://api.spotify.com/v1/me/playlists?limit=50"
    do {
        $response = Invoke-RestMethod -Method Get -Uri $url -Headers @{Authorization = "Bearer $accessToken"}
        $playlists += $response.items
        $url = $response.next
    } while ($url)

    $playlistsHash = @{}
    foreach ($playlist in $playlists) {
        if ($playlist.name.StartsWith("rb ")) {
            $playlistsHash[$playlist.name] = $playlist
        }
    }
    return $playlistsHash
}

function New-SpotifyPlaylist($accessToken, $name, $userId) {
    $url = "https://api.spotify.com/v1/users/$userId/playlists"
    $body = @{
        name = $name
        public = $false
    }
    return Invoke-RestMethod -Method Post -Uri $url -Headers @{Authorization = "Bearer $accessToken"} -Body ($body | ConvertTo-Json)
}

function Remove-SpotifyPlaylist($accessToken, $id) {
    $url = "https://api.spotify.com/v1/playlists/$id/followers"
    Invoke-RestMethod -Method Delete -Uri $url -Headers @{ Authorization = "Bearer $accessToken" } | Out-Null
}

function Get-SpotifyPlaylistTracks($accessToken, $playlistId) {
    $tracks = @()
    $url = "https://api.spotify.com/v1/playlists/$playlistId/tracks"
    do {
        $response = Invoke-RestMethod -Method Get -Uri $url -Headers @{Authorization = "Bearer $accessToken"}
        $tracks += $response.items
        $url = $response.next
    } while ($url)
    return $tracks
}

function Remove-SpotifyPlaylistTracks($accessToken, $playlistId, $uris) {
    $url = "https://api.spotify.com/v1/playlists/$playlistId/tracks"
    $urisBatch = @()
    foreach ($uri in $uris) {
        $urisBatch += @{ uri = $uri }
        if ($urisBatch.Count -eq 100) {
            $body = @{ tracks = $urisBatch }
            Invoke-RestMethod -Method Delete -Uri $url -Headers @{Authorization = "Bearer $accessToken"} -Body ($body | ConvertTo-Json) | Out-Null
            $urisBatch = @()
        }
    }
    if ($urisBatch.Count -gt 0) {
        $body = @{ tracks = $urisBatch }
        Invoke-RestMethod -Method Delete -Uri $url -Headers @{Authorization = "Bearer $accessToken"} -Body ($body | ConvertTo-Json) | Out-Null
    }
}

function Add-SpotifyTracksToPlaylist($accessToken, $playlistId, $uris) {
    $url = "https://api.spotify.com/v1/playlists/$playlistId/tracks?limit=50"
    $urisBatch = @()
    foreach ($uri in $uris) {
        $urisBatch += $uri
        if ($urisBatch.Count -eq 50) {
            $body = @{ uris = $urisBatch }
            Invoke-RestMethod -Method Post -Uri $url -Headers @{Authorization = "Bearer $accessToken"} -Body ($body | ConvertTo-Json) | Out-Null
            $urisBatch = @()
        }
    }
    if ($urisBatch.Count -gt 0) {
        $body = @{ uris = $urisBatch }
        Invoke-RestMethod -Method Post -Uri $url -Headers @{Authorization = "Bearer $accessToken"} -Body ($body | ConvertTo-Json) | Out-Null
    }
}

function Get-SpotifySavedTracks($accessToken) {
    $savedTracks = @()
    $url = "https://api.spotify.com/v1/me/tracks?limit=50"
    do {
        $response = Invoke-RestMethod -Method Get -Uri $url -Headers @{Authorization = "Bearer $accessToken"}
        $savedTracks += $response.items
        $url = $response.next
    } while ($url)
    return $savedTracks
}

function Follow-SpotifyArtists($accessToken, $artistIds) {
    $artistIdsBatch = @()
    foreach ($artistId in $artistIds) {
        $artistIdsBatch += $artistId
        if ($artistIdsBatch.Count -eq 50) {
            $url = "https://api.spotify.com/v1/me/following?type=artist&ids=$($artistIdsBatch -join ',')"
            Invoke-RestMethod -Method Put -Uri $url -Headers @{Authorization = "Bearer $accessToken"} | Out-Null
            $artistIdsBatch = @()
        }
    }
    if ($artistIdsBatch.Count -gt 0) {
        $url = "https://api.spotify.com/v1/me/following?type=artist&ids=$($artistIdsBatch -join ',')"
        Invoke-RestMethod -Method Put -Uri $url -Headers @{Authorization = "Bearer $accessToken"} | Out-Null
    }
}

function Get-RekordboxPlaylists($playlists, $prefix, $ignorePlaylists) {
    $playlistsHash = @{}
    foreach ($playlist in $playlists) {
        $longName = $prefix
        if (-not $config.config.spotifyExcludeFromPlaylistNames -or 
            -not $config.config.spotifyExcludeFromPlaylistNames.Contains($playlist.Name)) {
            $longName = "$prefix $($playlist.Name)"
        }
        if (-not $ignorePlaylists.Contains($playlist.Name)) {
            if ($playlist.TRACK.Count -ne 0) {
                $playlistsHash[$longName] = $playlist
            }
            foreach ($childPlaylist in $playlist.NODE) {
                $playlistsHash += Get-RekordboxPlaylists $childPlaylist $longName $ignorePlaylists
            }
        }
    }
    return $playlistsHash
}

function Get-MappedTracks($includeUnmapped = $true) {
    $mappedTracks = @{}
    if (Test-Path $MappedTracksFile) {
        foreach ($property in (Get-Content $MappedTracksFile -Raw | ConvertFrom-Json).PSObject.Properties) {
            if ($includeUnmapped -or $property.Value) {
                $mappedTracks[$property.Name] = $property.Value
            }
        }    
    }
    return $mappedTracks
}

function Save-MappedTracks($mappedTracks) {
    Write-Host
    $mappedTracks | ConvertTo-Json | Set-Content $MappedTracksFile
}

function Get-LikedTracks($accessToken, [switch]$fromCache) {
    $likedTracks = @{}
    if ($fromCache) {
        $likedTracks = @{}
        if (Test-Path $LikedTracksFile) {
            Write-Host "Loading liked tracks from cache..."
            foreach ($likedTrack in (Get-Content $LikedTracksFile -Raw | ConvertFrom-Json)) {
                $likedTracks[$likedTrack.uri] = $likedTrack
            }
        }
    } else {
        Write-Host "Loading liked tracks from Spotify..."
        foreach ($track in (Get-SpotifySavedTracks $accessToken).track) {
            $likedTracks[$track.uri] = $track
        }
        Save-LikedTracks $likedTracks
    }
    return $likedTracks
}

function Save-LikedTracks($likedTracks) {
    $likedTracks.Values | ConvertTo-Json -Compress -Depth 20 | Set-Content $LikedTracksFile
}

function Get-SearchTitle($rekordboxTrack) {
    return $rekordboxTrack.Name -Replace " - .+", "" -Replace " \(ext\)", "" -Replace " \(Ext\. Mix\)", "" -Replace " \(Original Mix\)", ""
}

function Get-SearchString($s) {
    $s = $s -Replace "[\(\)\[\],]+", " " -Replace "\.", "" -Replace " \- ", " " -Replace "\: ", " " -Split " "
    $s = $s | Where-Object { $_ -ne "" -and $_ -ne "ft" -and $_ -ne "feat" -and $_ -ne "featuring" }
    return $s -Join " "
}

function Get-SelectionIndex($prompt, $min, $max, $invalidMessage) {
    while ($true) {
        $input = Read-Host $prompt
        Write-Host $input
        if (-not $input) {
            return $null
        }
        if ($input -match "^\d+$") {
            $inputNumber = [int]$input
            if ($inputNumber -ge $min -and $inputNumber -le $max) {
                return $inputNumber
            }
        }
        $prompt = $invalidMessage
    }
}

function Get-MatchScore($a, $b) {
    $aTokens = $a.ToLower() -Split "\s+" | Where-Object { $_ }
    $bTokens = $b.ToLower() -Split "\s+" | Where-Object { $_ }
    if ($aTokens.Count -eq 0 -or $bTokens.Count -eq 0) {
        return 0
    }

    # Count matching tokens
    $aMatchCount = ($aTokens | Where-Object { $bTokens -contains $_ }).Count
    $bMatchCount = ($bTokens | Where-Object { $aTokens -contains $_ }).Count

    # Calculate match percentages
    $aMatchPercentage = $aMatchCount / $aTokens.Count
    $bMatchPercentage = $bMatchCount / $bTokens.Count
    if ($bMatchPercentage -eq 0) {
        return 0
    }
    return $aMatchPercentage * $bMatchPercentage
}

function Get-TrackMatchScore($title, $artist, $spotifyTitle, $spotifyArtist, $isLiked, $spotifyRank) {
    $score = (Get-MatchScore $title $spotifyTitle) + (Get-MatchScore $artist $spotifyArtist)
    if ($isLiked) { $score = $score + 2.0 }
    $score = $score - ($spotifyRank - 1) / 10.0
    return $score / 2.0
}

function Find-SpotifyTrackForRekordboxTrack($accessToken, $rekordboxTrack, $mappedTracks, $likedTracks, $interactive) {
    $title = Get-SearchString(Get-SearchTitle $rekordboxTrack)
    $artist = Get-SearchString($rekordboxTrack.Artist)

    if ($mappedTracks.ContainsKey($rekordboxTrack.TrackID)) {
        $mappedUri = $mappedTracks[$rekordboxTrack.TrackID]
        if ($mappedUri) {
            return $mappedUri
        }
        return $null 
    }

    Write-Host
    Write-Host "Searching for '$title - $artist'..."
    $tracks = @()
    $tracks += Find-SpotifyTrack $accessToken "track:$title artist:$artist"

    if ($tracks.length -eq 0) {
        Write-Host "Searching free text '$title $artist'..."
        $tracks += Find-SpotifyTrack $accessToken "$title $artist"
    }

    if ($tracks.length -eq 0) {
        $alternativeTitle = ($title -Split " " | Where-Object { $_ -notin @("Extended", "Mix", "Original", "Remix") }) -Join " "
        if ($alternativeTitle -ne $title) {
            Write-Host "Searching by alternative title '$alternativeTitle'..."
            $tracks += Find-SpotifyTrack $accessToken "track:$alternativeTitle artist:$artist"
        }
    }

    if ($tracks.length -eq 0) {
        Write-Host "NO TRACKS FOUND"
        if (-not $interactive) {
            return $null
        }

        $alternativeTitle = Read-Host "Enter an alternative title"
        if ($alternativeTitle) {
            $title = Get-SearchString($alternativeTitle)
        }
        $alterntativeArtist = Read-Host "Enter an alternative artist"
        if ($alterntativeArtist) {
            $artist = Get-SearchString($alterntativeArtist)
        }
        $tracks += Find-SpotifyTrack $accessToken "track:$title artist:$artist"
        if ($tracks.length -eq 0) {
            Write-Host "NO TRACKS FOUND"
            return $null
        }
    }

    $spotifyRank = 1
    [array]$trackScores = $tracks | ForEach-Object {
        $isLiked = $likedTracks.ContainsKey($_.uri)
        $spotifyTitle = Get-SearchString $_.name
        $spotifyArtist = Get-SearchString ($_.artists.name -Join " ")
        [pscustomobject]@{
            track = $_
            trackName = "$($_.name) - " + $_.artists.name -Join " "
            score = Get-TrackMatchScore $title $artist $spotifyTitle $spotifyArtist $isLiked $spotifyRank
            liked = $isLiked
            spotifyRank = $spotifyRank++ 
        }
    } | Sort-Object -Property score -Descending

    if ($interactive) {
        $trackIndex = 0
        foreach ($trackScore in $trackScores) {
            $trackIndex += 1
            $trackText = "[$($trackIndex)] $($trackScore.trackName)"
            if ($trackScore.liked) { 
                $trackText += " [LIKED]" 
            }
            if ($trackScore.spotifyRank -eq 1) { 
                $trackText += " [TOP]" 
            }
            $trackText += " ($($trackScore.score.ToString("F2")))" 
            Write-Host $trackText
        }
        $selectedTrackNumber = Get-SelectionIndex "Enter the number of the track you want to select" 1 $trackScores.Count "Invalid selection, please enter a number between 0 and $($trackScores.Count) or nothing to exit"
        if (-not $selectedTrackNumber) {
            Write-Host "No track selected."
            return $null
        }
        $matchedIndex = $selectedTrackNumber - 1
    } else {
        if ($trackScores[0].score -lt 0.9) {
            Write-Host "No matching tracks found with sufficient score (best was $($trackScores[0].score))."
            return $null
        }   
        $matchedIndex = 0
    }
    $matchedName = $trackScores[$matchedIndex].trackName
    $matchedUri = $trackScores[$matchedIndex].track.uri

    Write-Host "Found spotify track '$matchedName'"
    return $matchedUri
}

function Sync-Tracks($accessToken, $spotifyPlaylist, $rekordboxPlaylist, $collectionTracks, $mappedTracks, $likedTracks) {
    $rekordboxTracks = Get-TracksFromPlaylist $rekordboxPlaylist $collectionTracks
    if (-not $rekordboxTracks.Count ) {
        Write-Host "Empty playlist - will be deleted"
        return $false
    }
    
    $spotifyUris = New-Object System.Collections.ArrayList
    $trackCount = 0
    foreach ($rekordboxTrack in $rekordboxTracks) {
        $spotifyUri = Find-SpotifyTrackForRekordboxTrack $accessToken $rekordboxTrack $mappedTracks $likedTracks $interactive

        $mappedTracks[$rekordboxTrack.TrackID] = $spotifyUri
        if ($spotifyUri) {
            $spotifyUris.Add($spotifyUri)
        }
    }

    Write-Host "$([int](100 * $spotifyUris.Count / $rekordboxTracks.Count))% match ($($spotifyUris.Count) / $($rekordboxTracks.Count) tracks)"
    
    if ($spotifyUris.Count -eq 0) {
        return $false
    }

    # Check if the current playlist is identical
    $currentSpotifyTracks = Get-SpotifyPlaylistTracks $accessToken $spotifyPlaylist.id
    $currentSpotifyUris = $currentSpotifyTracks | ForEach-Object { $_.track.uri }
    $differenceSpotted = $currentSpotifyTracks.Count -ne $spotifyUris.Count
    if (-not $differenceSpotted) {
        for ($i = 0; $i -lt $currentSpotifyUris.Count; $i++) {
            if ($currentSpotifyUris[$i] -ne $spotifyUris[$i]) {
                $differenceSpotted = $true
                break
            }
        }
    }

    if ($differenceSpotted) {
        Write-Host "Playlist updated"
        Remove-SpotifyPlaylistTracks $accessToken $spotifyPlaylist.id $currentSpotifyUris
        Add-SpotifyTracksToPlaylist $accessToken $spotifyPlaylist.id $spotifyUris
        Save-MappedTracks $mappedTracks
    }

    Write-Host 
    return $true
}

function Sync-Playlists($accessToken, $libraryXml, $mappedTracks, $likedTracks, $unmapped) {
    $spotifyPlaylists = Get-SpotifyPlaylists $accessToken
    $ignorePlaylists = $config.config.ignorePlaylists -split "," | ForEach-Object { $_.Trim() } 
    if ($config.config.spotifyIgnorePlaylists) {
        $ignorePlaylists += $config.config.spotifyIgnorePlaylists -split "," | ForEach-Object { $_.Trim() }
    }
    $rekordboxPlaylists = Get-RekordboxPlaylists $libraryXml.DJ_PLAYLISTS.PLAYLISTS.NODE.NODE "rb" $ignorePlaylists
    $collectionTracks = Get-RekordboxCollectionTracks $libraryXml
    $userId = Get-SpotifyUserId $accessToken
    #$replaceInTitle = [string]$config.config.spotifyReplaceInTitle -Split "," | Where-Object { $_ -ne ' ' }

    try {
        foreach ($playlistName in $rekordboxPlaylists.Keys) {
            if ($spotifyPlaylists.ContainsKey($playlistName)) {
                Write-Host "Found playlist '$playlistName'"
                $spotifyPlaylist = $spotifyPlaylists[$playlistName]
            } else {
                Write-Host "Creating playlist '$playlistName'"
                $spotifyPlaylist = New-SpotifyPlaylist $accessToken $playlistName $userId
            }

            if (Sync-Tracks $accessToken $spotifyPlaylist $rekordboxPlaylists[$playlistName] $collectionTracks $mappedTracks $likedTracks) {
                $spotifyPlaylists.Remove($playlistName)
            }
        }

        foreach ($playlistName in $spotifyPlaylists.Keys) {
            Write-Host "Deleting playlist '$playlistName'"
            Remove-SpotifyPlaylist $accessToken $spotifyPlaylists[$playlistName].id
        }

        Write-Host
    } 
    finally {
        if ($mappedTracks.Count -eq 0) {
            Write-Host "No tracks mapped"
        } else {
            $nullMappedTracksCount = ($mappedTracks.Values | Where-Object { $_ -eq $null }).Count
            Write-Host "Overall track match percentage: $([int](100 - 100 * ($nullMappedTracksCount / $mappedTracks.Count)))%"
        }
        Save-MappedTracks $mappedTracks
    }
}

function Follow-LikedArtists($accessToken, $libraryXml, $mappedTracks, $likedTracks, $spotifyFollowLikedArtistsThreshold) {
    Write-Host "Following artists with $spotifyFollowLikedArtistsThreshold or more liked tracks..."

    $artistTrackCounts = @{}
    $mappedUris = @{}
    $mappedTracks.Values | ForEach-Object { if ($_) { $mappedUris[$_] = $null } }
    $artistsToFollow = @{}
    foreach ($likedTrack in $likedTracks.Values | Where-Object { $mappedUris.ContainsKey($_.uri) }) {
        foreach ($artist in $likedTrack.artists) {
            if (-not $artistTrackCounts.ContainsKey($artist.id)) {
                $artistTrackCounts[$artist.id] = 0
                $artistsToFollow[$artist.id] = $artist.name
            }
            $artistTrackCounts[$artist.id]++
        }
    }

    foreach ($artistId in $artistTrackCounts.Keys) {
        if ($artistTrackCounts[$artistId] -ge $spotifyFollowLikedArtistsThreshold) {
            Write-Host "Following artist '$($artistsToFollow[$artistId])'"
            Follow-SpotifyArtists $accessToken $artistId
        }
    }
}


if (-not $Load) {
    $config = Get-Configuration
    $accessToken, $refreshToken = Authenticate-Spotify `
        -clientId $config.config.spotifyClientId `
        -clientSecret $config.config.spotifyClientSecret `
        -scope "playlist-read-private playlist-modify-private user-library-read user-follow-modify"
    $libraryPath = Get-RekordboxLibraryPath $config
    $libraryXml = Load-RekordboxLibrary $libraryPath
    $mappedTracks = Get-MappedTracks (-not $unmapped)
    $likedTracks = Get-LikedTracks $accessToken -fromCache:$UseLikedCache

    if ($Remap) {
        if (Test-Path $MappedTracksFile) {
            Remove-Item $MappedTracksFile -Force
            Write-Host "Mapped tracks file deleted."
        }
    }

    # Sync-Playlists $accessToken $libraryXml $mappedTracks $likedTracks $Unmapped

    $spotifyFollowLikedArtistsThreshold = $config.config.spotifyFollowLikedArtistsThreshold
    if ($spotifyFollowLikedArtistsThreshold -and $spotifyFollowLikedArtistsThreshold -gt 0) {
        Follow-LikedArtists $accessToken $libraryXml $mappedTracks $likedTracks $spotifyFollowLikedArtistsThreshold
    }
}