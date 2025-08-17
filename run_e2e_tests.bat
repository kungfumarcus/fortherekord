@echo off
REM Run end-to-end tests
echo Running end-to-end tests...

REM Ensure package is installed
pip install -e . > nul 2>&1

REM Run only E2E tests
python -m pytest tests/test_e2e.py -v

if %ERRORLEVEL% NEQ 0 (
    echo E2E tests failed!
    exit /b 1
)

echo.
echo E2E tests completed successfully!
