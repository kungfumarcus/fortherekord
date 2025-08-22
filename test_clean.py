#!/usr/bin/env python3

import re

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

# Test the problematic cases
test_cases = [
    'Remission (ext) - Lane 8, Kasablanca > [<DjmdKey(1066001881 Name=F#m)>] - Lane 8, Kasablanca > [<DjmdKey(1066001881 Name=F#m)>] - Lane 8, Kasablanca > [<DjmdKey(1066001881 Name=F#m)>]',
    'Lost (ext) - Innellea, Kasablanca [<DjmdKey(3379041305 Name=Fm)>] - Innellea, Kasablanca [<DjmdKey(3379041305 Name=Fm)>] - Innellea, Kasablanca [<DjmdKey(3379041305 Name=Fm)>]',
    'Terminal Feeling (ext) - Kasablanca [<DjmdKey(1066001881 Name=F#m)>] - Kasablanca [<DjmdKey(1066001881 Name=F#m)>] - Kasablanca [<DjmdKey(1066001881 Name=F#m)>]'
]

for i, test_case in enumerate(test_cases, 1):
    print(f"\nTest {i}:")
    print(f"Original: {test_case}")
    print(f"Cleaned:  {clean_corrupted_title(test_case)}")
