@echo off
setlocal EnableExtensions
REM Stop only the supported AlertApp monitor (backgroundAlert1.py), not all Python processes.
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$procs = Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { $_.CommandLine -like '*backgroundAlert1.py*' }; if (-not $procs) { Write-Host 'No backgroundAlert1.py process found.'; exit 0 }; $procs | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue; Write-Host ('Stopped PID ' + $_.ProcessId) }"
echo Stock alert service stop requested.
exit /b 0
