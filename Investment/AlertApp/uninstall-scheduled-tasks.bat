@echo off
REM Remove the AlertApp scheduled tasks (does not stop a running listener).
setlocal
schtasks /Delete /TN "AlertApp-Watchdog" /F
schtasks /Delete /TN "AlertApp-Startup" /F
echo.
echo [OK] Scheduled tasks removed (if they existed).
echo To stop the running listener, run stop_stock_alert.bat in C:\Investment,
echo or end the pythonw.exe / python.exe process manually.
exit /b 0
