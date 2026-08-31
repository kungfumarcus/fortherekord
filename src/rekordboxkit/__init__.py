"""
Shared Rekordbox domain and database adapter.

Used by the ForTheRekord CLI and the Rekordbox MCP application.
"""

from .session import RekordboxSession
from .repository import RekordboxRepository

__all__ = ["RekordboxSession", "RekordboxRepository"]
