param (
    [string]$sourcePath,
    [int]$Min,
    [switch]$IgnoreDuplicates
)

$MUSIC_FILE_EXTENSIONS = @(".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".aiff", ".alac", ".m4a", ".ra", ".rm")

function Load-SourceFiles($path) {
    # Check if the directory exists
    if (-not $path -or -not (Test-Path -LiteralPath $path -PathType Container)) {
        do {
            $path = Read-Host "Please enter a valid directory path"
        } 
        while (-Not (Test-Path -Path $path))
    }

    # Get all files in the directory
    $files = Get-ChildItem -LiteralPath $path -Recurse -File | Where-Object { $_.Extension -in $MUSIC_FILE_EXTENSIONS }
    Write-Host "Found $($files.Count) music files in '$path'"
    $files
}

function Create-TargetDirectory($path) {
    if (-not (Test-Path -LiteralPath $path)) {
        Write-Host "Creating directory $path"
        New-Item -ItemType Directory -Path $path | Out-Null
    }
}

function Get-MusicFileGenre($file) {
    $shell = New-Object -ComObject Shell.Application
    $namespace = $shell.Namespace((Split-Path -Parent $file.FullName))
    $item = $namespace.Items().Item($file.Name)
    $genre = $item.ExtendedProperty("Genre")
    if ($genre -is [System.Array]) {
        $genre = ($genre -join " ").Trim()
    }
    if ([string]::IsNullOrEmpty($genre)) {
        $genre = $file.Extension 
    }
    $genre
}

function Get-GenreToFiles($files) {
    $genreToFiles = @{}
    foreach ($file in $files) {
        $genre = Get-MusicFileGenre $file      
        if ($genreToFiles.ContainsKey($genre)) {
            $genreToFiles[$genre] += $file
        } else {
            $genreToFiles[$genre] = @($file)
        }
    }
    $genreToFiles
}

function Copy-MusicFiles($genreToFiles, $targetPath) {
    $duplicateFileNames = @()

    foreach ($genre in $genreToFiles.Keys) {
        $files = $genreToFiles[$genre]
        
        # Escape any invalid path characters in the genre name
        foreach ($char in [System.IO.Path]::GetInvalidFileNameChars()) {
            $genre = $genre.Replace([string]$char, "")
        } 
        Write-Host "Copying $($files.Count) files to genre directory '$genre'"

        # Create a directory for the target path if it doesn't exist
        $targetDirectoryPath = Join-Path $targetPath $genre
        if (-Not (Test-Path -LiteralPath $targetDirectoryPath)) {
            New-Item -ItemType Directory -Path $targetDirectoryPath | Out-Null
        }

        foreach ($file in $files) {
            $fileName = $file.Name
            $targetFilePath = Join-Path $targetDirectoryPath $fileName

            if (-not $IgnoreDuplicates) {
                # Check if the file already exists in the destination, creating a unique name if so
                $counter = 1
                while (Test-Path -LiteralPath $targetFilePath) {
                    $baseName = [System.IO.Path]::GetFileNameWithoutExtension($fileName)
                    $extension = [System.IO.Path]::GetExtension($fileName)
                    $uniqueTargetFileName = "$baseName ($counter)$extension"
                    $targetFilePath = Join-Path $targetDirectoryPath $uniqueTargetFileName
                    $duplicateFileNames += Join-Path $genre $uniqueTargetFileName
                    $counter++
                }
            }

            # Copy the file to the genre directory
            Copy-Item -LiteralPath $file.FullName -Destination $targetFilePath
        }
    }

    Write-Host
    if ($duplicateFileNames.Count -gt 0) {    
        Write-Host "WARNING: Duplicate file names:"
        foreach ($fileName in $duplicateFileNames) {
            Write-Host $fileName
        }
    }

    Write-Host
    Write-Host "Music files have been organized by genre."
}

function Check-IgnoredFiles($sourcePath) {
    # List all file paths grouped by extension, ignoring mp3 files
    $filesByExtension = Get-ChildItem -LiteralPath $directory -Recurse -File | Where-Object { $_.Extension -ne ".mp3" } | `
        Group-Object -Property Extension
    foreach ($group in $filesByExtension) {
        Write-Host
        Write-Host "Extension: $($group.Name)"
        foreach ($file in $group.Group) {
            Write-Host $file.FullName
        }
    }
}

function Check-MinFileCount($sourcePath, $Min) {
    Write-Host
    Write-Host "Genres with fewer than $Min files:"
    $folders = Get-ChildItem -Path $targetPath -Directory -Recurse
    foreach ($folder in $folders) {
        $fileCount = (Get-ChildItem -Path $folder.FullName -File).Count
        if ($fileCount -lt $Min) {
            Write-Host "$($folder.Name) ($fileCount files)"
        }
    }
}

$targetPath = "$sourcePath - Organized"
Create-TargetDirectory $targetPath
$files = Load-SourceFiles $sourcePath
$genreToFiles = Get-GenreToFiles $files
Copy-MusicFiles $genreToFiles $targetPath
if ($Min) {
    Check-MinFileCount $targetPath $Min
}