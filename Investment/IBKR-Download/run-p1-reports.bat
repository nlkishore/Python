@echo off
cd /d "%~dp0"
python -m ibkr_download_reports %*
