@echo off
REM Clone the repository
git clone <repository_url>
cd <repository_name>

REM Get the list of changed files
git diff --name-only branch1 branch2 > diff_files.txt

REM Create directories for each branch
mkdir branch1_files
mkdir branch2_files

REM Copy the files to respective folders
for /f "delims=" %%f in (diff_files.txt) do (
    REM Copy files from branch1
    git checkout branch1 -- "%%f"
    if exist "%%f" (xcopy /y /e "%%f" "branch1_files\%%f")
    
    REM Copy files from branch2
    git checkout branch2 -- "%%f"
    if exist "%%f" (xcopy /y /e "%%f" "branch2_files\%%f")
)

REM Extract added or modified lines
git diff branch1 branch2 > diff_output.txt

REM Run the Python script to generate summary
python parse_diff.py

REM Summary message
echo Summary of added and removed lines with method names has been written to summary.txt
pause
