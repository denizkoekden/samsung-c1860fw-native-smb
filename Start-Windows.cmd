@echo off
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
    py -3 patcher.py --gui
) else (
    python patcher.py --gui
)
if errorlevel 1 (
    echo.
    echo Python 3.10 oder neuer wird benoetigt. Siehe docs\ANLEITUNG.md.
    pause
)
