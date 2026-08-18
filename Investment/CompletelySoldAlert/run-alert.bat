@echo off

setlocal

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (

  echo Create venv first: python -m venv .venv

  echo Then: .venv\Scripts\pip install -r requirements.txt

  exit /b 1

)

call .venv\Scripts\activate.bat

python -m completely_sold_alert %*

