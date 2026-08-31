"""
Rekordbox database session.

Opens the encrypted master.db and detects whether Rekordbox is running.
"""

import io
import logging
from pathlib import Path
from typing import Any, Optional

from pyrekordbox import Rekordbox6Database

from .errors import RekordboxRunningError
from .write_guard import commit_database


class RekordboxSession:
    """
    Open a Rekordbox 6/7 database and track whether the app holds the lock.
    """

    def __init__(self, db_path: Path):
        """Initialize session with a database path. Does not open until database()."""
        self.db_path = Path(db_path)
        self._db: Optional[Any] = None
        self.is_rekordbox_running = False

    def database(self) -> Any:
        """Get the database connection, opening if necessary."""
        if self._db is None:
            if not self.db_path.exists():
                raise FileNotFoundError(f"Rekordbox database not found: {self.db_path}")

            log_capture = io.StringIO()
            handler = logging.StreamHandler(log_capture)
            logger = logging.getLogger("pyrekordbox")
            logger.addHandler(handler)
            logger.setLevel(logging.WARNING)

            try:
                self._db = Rekordbox6Database(str(self.db_path))
                log_output = log_capture.getvalue()
                self.is_rekordbox_running = "Rekordbox is running" in log_output
            finally:
                logger.removeHandler(handler)

        return self._db

    def commit(self) -> None:
        """Commit pending changes if Rekordbox is closed and tests allow it."""
        if self._db is None:
            return
        if self.is_rekordbox_running:
            raise RekordboxRunningError("Rekordbox is currently running")
        commit_database(self._db)
