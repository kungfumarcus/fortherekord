"""
Generic text processing utilities for ForTheRekord.
"""

import re


def normalize_search_string(text: str) -> str:
    """Normalize string for search matching."""
    if not text:
        return ""
    
    # Convert to lowercase
    normalized = text.lower()
    
    # Remove special characters and keep only alphanumeric and spaces
    normalized = re.sub(r'[^a-z0-9\s]', '', normalized)
    
    # Normalize whitespace
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    
    return normalized


def extract_search_title(title: str) -> str:
    """Extract searchable title by removing mix indicators."""
    if not title:
        return ""
    
    # Remove common mix indicators
    patterns = [
        r'\s*\(Original Mix\)',
        r'\s*\(Extended Mix\)',
        r'\s*\(Ext\. Mix\)',
        r'\s*\(Radio Edit\)',
        r'\s*\(Club Mix\)',
        r'\s*\(Remix\)',
        r'\s*\(Edit\)',
        r'\s*\(VIP\)',
        r'\s*\(Bootleg\)',
        r'\s*\(Mashup\)'
    ]
    
    result = title
    for pattern in patterns:
        result = re.sub(pattern, '', result, flags=re.IGNORECASE)
    
    # Clean up extra whitespace
    result = re.sub(r'\s+', ' ', result).strip()
    
    return result
