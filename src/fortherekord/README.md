# fortherekord/

Main Python package for the ForTheRekord application.

## Modules

- `__init__.py` - Package initialization and metadata
- `main.py` - CLI interface using Click framework
- `config.py` - Configuration management with Pydantic and YAML
- `models.py` - Simple data structures (dictionary-based, no complex classes)
- `rekordbox.py` - Rekordbox XML parsing and data extraction
- `utils.py` - Utility functions for text processing and JSON handling

## Architecture

The package uses a simple, functional approach matching the PowerShell scripts:
- Dictionary-based data structures instead of complex classes
- Direct XML attribute access for parsing
- Simple utility functions for common operations
- Minimal abstractions for maximum maintainability

## Design Philosophy

Code is written to be as simple as possible, matching the PowerShell hashtable approach rather than complex object-oriented patterns. This makes the code easier to understand, debug, and maintain.
