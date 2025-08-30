"""
Tests for CLI utility functions.

Tests the terminal output formatting and cursor control functions.
"""

from fortherekord.cli_tools import progress_bar, cursor_up, cursor_down, clear_line


class TestProgressBar:
    """Test progress bar functionality."""

    def test_progress_bar_basic(self):
        """Test basic progress bar display."""
        result = progress_bar(50, 100)
        assert "[" in result
        assert "]" in result
        assert "50%" in result
        assert "=" in result
        assert "-" in result

    def test_progress_bar_zero_total(self):
        """Test progress bar with zero total (edge case)."""
        result = progress_bar(10, 0)
        assert "100%" in result

    def test_progress_bar_custom_width(self):
        """Test progress bar with custom width."""
        result = progress_bar(50, 100, width=20)
        # Should be 20 characters between brackets
        bracket_content = result.split("[")[1].split("]")[0]
        assert len(bracket_content) == 20

    def test_progress_bar_zero_percent(self):
        """Test progress bar at 0%."""
        result = progress_bar(0, 100)
        assert "0%" in result
        # Should be all dashes
        assert "=" not in result.split("[")[1].split("]")[0]

    def test_progress_bar_hundred_percent(self):
        """Test progress bar at 100%."""
        result = progress_bar(100, 100)
        assert "100%" in result
        # Should be all equals
        assert "-" not in result.split("[")[1].split("]")[0]


class TestCursorControls:
    """Test cursor control functions."""

    def test_cursor_up_default(self):
        """Test cursor up with default parameter."""
        result = cursor_up()
        assert result == "\033[1A"

    def test_cursor_up_multiple_lines(self):
        """Test cursor up with multiple lines."""
        result = cursor_up(5)
        assert result == "\033[5A"

    def test_cursor_down_default(self):
        """Test cursor down with default parameter."""
        result = cursor_down()
        assert result == "\033[1B"

    def test_cursor_down_multiple_lines(self):
        """Test cursor down with multiple lines."""
        result = cursor_down(3)
        assert result == "\033[3B"

    def test_clear_line_default(self):
        """Test clear line with default width."""
        result = clear_line()
        assert result.startswith("\r")
        assert len(result) == 51  # \r + 50 spaces

    def test_clear_line_custom_width(self):
        """Test clear line with custom width."""
        result = clear_line(width=20)
        assert result.startswith("\r")
        assert len(result) == 21  # \r + 20 spaces
        assert result == "\r" + " " * 20
