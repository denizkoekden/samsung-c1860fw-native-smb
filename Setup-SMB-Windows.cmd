@echo off
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
    py -3 configure_smb.py
) else (
    python configure_smb.py
)
echo.
pause
