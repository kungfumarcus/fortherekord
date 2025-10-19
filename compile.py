
#!/usr/bin/env python3
"""
Compile script for ForTheRekord - Creates executable using PyInstaller.

This script handles cross-platform building and can be called from:
- Local development (via compile.bat on Windows)
- GitHub Actions (for automated releases)
"""

import os
import sys
import subprocess
import shutil
import platform
from pathlib import Path


def get_platform_info():
    """Get platform-specific build information."""
    system = platform.system().lower()
    
    if system == "windows":
        return {
            "name": "windows", 
            "exe_name": "fortherekord.exe",
            "pyinstaller_args": [
                "--console",
                "--optimize", "2",  # Python bytecode optimization
                "--strip",  # Strip debug symbols to reduce size
            ]
        }
    elif system == "darwin":  # macOS
        return {
            "name": "macos",
            "exe_name": "fortherekord", 
            "pyinstaller_args": [
                "--console",
                # Note: Removed --target-arch universal2 due to Levenshtein library compatibility
                # Will build for native architecture (Intel or Apple Silicon)
                "--optimize", "2",  # Python bytecode optimization
                "--strip",  # Strip debug symbols to reduce size
            ]
        }
    else:
        raise RuntimeError(f"Unsupported platform: {system}")


def install_pyinstaller():
    """Install PyInstaller if not already available."""
    try:
        import PyInstaller
        print("PyInstaller already installed")
        return True
    except ImportError:
        print("Installing PyInstaller...")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], 
                         check=True, capture_output=True, text=True)
            print("PyInstaller installed successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Failed to install PyInstaller: {e}")
            return False


def clean_dist():
    """Clean previous build artifacts."""
    dist_path = Path("dist")
    build_path = Path("build")
    
    if dist_path.exists():
        print("Cleaning previous dist/ folder...")
        shutil.rmtree(dist_path)
    
    if build_path.exists():
        print("Cleaning previous build/ folder...")
        shutil.rmtree(build_path)


def setup_macos_compatibility():
    """
    Set up macOS deployment target for maximum compatibility.
    
    macOS 10.13 (High Sierra, 2017) covers:
    - All Intel Macs from 2017+
    - Apple Silicon Macs (native architecture build)
    - Works with Python 3.9+ requirement from pyproject.toml
    
    Note: Building for native architecture due to Levenshtein library limitations.
    """
    if platform.system().lower() == "darwin":
        os.environ["MACOSX_DEPLOYMENT_TARGET"] = "10.13"
        arch = platform.machine()
        print(f"Targeting macOS 10.13+ for {arch} architecture")


def build_executable():
    """Build the executable using PyInstaller."""
    platform_info = get_platform_info()
    
    print(f"Building for {platform_info['name']}...")
    
    # Set up macOS compatibility
    setup_macos_compatibility()
    
    # Base PyInstaller command with size optimizations
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",  # Single executable file
        "--name", "fortherekord",
        "--clean",
        "--noconfirm",
        "--noupx",  # Don't use UPX compression (can cause issues)
        # Exclude common large modules we don't use directly
        "--exclude-module", "tkinter",
        "--exclude-module", "matplotlib", 
        "--exclude-module", "PIL",
        # Note: numpy is required by pyrekordbox, so don't exclude it
        "--exclude-module", "scipy",
        "--exclude-module", "pandas",
        "--exclude-module", "IPython",
        "--exclude-module", "jupyter",
        "--exclude-module", "notebook",
        "--exclude-module", "test",
        "--exclude-module", "unittest",
        "--exclude-module", "doctest",
        # Exclude development/testing modules
        "--exclude-module", "pytest",
        "--exclude-module", "black",
        "--exclude-module", "flake8",
        "--exclude-module", "pylint",
        "--exclude-module", "mypy",
    ]
    
    # Add platform-specific arguments
    cmd.extend(platform_info["pyinstaller_args"])
    
    # Add data files (config template, etc.)
    data_folder = Path("data")
    if data_folder.exists():
        cmd.extend(["--add-data", f"data{os.pathsep}data"])
    
    # Entry point
    cmd.append("src/fortherekord/__main__.py")
    
    print(f"Running: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("PyInstaller completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"PyInstaller failed:")
        print(f"STDOUT: {e.stdout}")
        print(f"STDERR: {e.stderr}")
        return False


def rename_executable():
    """Rename executable with platform suffix for GitHub releases."""
    platform_info = get_platform_info()
    
    dist_path = Path("dist")
    original_exe = dist_path / "fortherekord"
    if platform.system().lower() == "windows":
        original_exe = dist_path / "fortherekord.exe"
    
    # For local builds, keep original name
    # For GitHub Actions, add platform suffix
    if os.environ.get("GITHUB_ACTIONS"):
        if platform.system().lower() == "windows":
            new_name = dist_path / "fortherekord-windows.exe"
        else:
            new_name = dist_path / "fortherekord-macos"
        
        if original_exe.exists():
            print(f"Renaming {original_exe.name} -> {new_name.name}")
            original_exe.rename(new_name)
        else:
            print(f"Expected executable not found: {original_exe}")
            return False
    
    return True


def main():
    """Main build process."""
    print("ForTheRekord Compile Script")
    print("=" * 50)
    
    # Check we're in the right directory
    if not Path("src/fortherekord").exists():
        print("Error: Must run from project root directory")
        print("   Expected to find: src/fortherekord/")
        sys.exit(1)
    
    # Install PyInstaller if needed
    if not install_pyinstaller():
        sys.exit(1)
    
    # Clean previous builds
    clean_dist()
    
    # Build executable
    if not build_executable():
        sys.exit(1)
    
    # Rename for GitHub releases
    if not rename_executable():
        sys.exit(1)
    
    # Show results
    platform_info = get_platform_info()
    dist_path = Path("dist")
    
    print("\nCompile completed successfully!")
    print(f"Output directory: {dist_path.absolute()}")
    
    if dist_path.exists():
        print("Generated files:")
        for file in dist_path.iterdir():
            if file.is_file():
                size_mb = file.stat().st_size / (1024 * 1024)
                print(f"   {file.name} ({size_mb:.1f} MB)")
    
    print(f"\nTest your executable:")
    if platform.system().lower() == "windows":
        print(f"   .\\dist\\fortherekord.exe --help")
    else:
        print(f"   ./dist/fortherekord --help")


if __name__ == "__main__":
    main()