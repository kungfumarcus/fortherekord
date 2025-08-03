"""
File operations and path utilities for ForTheRekord.
"""

import json
from typing import List
from pathlib import Path


def save_json(data: dict, file_path: Path) -> None:
    """Save data to JSON file."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_json(file_path: Path) -> dict:
    """Load data from JSON file."""
    if not file_path.exists():
        return {}
    
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def validate_file_paths(*paths: Path) -> List[str]:
    """Validate file paths and return list of errors."""
    errors = []
    for path in paths:
        if not path.exists():
            errors.append(f"File not found: {path}")
        elif path.is_dir():
            errors.append(f"Path is a directory, not a file: {path}")
    return errors


def load_json_file(file_path: Path) -> dict:
    """Alias for load_json for test compatibility."""
    if not file_path.exists():
        return None
    
    try:
        return load_json(file_path)
    except json.JSONDecodeError as e:
        print(f"Error loading JSON file {file_path}: {e}")
        return None


def save_json_file(data: dict, file_path: Path) -> bool:
    """Alias for save_json for test compatibility."""
    try:
        save_json(data, file_path)
        return True
    except Exception as e:
        print(f"Error saving JSON: {e}")
        return False
