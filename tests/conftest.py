"""
Test configuration for pytest.

Common fixtures and test utilities.
"""

import pytest
import tempfile
import shutil
from pathlib import Path

# Load environment variables from .env.local for E2E testing
try:
    from dotenv import load_dotenv
    load_dotenv('.env.local')  # Load secrets from .env.local
except ImportError:
    pass  # python-dotenv not installed, skip

from fortherekord.models import RekordboxTrack, RekordboxPlaylist


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    temp_path = tempfile.mkdtemp()
    yield Path(temp_path)
    shutil.rmtree(temp_path)


@pytest.fixture
def sample_track():
    """Create a sample RekordboxTrack for testing."""
    return RekordboxTrack(
        title="Test Song",
        artist="Test Artist",
        album="Test Album",
        track_id="1",
        duration=180,
        bpm=128.0,
        key="Am",
        genre="House"
    )


@pytest.fixture
def sample_tracks():
    """Create a collection of sample tracks."""
    return {
        "1": RekordboxTrack(title="Song 1", artist="Artist 1", track_id="1"),
        "2": RekordboxTrack(title="Song 2", artist="Artist 2", track_id="2"),
        "3": RekordboxTrack(title="Song 3", artist="Artist 3", track_id="3")
    }
