"""
Rekordbox database session.

Opens the encrypted master.db and detects whether Rekordbox is running.
"""

from pathlib import Path
from typing import Any, Optional

from pyrekordbox import Rekordbox6Database
from pyrekordbox.utils import get_rekordbox_pid

from .errors import RekordboxRunningError
from .write_guard import commit_database


class RekordboxSession:
    """
    Open a Rekordbox 6/7 database and detect whether the app is running.
    """

    def __init__(self, db_path: Path):
        """Initialize session with a database path. Does not open until database()."""
        self.db_path = Path(db_path)
        self._db: Optional[Any] = None
        self._running_override: Optional[bool] = None

    @property
    def is_rekordbox_running(self) -> bool:
        """True when a Rekordbox process is running. Rechecked on each access."""
        if self._running_override is not None:
            return self._running_override
        return bool(get_rekordbox_pid())

    @is_rekordbox_running.setter
    def is_rekordbox_running(self, value: bool) -> None:
        self._running_override = value

    def database(self) -> Any:
        """Get the database connection, opening if necessary."""
        if self._db is None:
            if not self.db_path.exists():
                raise FileNotFoundError(f"Rekordbox database not found: {self.db_path}")
            self._db = Rekordbox6Database(str(self.db_path))
        return self._db

    def commit(self) -> None:
        """Commit pending changes if Rekordbox is closed and tests allow it."""
        if self._db is None:
            return
        if self.is_rekordbox_running:
            raise RekordboxRunningError("Rekordbox is currently running")
        commit_database(self._db)
