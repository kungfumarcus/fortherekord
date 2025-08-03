"""
Tests for file_utils module.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch
import pytest

from fortherekord.file_utils import save_json, load_json, validate_file_paths


class TestSaveJson:
    """Test save_json function."""
    
    def test_save_json_success(self):
        """Test successful JSON saving."""
        data = {"test": "value", "number": 42}
        
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            file_path = Path(f.name)
        
        try:
            save_json(data, file_path)
            
            # Verify file was created and contains correct data
            assert file_path.exists()
            with open(file_path, 'r', encoding='utf-8') as f:
                loaded_data = json.load(f)
            assert loaded_data == data
        finally:
            file_path.unlink()
    
    def test_save_json_creates_directory(self):
        """Test that save_json creates parent directories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "subdir" / "nested" / "test.json"
            data = {"created": "directory"}
            
            save_json(data, file_path)
            
            assert file_path.exists()
            assert file_path.parent.exists()


class TestLoadJson:
    """Test load_json function."""
    
    def test_load_json_nonexistent_file(self):
        """Test loading non-existent JSON file."""
        path = Path("/nonexistent/file.json")
        result = load_json(path)
        assert result == {}
    
    def test_load_json_success(self):
        """Test successful JSON loading."""
        data = {"test": "value", "list": [1, 2, 3]}
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(data, f)
            file_path = Path(f.name)
        
        try:
            result = load_json(file_path)
            assert result == data
        finally:
            file_path.unlink()
    
    def test_load_json_invalid_json(self):
        """Test loading invalid JSON file raises exception."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("invalid json content")
            file_path = Path(f.name)
        
        try:
            with pytest.raises(json.JSONDecodeError):
                load_json(file_path)
        finally:
            file_path.unlink()


class TestValidateFilePaths:
    """Test validate_file_paths function."""
    
    def test_validate_existing_files(self):
        """Test validating existing files."""
        with tempfile.NamedTemporaryFile() as f1, tempfile.NamedTemporaryFile() as f2:
            path1, path2 = Path(f1.name), Path(f2.name)
            errors = validate_file_paths(path1, path2)
            assert errors == []
    
    def test_validate_nonexistent_file(self):
        """Test validating non-existent file."""
        path = Path("/nonexistent/file.txt")
        errors = validate_file_paths(path)
        assert len(errors) == 1
        assert "File not found" in errors[0]
        assert str(path) in errors[0]
    
    def test_validate_directory(self):
        """Test validating directory instead of file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir)
            errors = validate_file_paths(path)
            assert len(errors) == 1
            assert "directory, not a file" in errors[0]
    
    def test_validate_mixed_paths(self):
        """Test validating mix of valid and invalid paths."""
        with tempfile.NamedTemporaryFile() as valid_file:
            valid_path = Path(valid_file.name)
            invalid_path = Path("/nonexistent/file.txt")
            
            errors = validate_file_paths(valid_path, invalid_path)
            assert len(errors) == 1
            assert "File not found" in errors[0]
