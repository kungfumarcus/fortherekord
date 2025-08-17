"""
Tests for main CLI functionality.

Tests the basic CLI shell with help and version commands.
"""

import pytest
from click.testing import CliRunner

from fortherekord.main import cli


# Helper functions to reduce repetition
def run_cli_command(args: list[str]) -> object:
    """Helper function to run CLI commands and return result."""
    runner = CliRunner()
    return runner.invoke(cli, args)


def assert_successful_command(result) -> None:
    """Helper function to assert command executed successfully."""
    assert result.exit_code == 0
    assert result.output is not None


def assert_failed_command(result, expected_exit_code: int = 1) -> None:
    """Helper function to assert command failed with expected exit code."""
    assert result.exit_code == expected_exit_code


class TestCLIBasics:
    """Test basic CLI functionality."""

    def test_cli_help(self):
        """Test that help command works."""
        result = run_cli_command(["--help"])
        assert_successful_command(result)
        assert "ForTheRekord" in result.output
        assert "Synchronize Rekordbox DJ library with Spotify" in result.output

    def test_cli_version(self):
        """Test that version command works."""
        result = run_cli_command(["--version"])
        assert_successful_command(result)
        # Should contain version number
        assert "0.1.0" in result.output or "version" in result.output.lower()

    def test_sync_command_help(self):
        """Test that sync command help works."""
        result = run_cli_command(["sync", "--help"])
        assert_successful_command(result)
        assert "Synchronize" in result.output

    def test_sync_command_not_implemented(self):
        """Test that sync command shows not implemented message."""
        result = run_cli_command(["sync"])
        assert_successful_command(result)
        assert "not yet implemented" in result.output.lower()


class TestCLIErrors:
    """Test CLI error handling."""

    def test_invalid_command(self):
        """Test that invalid commands show help."""
        result = run_cli_command(["invalid"])
        assert_failed_command(result, 2)  # Click returns 2 for usage errors
        assert "Usage:" in result.output


# Test fixtures for common setup
@pytest.fixture
def cli_runner():
    """Provide a Click CLI runner for tests."""
    return CliRunner()


# Example of how to use fixtures to reduce repetition
class TestCLIWithFixtures:
    """Example of using fixtures to reduce test repetition."""

    def test_help_with_fixture(self, cli_runner):
        """Test help command using fixture."""
        result = cli_runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "ForTheRekord" in result.output
