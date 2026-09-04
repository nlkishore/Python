@echo off
REM ============================================================================
REM  Start AlertApp Green API listener (price + rebuy + WhatsApp commands).
REM
REM  Foreground (this console stays attached — Ctrl+C to stop):
REM    run-green-api-listener.bat
REM
REM  Background (detached pythonw, logs append to listener.log):
REM    run-green-api-listener.bat /background
REM    run-green-api-listener.bat -b
REM
REM  Auto-start on reboot + self-heal: install-scheduled-tasks.bat
REM  Stop: C:\Investment\stop_stock_alert.bat
REM ============================================================================
setlocal
cd /d "%~dp0"
set PYTHONUNBUFFERED=1

set "MODE=foreground"
if /I "%~1"=="/background" set "MODE=background"
if /I "%~1"=="-b" set "MODE=background"
if /I "%~1"=="--background" set "MODE=background"

if /I "%MODE%"=="background" goto :background

echo Starting AlertApp Green API listener (foreground)...
echo Stop with Ctrl+C, or run C:\Investment\stop_stock_alert.bat
python backgroundAlert1.py
exit /b %ERRORLEVEL%

:background
REM Prefer pythonw (no console window). Fall back to python if missing.
set "PYW="
for /f "delims=" %%p in ('python -c "import sys,os;print(os.path.join(os.path.dirname(sys.executable),'pythonw.exe'))" 2^>nul') do set "PYW=%%p"
if not defined PYW set "PYW=pythonw.exe"
if not exist "%PYW%" set "PYW=python"

echo Starting AlertApp in background...
echo   Log: %~dp0listener.log
echo   Stop: C:\Investment\stop_stock_alert.bat

REM Append startup marker, then launch detached (no wait).
>>"%~dp0listener.log" echo.
>>"%~dp0listener.log" echo ===== %DATE% %TIME% background start =====

start "" /B "%PYW%" "%~dp0backgroundAlert1.py" >>"%~dp0listener.log" 2>&1

REM Brief settle, then confirm process exists
powershell -NoProfile -Command "Start-Sleep -Seconds 2"
powershell -NoProfile -Command ^
  "$p = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*backgroundAlert1.py*' }; if ($p) { $p | ForEach-Object { Write-Host ('OK background PID ' + $_.ProcessId) } } else { Write-Host 'WARN: process not found yet — check listener.log'; exit 1 }"
exit /b %ERRORLEVEL%
