"""
Tests for search_utils module.
"""

import pytest
from fortherekord.search_utils import (
    normalize_search_string,
    extract_search_title
)


class TestNormalizeSearchString:
    """Test normalize_search_string function."""
    
    def test_normalize_basic(self):
        """Test basic string normalization."""
        result = normalize_search_string("Hello World")
        assert result == "hello world"
    
    def test_normalize_empty(self):
        """Test normalizing empty string."""
        result = normalize_search_string("")
        assert result == ""
    
    def test_normalize_special_chars(self):
        """Test normalizing string with special characters."""
        result = normalize_search_string("Café & Bar (Remix)")
        assert result == "caf bar remix"  # Note: é becomes empty in current implementation
    
    def test_normalize_multiple_spaces(self):
        """Test normalizing string with multiple spaces."""
        result = normalize_search_string("Multiple   Spaces    Here")
        assert result == "multiple spaces here"
    
    def test_normalize_leading_trailing_spaces(self):
        """Test normalizing string with leading/trailing spaces."""
        result = normalize_search_string("  Trim Me  ")
        assert result == "trim me"


class TestExtractSearchTitle:
    """Test extract_search_title function."""
    
    def test_extract_basic(self):
        """Test basic title extraction."""
        result = extract_search_title("Song Title")
        assert result == "Song Title"
    
    def test_extract_empty(self):
        """Test extracting from empty string."""
        result = extract_search_title("")
        assert result == ""
    
    def test_extract_original_mix(self):
        """Test extracting title with Original Mix indicator."""
        result = extract_search_title("Song Title (Original Mix)")
        assert result == "Song Title"
    
    def test_extract_extended_mix(self):
        """Test extracting title with Extended Mix indicator."""
        result = extract_search_title("Song Title (Extended Mix)")
        assert result == "Song Title"
    
    def test_extract_multiple_indicators(self):
        """Test extracting title with multiple mix indicators."""
        result = extract_search_title("Song Title (Radio Edit) (Original Mix)")
        assert result == "Song Title"
    
    def test_extract_case_insensitive(self):
        """Test case insensitive extraction."""
        result = extract_search_title("Song Title (original mix)")
        assert result == "Song Title"
    
    def test_extract_whitespace_cleanup(self):
        """Test whitespace cleanup after extraction."""
        result = extract_search_title("Song Title  (Original Mix)  ")
        assert result == "Song Title"
