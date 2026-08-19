@echo off
setlocal EnableExtensions
REM Stop the AlertApp monitor (backgroundAlert1.py) - targets both python.exe and
REM pythonw.exe (used when launched by Task Scheduler / watchdog).
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$stopped = 0; @('python.exe','pythonw.exe') | ForEach-Object { $exe = $_; Get-CimInstance Win32_Process -Filter \"Name='$exe'\" | Where-Object { $_.CommandLine -like '*backgroundAlert1.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue; Write-Host ('Stopped ' + $exe + ' PID ' + $_.ProcessId); $stopped++ } }; if ($stopped -eq 0) { Write-Host 'No backgroundAlert1.py process found.' }"
echo Stock alert stop requested.
exit /b 0
