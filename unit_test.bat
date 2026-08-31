@echo off
python -m pytest tests/unit -v --tb=long --cov=src/fortherekord --cov=src/rekordboxkit --cov=src/fortherekord_mcp --cov-report=html --cov-report=term-missing
