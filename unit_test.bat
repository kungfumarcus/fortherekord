@echo off
python -m pytest tests/ -v --tb=short --cov=src/fortherekord --cov-report=html --cov-report=term-missing --ignore=tests/e2e/
