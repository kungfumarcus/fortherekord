param (
    $rootName,
    $mytag
)

$config = Get-Configuration
$accessToken, $refreshToken = Authenticate-Spotify $config.config.spotifyClientId $config.config.spotifyClientSecret
$libraryPath = Get-RekordboxLibraryPath $config
$libraryXml = Load-RekordboxLibrary $libraryPath

$rootNode = $libraryXml.SelectSingleNode("DJ_PLAYLISTS/PLAYLISTS/NODE/NODE[@Name='$rootName']")
foreach ($mytagNode in $rootNode.SelectNodes("NODE[@Name='mytags']/NODE")) {
    $mytagNode.ParentNode.RemoveChild($mytagNode)
}



Save-RekordboxLibrary $libraryPath ($libraryPath -Replace '\.xml$', '-import.xml') $libraryXml
