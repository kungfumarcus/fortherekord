"""
CLI utility functions for terminal output formatting and progress display.
"""


def progress_bar(current: int, total: int, width: int = 33) -> str:
    """
    Display a progress bar.

    Args:
        current: Current progress value
        total: Total value for 100%
        width: Width of progress bar in characters

    Returns:
        Formatted progress bar string like "[========----------]  67%"
    """
    if total == 0:
        percent = 100
    else:
        percent = int((current / total) * 100)

    filled = "=" * (percent * width // 100)
    empty = "-" * (width - len(filled))

    return f"[{filled}{empty}] {percent:3d}%"


def cursor_up(lines: int = 1) -> str:
    """Return ANSI escape code to move cursor up specified lines."""
    return f"\033[{lines}A"


def cursor_down(lines: int = 1) -> str:
    """Return ANSI escape code to move cursor down specified lines."""
    return f"\033[{lines}B"


def clear_line(width: int = 50) -> str:
    """Return string to clear current line with spaces."""
    return "\r" + " " * width
