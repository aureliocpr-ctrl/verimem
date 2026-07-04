@echo off
REM Launch HippoAgent dashboard + open browser at the dashboard URL.
cd /d "%~dp0\.."
if not exist ".venv\Scripts\activate.bat" (
    echo [HippoAgent] virtualenv .venv not found in:
    echo   %CD%
    echo.
    echo First-run setup:
    echo   python -m venv .venv
    echo   .venv\Scripts\activate
    echo   pip install -e .
    echo.
    pause
    exit /b 1
)
call ".venv\Scripts\activate.bat"
echo [HippoAgent] starting dashboard on http://127.0.0.1:8765 ...
start "" http://127.0.0.1:8765
hippo dashboard
echo.
echo [HippoAgent] dashboard stopped. Press any key to close.
pause >nul
