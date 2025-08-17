@echo off
echo Running unit tests with coverage...

REM Ensure package is installed
pip install -e . > nul 2>&1

REM Run unit tests with coverage (exclude e2e tests)
python -m pytest tests/ --cov=src/fortherekord --cov-report=term-missing --cov-report=html -v ^
  --ignore=tests/e2e

if %ERRORLEVEL% NEQ 0 (
    echo Unit tests failed!
    exit /b 1
)

echo.
echo Unit tests completed successfully!
echo Coverage report saved to htmlcov/index.html
