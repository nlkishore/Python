@echo off
REM Start IBKR Client Portal Gateway (port 5000 per root\conf.yaml)
REM Must run from clientportal.gw folder — see doc\GettingStarted.md
set "GW_HOME=%~dp0clientportal.gw"
set "GW_CONF=root\conf.yaml"

if not exist "%GW_HOME%\bin\run.bat" (
    echo ERROR: run.bat not found under %GW_HOME%\bin
    exit /b 1
)
if not exist "%GW_HOME%\%GW_CONF%" (
    echo ERROR: Config not found: %GW_HOME%\%GW_CONF%
    exit /b 1
)

echo Starting IBKR Client Portal Gateway...
echo   Home:   %GW_HOME%
echo   Config: %GW_CONF%
echo   When you see "Server listening on port 5000", open https://localhost:5000 and login.
echo.

cd /d "%GW_HOME%"
call bin\run.bat %GW_CONF%
