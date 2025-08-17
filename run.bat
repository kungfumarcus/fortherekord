@echo off
REM Run ForTheRekord application
echo Running ForTheRekord...

REM Ensure package is installed
pip install -e . > nul 2>&1

REM Run the application
python -m fortherekord

if %ERRORLEVEL% NEQ 0 (
    echo Application failed!
    pause
    exit /b 1
)

echo.
echo Application completed successfully!
pause
