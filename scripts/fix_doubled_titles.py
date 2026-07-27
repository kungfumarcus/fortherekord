"""
Detect and fix double-enhanced track titles in the Rekordbox database.

Root cause: a previous version of _clean_title failed to match multi-artist
suffixes (e.g. "Artist1, Artist2"), so process_track stacked a second
" - Artist [Key]" onto an already-enhanced title each time it ran.

Usage:
  python scripts/fix_doubled_titles.py            # dry run (safe, no writes)
  python scripts/fix_doubled_titles.py --apply    # commit fixes to DB
"""

import re
import sys
import argparse
from pathlib import Path

import yaml
from pyrekordbox import Rekordbox6Database

KEY_RE = re.compile(r" - .+? \[[A-G][#b]?/?m?\]$")
DOUBLE_KEY_RE = re.compile(r"\[[A-G][#b]?/?m?\].*\[[A-G][#b]?/?m?\]")


def strip_last_key_suffix(title: str) -> str:
    """Remove the outermost ' - Artist [Key]' suffix."""
    return KEY_RE.sub("", title).rstrip()


def is_corrupted(title: str) -> bool:
    """True when the title contains two or more [Key] brackets."""
    return bool(DOUBLE_KEY_RE.search(title))


def load_db_path() -> Path:
    config_path = Path.home() / "AppData" / "Local" / "fortherekord" / "config.yaml"
    if not config_path.exists():
        sys.exit(f"Config not found: {config_path}")
    with open(config_path) as f:
        config = yaml.safe_load(f)
    return Path(config["rekordbox"]["library_path"])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply", action="store_true", help="Write fixes to database (default: dry run)"
    )
    args = parser.parse_args()

    db_path = load_db_path()
    print(f"Opening database: {db_path}")
    db = Rekordbox6Database(str(db_path))

    fixes: list[tuple] = []  # (content_obj, old_title, new_title)

    for content in db.get_content():
        title = content.Title or ""
        if not is_corrupted(title):
            continue
        fixed = strip_last_key_suffix(title)
        fixes.append((content, title, fixed))

    if not fixes:
        print("No corrupted titles found.")
        return

    print(f"\n{'DRY RUN — ' if not args.apply else ''}Found {len(fixes)} corrupted title(s):\n")
    for _, old, new in fixes:
        print(f"  FROM: {old}")
        print(f"    TO: {new}\n")

    if args.apply:
        for content, _, new_title in fixes:
            content.Title = new_title
        db.commit()
        print(f"Committed {len(fixes)} fix(es) to database.")
    else:
        print("Run with --apply to write changes.")


if __name__ == "__main__":
    main()
