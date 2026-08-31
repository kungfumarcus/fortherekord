"""
Commit safety for Rekordbox database writes.

Never commit while tests run. Optionally dump a marker file for e2e inspection.
"""

import json
import os
from pathlib import Path
from typing import Any


def is_test_mode() -> bool:
    """Return True when FORTHEREKORD_TEST_MODE is enabled."""
    return os.getenv("FORTHEREKORD_TEST_MODE", "") == "1"


def commit_database(db: Any) -> None:
    """
    Commit db unless test mode is on.

    In test mode, write a JSON marker to FORTHEREKORD_TEST_DUMP_FILE instead.
    """
    if is_test_mode():
        dump_path = os.getenv("FORTHEREKORD_TEST_DUMP_FILE")
        if dump_path:
            payload = {"committed": False, "test_mode": True}
            Path(dump_path).write_text(json.dumps(payload), encoding="utf-8")
        return

    db.commit()
