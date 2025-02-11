@echo off
setlocal enabledelayedexpansion

:: Define base directories
set ECLIPSE_WORKSPACE=C:\Projects\eclipse\workspace
set SERVER_CONFIG=%ECLIPSE_WORKSPACE%\.metadata\.plugins\org.eclipse.wst.server.core\servers.xml
set TOMCAT_BASE_DIR=C:\Projects\tomcat

:: List all available Tomcat instances
echo Available Tomcat instances:
dir /b %TOMCAT_BASE_DIR%
echo.

:: Ensure servers.xml exists
if not exist "%SERVER_CONFIG%" (
    echo Creating Eclipse server configuration...
    echo ^<?xml version="1.0" encoding="UTF-8"?^> > "%SERVER_CONFIG%"
    echo ^<servers^> >> "%SERVER_CONFIG%"
    echo ^</servers^> >> "%SERVER_CONFIG%"
)

:: Loop through all Tomcat instances and add them to Eclipse Server View
(for /d %%D in (%TOMCAT_BASE_DIR%\tomcat_*) do (
    set "TOMCAT_INSTANCE=%%D"
    set "TOMCAT_NAME=%%~nxD"
    
    echo Adding Tomcat instance !TOMCAT_NAME! to Eclipse...
    
    :: Remove closing tag </servers> before appending new servers
    (for /f "delims=" %%i in (%SERVER_CONFIG%) do (
        echo %%i | findstr /V "</servers>" >> %SERVER_CONFIG%_new
    ))

    :: Append new server entry
    echo  ^<server id="!TOMCAT_NAME!" name="!TOMCAT_NAME!" runtime="Apache Tomcat" path="!TOMCAT_INSTANCE!"^> >> %SERVER_CONFIG%_new
    echo  ^</servers^> >> %SERVER_CONFIG%_new

    del %SERVER_CONFIG%
    rename %SERVER_CONFIG%_new servers.xml
))

echo All Tomcat instances added successfully!
exit
