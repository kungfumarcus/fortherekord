"""
DevOps test for compilation readiness.

Tests that the compilation process would work without actually building the executable.
No database setup or heavy infrastructure - just build system validation.
"""

import subprocess
import sys
from pathlib import Path


def test_compile_dry_run():
    """Test that compilation would succeed using dry-run mode."""
    # Ensure we're in the project root
    project_root = Path(__file__).parent.parent.parent

    # Run compile.py with --dry-run flag
    result = subprocess.run(
        [sys.executable, "compile.py", "--dry-run"],
        cwd=project_root,
        capture_output=True,
        text=True,
        timeout=60,  # 1 minute timeout
    )

    # Check that the command succeeded
    assert result.returncode == 0, (
        f"Compile dry-run failed with return code {result.returncode}.\n"
        f"STDOUT: {result.stdout}\n"
        f"STDERR: {result.stderr}"
    )

    # Check for expected success messages in output
    output = result.stdout.lower()
    assert (
        "compilation readiness test passed" in output
    ), f"Expected success message not found in output:\n{result.stdout}"

    # Verify specific test components passed
    assert "[OK] Main module imports successfully" in result.stdout
    assert "[OK] PyInstaller is available and importable" in result.stdout
    assert "[OK] Platform detection:" in result.stdout


def test_compile_script_exists():
    """Test that the compile.py script exists and is executable."""
    project_root = Path(__file__).parent.parent.parent
    compile_script = project_root / "compile.py"

    assert compile_script.exists(), "compile.py script not found"
    assert compile_script.is_file(), "compile.py is not a file"


if __name__ == "__main__":
    # Allow running this test directly
    test_compile_script_exists()
    test_compile_dry_run()
    print("✅ All compilation tests passed!")
