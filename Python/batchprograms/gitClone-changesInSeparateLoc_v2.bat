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
    echo Usage: %0 branch_name build_xml_path ant_task
    goto :eof
)

:: Check if build.xml path and Ant task are provided
if "%2"=="" (
    echo Usage: %0 branch_name build_xml_path ant_task
    goto :eof
)

if "%3"=="" (
    echo Usage: %0 branch_name build_xml_path ant_task
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

:: Run Ant build on the backup directory using the specified build.xml and task
cd %BACKUP_DIR%
ant -f %2 %3

:: Copy modified files from the backup directory back to the project directory
set MODIFIED_FILES_LIST=C:\Path\To\ModifiedFileList.txt

:: Read the modified file list and copy each file back to the project directory
for /f "delims=" %%f in (%MODIFIED_FILES_LIST%) do (
    if exist %BACKUP_DIR%\%%f (
        xcopy /Y /H /C /I %BACKUP_DIR%\%%f %PROJECT_DIR%\%1%\%%f
    ) else (
        echo File %%f does not exist in backup directory
    )
)

:: Add, commit, and push the changes to the Bitbucket repository
cd %PROJECT_DIR%\%1%
git add .
git commit -m "Updated modified files from backup after Ant build"
git push origin %1

echo Modified files copied back to branch %1%, Ant build run, and changes pushed to Bitbucket
goto :eof

:eof
exit /b 0
