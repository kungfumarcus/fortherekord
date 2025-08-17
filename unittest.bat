@echo off
REM ForTheRekord Unit Test Runner
REM Runs all unit tests with verbose output

echo Running ForTheRekord unit tests...
echo.

REM Change to the project directory
cd /d "%~dp0"

REM Run tests with verbose output and coverage if available
python -m pytest tests/ -v --tb=short

REM Check if tests passed
if %errorlevel% equ 0 (
    echo.
    echo ✅ All tests passed!
) else (
    echo.
    echo ❌ Some tests failed!
    exit /b %errorlevel%
)

pause
