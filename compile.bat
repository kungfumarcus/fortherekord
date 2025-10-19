@echo off
echo Compiling ForTheRekord...
echo.

REM Check if Python is available
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Error: Python not found in PATH
    echo    Please install Python or add it to your PATH
    pause
    exit /b 1
)

REM Run the compile script
python compile.py

REM Check if build was successful
if %ERRORLEVEL% neq 0 (
    echo.
    echo Build failed!
    pause
    exit /b 1
)

echo.
echo Build completed! Check the dist/ folder.
echo.
pause