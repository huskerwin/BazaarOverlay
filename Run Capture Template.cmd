@echo off
setlocal
cd /d "%~dp0"

set "PY_EXE=python"
if exist ".venv\Scripts\python.exe" (
    set "PY_EXE=.venv\Scripts\python.exe"
)

"%PY_EXE%" --version >nul 2>nul
if errorlevel 1 (
    echo Python was not found.
    echo Install Python 3.11+ and dependencies first:
    echo   pip install -r requirements.txt
    pause
    exit /b 1
)

echo.
echo === Bazaar Template Capture ===
echo Press Shift+C in your game window, then draw a box to capture.
echo.

set "ITEM_ID="
set /p ITEM_ID=Item id (example: iron_sword):
if "%ITEM_ID%"=="" (
    echo Item id is required.
    pause
    exit /b 1
)

set "DISPLAY_NAME="
set /p DISPLAY_NAME=Display name (optional):

set "THRESHOLD="
set /p THRESHOLD=Threshold [0.82]:
if "%THRESHOLD%"=="" set "THRESHOLD=0.82"

echo.
if "%DISPLAY_NAME%"=="" (
    "%PY_EXE%" tools\capture_template.py "%ITEM_ID%" --mode hotkey-box --threshold "%THRESHOLD%"
) else (
    "%PY_EXE%" tools\capture_template.py "%ITEM_ID%" --mode hotkey-box --threshold "%THRESHOLD%" --name "%DISPLAY_NAME%"
)
set "EXIT_CODE=%ERRORLEVEL%"

echo.
if "%EXIT_CODE%"=="0" (
    echo Template capture finished.
) else (
    echo Template capture exited with code %EXIT_CODE%.
)
pause
exit /b %EXIT_CODE%
