@echo off
python -m pytest tests/unit -v --tb=long --cov=src/fortherekord --cov-report=html --cov-report=term-missing
