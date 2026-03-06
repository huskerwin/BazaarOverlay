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

"%PY_EXE%" main.py
set "EXIT_CODE=%ERRORLEVEL%"
if not "%EXIT_CODE%"=="0" (
    echo.
    echo Bazaar Overlay exited with code %EXIT_CODE%.
    pause
)
exit /b %EXIT_CODE%
