@echo off
REM Open a console with the HippoAgent venv activated, ready for `hippo ...`
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
echo.
echo  ============================================
echo   HippoAgent CLI ready
echo   Try:  hippo --help
echo         hippo chat
echo         hippo dashboard
echo         hippo providers list
echo  ============================================
echo.
cmd /k
