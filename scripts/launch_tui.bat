@echo off
REM Launch HippoAgent TUI (full-screen terminal UI).
cd /d "%~dp0\.."
if not exist ".venv\Scripts\activate.bat" (
    echo [HippoAgent] virtualenv .venv not found.
    pause
    exit /b 1
)
call ".venv\Scripts\activate.bat"
hippo tui
