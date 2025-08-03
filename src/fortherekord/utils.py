"""
Backward compatibility module - imports from specialized utility modules.

This module provides backward compatibility for existing imports.
New code should import directly from the specific utility modules:
- text_utils: Generic text processing and formatting
- file_utils: File operations and path utilities  
- Domain-specific text functions are now in their respective modules (rekordbox.py, matching.py)
- display_progress is now in main.py
"""

# Import all functions from specialized modules for backward compatibility
from .search_utils import (
    normalize_search_string,
    extract_search_title
)

from .file_utils import (
    save_json,
    load_json,
    validate_file_paths,
    load_json_file,
    save_json_file
)

# Import domain-specific functions for backward compatibility
from .rekordbox import clean_track_title, clean_artist_name
from .main import display_progress
