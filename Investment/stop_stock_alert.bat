@echo off
setlocal EnableExtensions
REM Stop AlertApp monitor (backgroundAlert1.py) for any python*.exe / pythonw.exe.
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$stopped = 0; Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^python' -and $_.CommandLine -like '*backgroundAlert1.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue; Write-Host ('Stopped ' + $_.Name + ' PID ' + $_.ProcessId); $stopped++ }; if ($stopped -eq 0) { Write-Host 'No backgroundAlert1.py process found.' }"
echo Stock alert stop requested.
exit /b 0
