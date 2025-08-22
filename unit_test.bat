@echo off
python -m pytest tests/unit/ -v --tb=short --cov=src/fortherekord --cov-report=html --cov-report=term-missing
