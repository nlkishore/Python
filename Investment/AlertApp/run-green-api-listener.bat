@echo off
REM Start the AlertApp Green API listener (price monitor + command listener).
REM For auto-start on reboot, run install-scheduled-tasks.bat instead.
setlocal
cd /d "%~dp0"
echo Starting AlertApp Green API listener...
python backgroundAlert1.py
