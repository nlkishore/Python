@echo off
REM ============================================================================
REM  Install Windows Task Scheduler jobs that keep the AlertApp-IBKR Green API
REM  listener running: at logon and every 5 minutes (self-healing watchdog).
REM
REM  Run this ONCE (double-click, or from a normal CMD). Re-run to update.
REM  Tasks run only when THIS user is logged on (Store Python is per-user).
REM ============================================================================
setlocal
cd /d "%~dp0"
set "DIR=%~dp0"
if "%DIR:~-1%"=="\" set "DIR=%DIR:~0,-1%"

REM Resolve the real pythonw.exe (no console window) next to python.exe.
for /f "delims=" %%p in ('python -c "import sys,os;print(os.path.join(os.path.dirname(sys.executable),'pythonw.exe'))"') do set "PYW=%%p"
if not exist "%PYW%" (
  echo [X] Could not find pythonw.exe. Is Python installed and on PATH?
  exit /b 1
)
echo Using pythonw: %PYW%
echo Watchdog:     %DIR%\watchdog.py
echo.

REM --- Watchdog: every 5 minutes (covers crashes + within 5 min of boot) ---
schtasks /Create /TN "AlertApp-IBKR-Watchdog" ^
  /TR "\"%PYW%\" \"%DIR%\watchdog.py\"" ^
  /SC MINUTE /MO 5 /RL LIMITED /F
if errorlevel 1 goto :err

REM --- Startup: run the watchdog immediately at logon (instant start) ---
schtasks /Create /TN "AlertApp-IBKR-Startup" ^
  /TR "\"%PYW%\" \"%DIR%\watchdog.py\"" ^
  /SC ONLOGON /RL LIMITED /F
if errorlevel 1 goto :err

echo.
echo [OK] Scheduled tasks installed:
echo      - AlertApp-IBKR-Watchdog  (every 5 minutes)
echo      - AlertApp-IBKR-Startup   (at logon)
echo.
echo Running the watchdog once now to start the listener if needed...
"%PYW%" "%DIR%\watchdog.py"
echo Done. Check listener.log for listener output.
exit /b 0

:err
echo [X] Failed to create scheduled task. Try running this from an elevated CMD.
exit /b 1
