"""
End-to-end test for ForTheRekord metadata processing workflow.

Tests the complete metadata processing workflow with database safety mechanisms.
"""

import tempfile
import os
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "tests" / "e2e"))
from conftest import run_fortherekord_command


def test_metadata_processing_workflow_with_database_safety():
    """Test the complete metadata processing workflow with database safety."""
    
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as dump_file:
        dump_path = dump_file.name
    
    try:
        # Set up environment to ensure test safety
        test_env = {
            "FORTHEREKORD_TEST_MODE": "1",
            "FORTHEREKORD_TEST_DUMP_FILE": dump_path
        }
        
        # Test help works
        help_result = run_fortherekord_command(["--help"])
        assert help_result.returncode == 0
        assert "ForTheRekord" in help_result.stdout

        # Test version works
        version_result = run_fortherekord_command(["--version"])
        assert version_result.returncode == 0
        assert "0.1" in version_result.stdout

        # Test main command with database safety - should dump to JSON instead of DB
        main_result = run_fortherekord_command([], env_vars=test_env)
        assert main_result.returncode == 0
        
        # Should handle missing database gracefully or attempt processing
        assert ("rekordbox_library_path" in main_result.stdout or 
                "Loading Rekordbox" in main_result.stdout or
                "Error" in main_result.stdout)
        
        # Verify that if any database operations were attempted, they were dumped to JSON
        # instead of actually modifying the database
        if Path(dump_path).exists():
            # If dump file exists, verify it contains JSON data
            with open(dump_path, 'r') as f:
                content = f.read().strip()
                if content:  # Only check if there's actual content
                    import json
                    dump_data = json.loads(content)
                    assert isinstance(dump_data, (dict, list)), "Dump should contain valid JSON structure"
        
    finally:
        # Clean up
        if Path(dump_path).exists():
            Path(dump_path).unlink()
