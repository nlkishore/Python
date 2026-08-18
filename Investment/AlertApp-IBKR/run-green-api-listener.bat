@echo off
setlocal
cd /d "%~dp0"
echo Starting AlertApp-IBKR Green API listener...
python backgroundAlert.py
