@echo off
echo Building ForTheRekord...

REM Install development dependencies
echo Installing development dependencies...
pip install -e .[dev]

if %ERRORLEVEL% NEQ 0 (
    echo Build failed during dependency installation!
    exit /b 1
)

REM Run code quality checks
echo Running code quality checks...

echo Running flake8...
python -m flake8 src/ tests/
if %ERRORLEVEL% NEQ 0 (
    echo flake8 check failed!
    exit /b 1
)

echo Running pylint...
python -m pylint src/fortherekord
if %ERRORLEVEL% NEQ 0 (
    echo pylint check failed!
    exit /b 1
)

echo Running mypy...
python -m mypy src/fortherekord
if %ERRORLEVEL% NEQ 0 (
    echo mypy check failed!
    exit /b 1
)

echo Build completed successfully!
echo You can now run: fortherekord --help
