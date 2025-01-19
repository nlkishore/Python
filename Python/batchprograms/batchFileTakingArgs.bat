@echo off
::Use %~1, %~2, and %~3 to strip the surrounding double quotes when assigning the arguments to variables.
REM Define default values
set "arg1_default=default1"
set "arg2_default=default2"
set "arg3_default=default3"

REM Assign arguments to variables or prompt if missing
if "%~1"=="" (
    set /p arg1="Enter value for argument 1 (default: %arg1_default%): "
    if "%arg1%"=="" set "arg1=%arg1_default%"
) else (
    set "arg1=%~1"
)

if "%~2"=="" (
    set /p arg2="Enter value for argument 2 (default: %arg2_default%): "
    if "%arg2%"=="" set "arg2=%arg2_default%"
) else (
    set "arg2=%~2"
)

if "%~3"=="" (
    set /p arg3="Enter value for argument 3 (default: %arg3_default%): "
    if "%arg3%"=="" set "arg3=%arg3_default%"
) else (
    set "arg3=%~3"
)

REM Display assigned values
echo Argument 1: "%arg1%"
echo Argument 2: "%arg2%"
echo Argument 3: "%arg3%"

REM Add your batch file processing logic here
