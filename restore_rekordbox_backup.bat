@echo off
echo WARNING: Rekordbox Database Restore Utility
echo ============================================
echo.
echo This will restore your Rekordbox database from the E2E test backup.
echo ONLY use this if E2E tests corrupted your database!
echo.

REM Get the database path from config
python -c "
from fortherekord.config import load_config
config = load_config()
db_path = config.get('rekordbox', {}).get('library_path')
print(f'Database path: {db_path}')
if db_path:
    import os
    backup_path = db_path + '.e2e_backup'
    if os.path.exists(backup_path):
        print(f'Backup found: {backup_path}')
    else:
        print('ERROR: No backup file found!')
        print('You can only restore if E2E tests have been run recently.')
        exit(1)
" > temp_paths.txt

if %ERRORLEVEL% neq 0 (
    echo Error: Could not determine database paths
    pause
    exit /b 1
)

REM Read paths from temp file
for /f "tokens=1,2 delims=:" %%a in (temp_paths.txt) do (
    if "%%a"=="Database path" set DB_PATH=%%b
    if "%%a"=="Backup found" set BACKUP_PATH=%%b
)
del temp_paths.txt

if "%BACKUP_PATH%"=="" (
    echo ERROR: No backup file found!
    echo E2E tests must be run first to create a backup.
    pause
    exit /b 1
)

echo Database: %DB_PATH%
echo Backup:   %BACKUP_PATH%
echo.
echo Are you ABSOLUTELY sure you want to restore from backup?
echo This will OVERWRITE your current database!
echo.
set /p CONFIRM="Type 'YES' to confirm: "

if not "%CONFIRM%"=="YES" (
    echo Restore cancelled.
    pause
    exit /b 0
)

echo.
echo Restoring database...
copy "%BACKUP_PATH%" "%DB_PATH%"

if %ERRORLEVEL% equ 0 (
    echo.
    echo SUCCESS: Database restored from backup
    echo Your Rekordbox database has been restored to the state before E2E tests.
) else (
    echo.
    echo ERROR: Failed to restore database
    echo Please restore manually:
    echo   copy "%BACKUP_PATH%" "%DB_PATH%"
)

echo.
pause