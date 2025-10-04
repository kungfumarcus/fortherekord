#!/usr/bin/env python3
"""
Enhanced title cleanup script.

Removes " - xxx" from titles when xxx contains ANY of the artists,
not just exact matches.
"""

import re
import sys
from pathlib import Path
import yaml

# Add src directory to path to import our modules
sys.path.insert(0, str(Path(__file__).parent / "src"))

from fortherekord.rekordbox_library import RekordboxLibrary


def load_config():
    """Load configuration to get database path."""
    config_path = Path(r"C:\Users\Marcus.Lund\AppData\Local\fortherekord\config.yaml")
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def clean_title_smart(title, artist_name):
    """
    Remove artist patterns from the end of titles.
    
    Removes " - xxx" when xxx contains ANY of the individual artists.
    
    Example:
    - Title: "Be There ft. Ayah Marar - T & Sugah"  
    - Artist: "Ayah Marar, T & Sugah"
    - Result: "Be There ft. Ayah Marar" (removes " - T & Sugah")
    """
    if not title or not " - " in title or not artist_name:
        return title, False
    
    original_title = title
    
    # Split artist field into individual artists
    # Split on common separators: comma, &, feat, ft, featuring
    artists_split = re.split(r',\s*|&\s*|\s+feat\.?\s+|\s+ft\.?\s+|\s+featuring\s+', artist_name)
    individual_artists = [a.strip() for a in artists_split if a.strip()]
    
    # Keep removing patterns from the end
    while True:
        changed = False
        
        # Pattern 1: Remove " - anything [Key]" at the end
        end_with_key = r'^(.+) - ([^-]+) \[([A-G][#b]?/?[m]?)\]$'
        match = re.match(end_with_key, title)
        if match:
            suffix_part = match.group(2).strip()
            # Check if any individual artist appears in this suffix
            for artist in individual_artists:
                if artist.lower() in suffix_part.lower():
                    title = match.group(1)
                    changed = True
                    break
            if changed:
                continue
        
        # Pattern 2: Remove " - anything" if ANY artist appears in the suffix
        end_pattern = r'^(.+) - ([^-]+)$'
        match = re.match(end_pattern, title)
        if match:
            suffix_part = match.group(2).strip()
            # Check if any individual artist appears in this suffix
            for artist in individual_artists:
                if artist.lower() in suffix_part.lower():
                    title = match.group(1)
                    changed = True
                    break
            if changed:
                continue
        
        # No more changes, break
        if not changed:
            break
    
    return title, title != original_title


def main():
    """Main cleanup function."""
    print("🧹 Enhanced Title Cleanup")
    print("=" * 50)
    print("This will remove ' - xxx' from titles when xxx contains ANY artist")
    print()
    
    # Ask for dry run or real run
    print("Choose mode:")
    print("1. Dry run (show what would be changed)")
    print("2. Real run (actually modify database)")
    
    mode = input("Enter 1 or 2: ").strip()
    if mode not in ['1', '2']:
        print("Invalid choice. Aborted.")
        return
    
    dry_run = (mode == '1')
    
    if dry_run:
        print("\n🔍 DRY RUN MODE - No changes will be made")
    else:
        response = input("\n⚠️  REAL MODE - This will modify your database. Continue? (yes/no): ").strip().lower()
        if response != 'yes':
            print("Aborted.")
            return
    
    # Load config and get all tracks
    config = load_config()
    rekordbox = RekordboxLibrary(config)
    
    try:
        print("\n📂 Loading all tracks from database...")
        all_tracks = rekordbox.get_all_tracks()
        print(f"📊 Found {len(all_tracks)} total tracks")
        
        # Filter to tracks with specific corruption pattern: "TITLE - ARTIST - ARTISTS [key]"
        corrupted_tracks = []
        pattern = r'^.+ - .+ - .+ \[([A-G][#b]?/?[m]?)\]$'
        
        for track in all_tracks:
            if re.match(pattern, track.title):
                corrupted_tracks.append(track)
        
        print(f"🎯 Found {len(corrupted_tracks)} tracks with corruption pattern 'TITLE - ARTIST - ARTISTS [key]'")
        print()
        
        fixes_applied = 0
        
        for i, track in enumerate(corrupted_tracks, 1):
            print(f"[{i}/{len(corrupted_tracks)}] Processing track {track.id}...")
            
            # Clean the title
            cleaned_title, changed = clean_title_smart(track.title, track.artists)
            
            if changed:
                fixes_applied += 1
                print(f"\n   Track {track.id}:")
                print(f"   OLD: '{track.title}'")
                print(f"   NEW: '{cleaned_title}'")
                print(f"   ARTIST: '{track.artists}'")
                
                if dry_run:
                    print(f"   🔍 Would be fixed (dry run)")
                else:
                    # Apply the fix for real
                    success = rekordbox.update_track_metadata(track.id, cleaned_title, track.artists)
                    if success:
                        # Commit immediately
                        db = rekordbox._get_database()
                        db.commit()
                        print(f"   ✅ Fixed and saved")
                    else:
                        print(f"   ❌ Failed to update track {track.id}")
        
        print("\n" + "=" * 50)
        if dry_run:
            print("🔍 DRY RUN COMPLETE!")
            print(f"📊 Processed: {len(corrupted_tracks)} tracks")
            print(f"🔧 Would fix: {fixes_applied} tracks")
            print(f"✨ Already clean: {len(corrupted_tracks) - fixes_applied} tracks")
            print("\nRun again with mode 2 to actually apply the changes.")
        else:
            print("🎉 CLEANUP COMPLETE!")
            print(f"📊 Processed: {len(corrupted_tracks)} tracks")
            print(f"🔧 Fixed: {fixes_applied} tracks")
            print(f"✨ Clean: {len(corrupted_tracks) - fixes_applied} tracks")
            
            if fixes_applied > 0:
                print("\n⚠️  Please restart Rekordbox to see the changes")
    
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()