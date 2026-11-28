@echo off
title 24hrsNewsOnline - News Autopilot Daemon
cd /d "%~dp0"

echo ==================================================
echo   24hrsNewsOnline News Autopilot (15-20m / 90-day)
echo ==================================================
echo.

powershell -NoProfile -Command "if (Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*news_daemon.py*' }) { exit 1 } else { exit 0 }"
if %errorlevel% neq 0 (
    echo [INFO] News Autopilot is ALREADY running!
    echo [INFO] Log: %~dp0logs\news_autopilot.log
    echo.
    pause
    exit /b 0
)

echo [START] Launching News Autopilot Daemon...
echo [INFO] Press Ctrl+C anytime to stop.
echo.
python -u news_daemon.py
pause
