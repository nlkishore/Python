@echo off
setlocal enabledelayedexpansion

:: Define base directories
set ECLIPSE_WORKSPACE=C:\Projects\eclipse\workspace
set SERVER_CONFIG=%ECLIPSE_WORKSPACE%\.metadata\.plugins\org.eclipse.wst.server.core\servers.xml
set TOMCAT_BASE_DIR=C:\Projects\tomcat

:: Default port numbers
set HTTP_PORT=8080
set HTTPS_PORT=8443
set AJP_PORT=8009

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

    :: Generate unique ports by incrementing base values
    set /a HTTP_PORT+=1
    set /a HTTPS_PORT+=1
    set /a AJP_PORT+=1
    
    echo Adding Tomcat instance !TOMCAT_NAME! to Eclipse with ports: 
    echo   HTTP  : !HTTP_PORT!
    echo   HTTPS : !HTTPS_PORT!
    echo   AJP   : !AJP_PORT!

    :: Remove closing tag </servers> before appending new servers
    (for /f "delims=" %%i in (%SERVER_CONFIG%) do (
        echo %%i | findstr /V "</servers>" >> %SERVER_CONFIG%_new
    ))

    :: Append new server entry
    echo  ^<server id="!TOMCAT_NAME!" name="!TOMCAT_NAME!" runtime="Apache Tomcat" path="!TOMCAT_INSTANCE!"^> >> %SERVER_CONFIG%_new
    echo   ^<port name="HTTP" value="!HTTP_PORT!"/^> >> %SERVER_CONFIG%_new
    echo   ^<port name="HTTPS" value="!HTTPS_PORT!"/^> >> %SERVER_CONFIG%_new
    echo   ^<port name="AJP" value="!AJP_PORT!"/^> >> %SERVER_CONFIG%_new
    echo  ^</server^> >> %SERVER_CONFIG%_new
    echo  ^</servers^> >> %SERVER_CONFIG%_new

    del %SERVER_CONFIG%
    rename %SERVER_CONFIG%_new servers.xml

    :: Update Tomcat's server.xml to apply port changes
    set TOMCAT_CONF=!TOMCAT_INSTANCE!\conf\server.xml
    if exist "!TOMCAT_CONF!" (
        echo Updating ports in !TOMCAT_CONF!...

        (for /f "delims=" %%i in (!TOMCAT_CONF!) do (
            echo %%i | findstr /V "Connector port=" >> !TOMCAT_CONF!_new
        ))

        echo ^<Connector port="!HTTP_PORT!" protocol="HTTP/1.1" connectionTimeout="20000" redirectPort="!HTTPS_PORT!"/^> >> !TOMCAT_CONF!_new
        echo ^<Connector port="!AJP_PORT!" protocol="AJP/1.3" redirectPort="!HTTPS_PORT!"/^> >> !TOMCAT_CONF!_new

        del !TOMCAT_CONF!
        rename !TOMCAT_CONF!_new server.xml
    ) else (
        echo WARNING: server.xml not found for !TOMCAT_NAME!.
    )
))

echo All Tomcat instances added successfully with custom ports!
exit
 