@echo off
setlocal EnableExtensions
REM Supported alert path: Green API monitor with STATUS command listener.
cd /d "C:\Investment\AlertApp"
set PYTHONUNBUFFERED=1
python "backgroundAlert1.py"
