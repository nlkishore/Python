@echo off
setlocal enabledelayedexpansion

:: Configuration
set REPO_URL=https://github.com/example/%1.git  :: Replace with your actual repo URL
set BASE_DIR=C:\Projects
set WORKING_DIR=%BASE_DIR%\working_dir
set ECLIPSE_WORKSPACE=%BASE_DIR%\eclipse\workspace
set TOMCAT_BASE_DIR=%BASE_DIR%\tomcat
set ECLIPSE_EXE="C:\eclipse\eclipse.exe"   :: Update with actual Eclipse path

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

:: Ensure .project file exists (Eclipse project import)
set PROJECT_FILE=%ECLIPSE_PROJECT%\.project

if not exist "%PROJECT_FILE%" (
    echo Creating Eclipse .project file...
    (
    echo ^<?xml version="1.0" encoding="UTF-8"?^>
    echo ^<projectDescription^>
    echo    ^<name^>%REPO_NAME%^</name^>
    echo    ^<comment^>Imported Project^</comment^>
    echo    ^<projects^>^</projects^>
    echo    ^<buildSpec^>^</buildSpec^>
    echo    ^<natures^>^</natures^>
    echo ^</projectDescription^>
    ) > "%PROJECT_FILE%"
)

:: Force Eclipse to refresh workspace
echo Refreshing Eclipse workspace...
start "" "%ECLIPSE_EXE%" -nosplash -application org.eclipse.jdt.core.JavaModel -data "%ECLIPSE_WORKSPACE%" -refresh

:: Start Tomcat instance
echo Starting Tomcat instance for %REPO_NAME%...
cd /d "%TOMCAT_INSTANCE%\bin"
start "" cmd /c "catalina.bat run"

echo ======================================================
echo Repository %REPO_NAME% is now running on Tomcat.
echo Open browser: http://localhost:8081/
echo ======================================================
exit
