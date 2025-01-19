@echo off
setlocal enabledelayedexpansion

REM Define default values
set "repo_default=C:\path\to\default\repo"
set "branch_default=main"
set "copy_dest_default=C:\path\to\default\copy"

REM Assign arguments to variables or prompt if missing
if "%~1"=="" (
    set /p repo="Enter the Git local repository folder (default: %repo_default%): "
    if "%repo%"=="" set "repo=%repo_default%"
) else (
    set "repo=%~1"
)

if "%~2"=="" (
    set /p branch="Enter the branch name to switch to (default: %branch_default%): "
    if "%branch%"=="" set "branch=%branch_default%"
) else (
    set "branch=%~2"
)

if "%~3"=="" (
    set /p copy_dest="Enter the location where files will be copied (default: %copy_dest_default%): "
    if "%copy_dest%"=="" set "copy_dest=%copy_dest_default%"
) else (
    set "copy_dest=%~3"
)

REM Navigate to the local Git repository folder
cd "%repo%"
if errorlevel 1 (
    echo Failed to navigate to repository folder: %repo%
    exit /b 1
)

REM Switch to the specified branch
git switch %branch%
if errorlevel 1 (
    echo Failed to switch to branch: %branch%
    exit /b 1
)

REM Suppress login prompt by using Git credentials helper (assumes credentials are cached)
git config --global credential.helper cache

REM Pull latest code from the remote repository
git pull origin %branch%
if errorlevel 1 (
    echo Failed to pull the latest code from branch: %branch%
    exit /b 1
)

REM Get the latest and previous commit hashes
set "latest_commit="
for /f %%i in ('git log -n 1 --pretty=format:"%%H"') do set "latest_commit=%%i"

set "prev_commit="
for /f %%i in ('git log -n 2 --pretty=format:"%%H" ^| findstr /v "%latest_commit%"') do set "prev_commit=%%i"

if "%latest_commit%"=="" (
    echo Failed to retrieve the latest commit hash
    exit /b 1
)

if "%prev_commit%"=="" (
    echo Failed to retrieve the previous commit hash
    exit /b 1
)

REM Copy files with differences between the latest and previous commit
git diff --name-only %prev_commit% %latest_commit% > changed_files.txt

for /f "delims=" %%f in (changed_files.txt) do (
    set "src_file=%repo%\%%f"
    set "dest_file=%copy_dest%\%%f"

    REM Ensure the destination directory exists
    if not exist "%copy_dest%\%%~dpf" mkdir "%copy_dest%\%%~dpf"

    copy "%src_file%" "%dest_file%"
)

REM Clean up
del changed_files.txt

echo Done! Files with differences have been copied to: %copy_dest%
