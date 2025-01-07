@echo off

:: Define the main project directory and the branch names
set PROJECT_DIR=C:\Path\To\Your\Project
set BRANCH1=branch1
set BRANCH2=branch2

:: Create directories for each branch if they don't exist
if not exist %PROJECT_DIR%\%BRANCH1% mkdir %PROJECT_DIR%\%BRANCH1%
if not exist %PROJECT_DIR%\%BRANCH2% mkdir %PROJECT_DIR%\%BRANCH2%

:: Function to switch branches
:switch_branch
if "%1"=="" (
    echo Usage: %0 branch_name
    goto :eof
)

:: Navigate to the project directory and fetch the latest changes
cd %PROJECT_DIR%\%1%
git fetch origin
git checkout %1
git pull origin %1

:: Copy specified files to the backup directory
set BACKUP_DIR=C:\Path\To\Backup\%1%
set FILE_LIST=C:\Path\To\FileList.txt

:: Read the file list and copy each file to the backup directory
for /f "delims=" %%f in (%FILE_LIST%) do (
    if exist %PROJECT_DIR%\%1%\%%f (
        xcopy /Y /H /C /I %PROJECT_DIR%\%1%\%%f %BACKUP_DIR%\%%f
    ) else (
        echo File %%f does not exist in branch %1%
    )
)

echo Switched to branch %1% and copied specified files to %BACKUP_DIR%
goto :eof

:eof
exit /b 0