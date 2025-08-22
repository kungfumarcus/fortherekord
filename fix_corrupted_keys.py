"""
One-time script to fix corrupted key data in Rekordbox database.

This script removes the malformed <DjmdKey(...)> representations from track titles
and replaces them with clean key format [KeyName].
"""

import re
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from fortherekord.rekordbox_library import RekordboxLibrary
from fortherekord.models import Track
from fortherekord.config import load_config


def clean_corrupted_title(title: str) -> str:
    """
    Clean a corrupted title by removing malformed key representations.
    
    Examples:
    'Freedom - Bru-C [<DjmdKey(1618983746 Name=Dm)>] - Bru-C [<DjmdKey(1618983746 Name=Dm)>]'
    becomes:
    'Freedom - Bru-C [Dm]'
    """
    
    # Extract the original title and key from the corrupted format
    # Pattern: remove all " - Artist [<DjmdKey(...)>]" repetitions
    
    # First, extract any clean key that might exist
    clean_key_match = re.search(r'\[([A-G][#b]?m?)\]', title)
    clean_key = clean_key_match.group(1) if clean_key_match else None
    
    # Extract key from malformed format
    malformed_key_match = re.search(r'<DjmdKey\(\d+ Name=([^)]+)\)>', title)
    key_name = malformed_key_match.group(1) if malformed_key_match else clean_key
    
    # Remove all malformed key patterns
    title = re.sub(r'\s*\[<DjmdKey\([^>]+\)>\]', '', title)
    
    # Remove duplicate " - Artist" patterns (keep only the first occurrence)
    if ' - ' in title:
        # Split by " - " and keep first two parts (title and first artist)
        parts = title.split(' - ')
        if len(parts) > 2:
            # Keep only title and first artist
            title = f"{parts[0]} - {parts[1]}"
    
    # Remove any trailing " > " or ">" characters
    title = re.sub(r'\s*>\s*$', '', title).strip()
    
    # Add clean key if we found one
    if key_name:
        title = f"{title} [{key_name}]"
    
    return title


def main():
    """Fix corrupted key data in the database."""
    # Hardcode database path - replace with your actual path
    library_path = r"C:\Users\Marcus.Lund\AppData\Roaming\Pioneer\rekordbox\master.db"
    
    print(f"Using database: {library_path}")
    print("Loading Rekordbox library...")
    
    try:
        library = RekordboxLibrary(library_path)
        
        print("Getting all tracks...")
        tracks = library.get_all_tracks()
        
        print(f"Found {len(tracks)} tracks. Checking for corruption...")
        
        corrupted_tracks = []
        
        for track in tracks:
            if '<DjmdKey(' in track.title:
                original_title = track.title
                cleaned_title = clean_corrupted_title(track.title)
                
                if original_title != cleaned_title:
                    # Create a new track with cleaned title
                    cleaned_track = Track(
                        id=track.id,
                        title=cleaned_title,
                        artist=track.artist,
                        duration_ms=track.duration_ms,
                        key=track.key,
                        original_title=track.original_title,
                        original_artist=track.original_artist,
                    )
                    corrupted_tracks.append(cleaned_track)
                    print(f"\nCorrupted: {original_title}")
                    print(f"Cleaned:   {cleaned_title}")
        
        if corrupted_tracks:
            print(f"\nFound {len(corrupted_tracks)} corrupted tracks.")
            
            # First do a dry run
            print("\n=== DRY RUN ===")
            print("Simulating database changes...")
            dry_run_count = library.save_changes(corrupted_tracks, dry_run=True)
            print(f"Dry run complete. Would update {dry_run_count} tracks.")
            
            response = input(f"\nDo you want to actually fix these {len(corrupted_tracks)} tracks? (y/N): ")
            if response.lower() == 'y':
                print("\n=== ACTUAL SAVE ===")
                print("Saving changes to database...")
                changes_saved = library.save_changes(corrupted_tracks, dry_run=False)
                print(f"Successfully cleaned {changes_saved} tracks!")
            else:
                print("No changes made.")
        else:
            print("No corrupted tracks found!")
            
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
