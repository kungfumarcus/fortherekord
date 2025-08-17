# Python Development Standards Specification

## Scope
Define Python development standards and practices to ensure code quality, maintainability, and AI-assisted development compatibility.

## Technical Requirements
- **Python Version**: 3.8+ for broad compatibility
- **Code Style**: Follow PEP 8 standards
- **Documentation**: Clear docstrings and strategic commenting
- **Type Hints**: Use type annotations for better code clarity
- **Platform Support**: Cross-platform (Windows/macOS) for Rekordbox ecosystem compatibility
- **Development Platform**: Development on Windows only (.bat scripts for build automation)
- **Path Handling**: Use pathlib.Path for cross-platform compatibility

## Function Points

### Code Organization
- **Package Structure**: Standard Python package layout with `src/` directory
- **Module Naming**: Use lowercase with underscores (snake_case)
- **Class Naming**: Use CapitalizedWords (PascalCase)
- **Function Naming**: Use lowercase with underscores (snake_case)
- **Constant Naming**: Use UPPERCASE with underscores

### Documentation Standards
- **Class Documentation**: Every class must have a docstring explaining its purpose and responsibility
- **Method Documentation**: Public methods should have docstrings describing parameters and return values
- **Strategic Comments**: Add comments where code logic is complex or non-obvious to help AI understand intentions
- **Type Hints**: Use type annotations on function parameters and return values

### Code Quality Practices
- **Standard Libraries First**: Prefer Python standard library over third-party when functionality is equivalent
- **Explicit Imports**: Use explicit imports rather than wildcard imports (makes dependencies clear and helps AI understand code relationships)
- **Error Handling**: Use specific exception types rather than broad Exception catches
- **Resource Management**: Use context managers (with statements) for file operations and database connections

### AI-Friendly Patterns
- **Clear Intent**: Write code that clearly expresses business logic and intentions
- **Consistent Patterns**: Use consistent patterns across similar functionality
- **Descriptive Names**: Use descriptive variable and function names that explain purpose
- **Logical Grouping**: Group related functionality into cohesive modules and classes

### Development Tools
- **Linting**: Use flake8 for code quality checks with 100-character line length limit
- **Static Analysis**: Use pylint for comprehensive code analysis
- **Formatting**: Use black for consistent code formatting
- **Type Checking**: Use mypy for static type checking
- **Testing**: Use pytest for unit and integration testing with coverage reporting
- **Configuration**: Use `.flake8` configuration file for consistent linting rules across team

### Pylint Configuration Strategy
- **Global Configuration**: Keep pylint strict by default - only disable checks when absolutely necessary
- **File-Specific Disables**: Use `# pylint: disable=check-name` comments for specific cases rather than global disables
- **Framework-Specific Issues**: Disable `no-value-for-parameter` for Click decorated functions (Click handles argument injection)
- **Generated Files**: Exclude auto-generated files like `_version.py` from quality checks using ignore configuration
- **External Libraries**: Use `ignored-modules` in `.pylintrc` for third-party libraries (pyrekordbox, spotipy, click)

### Build and Quality Standards
- **Line Length**: Maximum 100 characters (configured in .flake8)
- **Import Order**: Follow PEP 8 import ordering (standard library, third-party, local imports)
- **Exception Handling**: Use specific exception types, avoid broad Exception catches
- **Interface Implementation**: Use `raise NotImplementedError` instead of `...` ellipsis in abstract methods
- **Code Cleanliness**: Remove unused parameters and avoid TODO comments (implementation details tracked in specifications)

### Example Code Structure
```python
"""
Module for handling track matching between music platforms.

This module provides fuzzy text matching capabilities for finding
equivalent tracks across different music services.
"""

from typing import List, Optional, Tuple
import logging


class TrackMatcher:
    """
    Handles fuzzy matching of tracks between different music platforms.
    
    Uses progressive matching strategy starting with exact text matches
    and falling back to cleaned/normalized text comparison.
    """
    
    def __init__(self, similarity_threshold: float = 0.75):
        """Initialize matcher with similarity threshold."""
        self.similarity_threshold = similarity_threshold
        self.logger = logging.getLogger(__name__)
    
    def find_best_match(self, source_track: dict, candidates: List[dict]) -> Optional[dict]:
        """
        Find the best matching track from candidates.
        
        Args:
            source_track: Track to find match for
            candidates: List of potential matching tracks
            
        Returns:
            Best matching track or None if no good match found
        """
        # Implementation would go here with clear logic flow
        pass
```
