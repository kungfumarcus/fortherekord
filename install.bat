@echo off
echo Installing ForTheRekord dependencies...

REM Install development dependencies
echo Installing development dependencies...
pip install -e .[dev]

if %ERRORLEVEL% NEQ 0 (
    echo Dependency installation failed!
    exit /b 1
)

echo Dependencies installed successfully!
echo You can now run: build.bat
