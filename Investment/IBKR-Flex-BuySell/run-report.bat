@echo off
cd /d "%~dp0"
if not exist "config.ini" (
  echo Copy config.ini.example to config.ini and set Flex token + query_id for --download.
  echo Running with --discover uses existing CSV under ..\IBKR-Transaction\
)
if exist ".venv\Scripts\python.exe" (
  call .venv\Scripts\activate.bat
) else (
  python -m venv .venv
  call .venv\Scripts\activate.bat
  pip install -r requirements.txt -q
)
python flex_buysell_report.py %*
