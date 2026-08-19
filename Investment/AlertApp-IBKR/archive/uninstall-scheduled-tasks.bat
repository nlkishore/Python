@echo off
REM Remove the AlertApp-IBKR scheduled tasks (does not stop a running listener).
setlocal
schtasks /Delete /TN "AlertApp-IBKR-Watchdog" /F
schtasks /Delete /TN "AlertApp-IBKR-Startup" /F
echo.
echo [OK] Scheduled tasks removed (if they existed).
echo To stop a running listener, end the pythonw.exe process or restart the PC.
exit /b 0
