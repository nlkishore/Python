@echo off
setlocal enabledelayedexpansion

:: Configuration
set REPO_URL=https://github.com/example/%1.git  :: Replace with your actual repo URL
set BASE_DIR=C:\Projects
set WORKING_DIR=%BASE_DIR%\working_dir
set ECLIPSE_WORKSPACE=%BASE_DIR%\eclipse\workspace
set TOMCAT_BASE_DIR=%BASE_DIR%\tomcat
set SERVER_CONFIG=%ECLIPSE_WORKSPACE%\.metadata\.plugins\org.eclipse.wst.server.core\servers.xml

:: Ask for repository name (branch name)
set /p REPO_NAME="Enter repository name (branch): "
set REPO_DIR=%WORKING_DIR%\%REPO_NAME%
set TOMCAT_INSTANCE=%TOMCAT_BASE_DIR%\tomcat_%REPO_NAME%

echo.
echo ======================================================
echo Syncing repository: %REPO_NAME%
echo ======================================================

:: Ensure working directory exists
if not exist "%WORKING_DIR%" mkdir "%WORKING_DIR%"

:: Clone or update repository
if exist "%REPO_DIR%" (
    echo Updating repository %REPO_NAME%...
    cd /d "%REPO_DIR%"
    git fetch
    git checkout %REPO_NAME%
    git pull
) else (
    echo Cloning repository %REPO_NAME%...
    git clone -b %REPO_NAME% %REPO_URL% "%REPO_DIR%"
)

:: Copy project to Eclipse workspace
set ECLIPSE_PROJECT=%ECLIPSE_WORKSPACE%\%REPO_NAME%

if exist "%ECLIPSE_PROJECT%" (
    echo Removing existing project: %ECLIPSE_PROJECT%
    rmdir /s /q "%ECLIPSE_PROJECT%"
)

echo Copying project to Eclipse workspace...
xcopy /E /I /Y "%REPO_DIR%" "%ECLIPSE_PROJECT%"

:: Configure Eclipse Server View
if not exist "%SERVER_CONFIG%" (
    echo Creating Eclipse server configuration...
    echo ^<?xml version="1.0" encoding="UTF-8"?^> > "%SERVER_CONFIG%"
    echo ^<servers^> >> "%SERVER_CONFIG%"
    echo ^</servers^> >> "%SERVER_CONFIG%"
)

:: Remove existing server entry if present
(for /f "delims=" %%i in (%SERVER_CONFIG%) do (
    echo %%i | findstr /V "</servers>" >> %SERVER_CONFIG%_new
))

:: Configure Tomcat with unique ports
set /a HTTP_PORT=8080 + 1
set /a HTTPS_PORT=8443 + 1
set /a AJP_PORT=8009 + 1

echo Configuring Tomcat instance %TOMCAT_INSTANCE%...
echo  ^<server id="%REPO_NAME%" name="%REPO_NAME%" runtime="Apache Tomcat" path="%TOMCAT_INSTANCE%"^> >> %SERVER_CONFIG%_new
echo   ^<port name="HTTP" value="%HTTP_PORT%"/^> >> %SERVER_CONFIG%_new
echo   ^<port name="HTTPS" value="%HTTPS_PORT%"/^> >> %SERVER_CONFIG%_new
echo   ^<port name="AJP" value="%AJP_PORT%"/^> >> %SERVER_CONFIG%_new
echo  ^</server^> >> %SERVER_CONFIG%_new
echo  ^</servers^> >> %SERVER_CONFIG%_new

del %SERVER_CONFIG%
rename %SERVER_CONFIG%_new servers.xml

:: Update Tomcat's server.xml
set TOMCAT_CONF=%TOMCAT_INSTANCE%\conf\server.xml

if exist "%TOMCAT_CONF%" (
    echo Updating Tomcat server.xml...

    (for /f "delims=" %%i in (%TOMCAT_CONF%) do (
        echo %%i | findstr /V "Connector port=" >> %TOMCAT_CONF%_new
    ))

    echo ^<Connector port="%HTTP_PORT%" protocol="HTTP/1.1" connectionTimeout="20000" redirectPort="%HTTPS_PORT%"/^> >> %TOMCAT_CONF%_new
    echo ^<Connector port="%AJP_PORT%" protocol="AJP/1.3" redirectPort="%HTTPS_PORT%"/^> >> %TOMCAT_CONF%_new

    del %TOMCAT_CONF%
    rename %TOMCAT_CONF%_new server.xml
) else (
    echo WARNING: server.xml not found for %TOMCAT_INSTANCE%.
)

:: Start Tomcat instance
echo Starting Tomcat instance for %REPO_NAME%...
cd /d "%TOMCAT_INSTANCE%\bin"
start "" cmd /c "catalina.bat run"

echo ======================================================
echo Repository %REPO_NAME% is now running on Tomcat.
echo Open browser: http://localhost:%HTTP_PORT%/
echo ======================================================
exit
