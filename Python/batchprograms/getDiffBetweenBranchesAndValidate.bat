git clone <repository_url> 
cd <repository_name>

::Get the list of changed files:
git diff --name-only branch1 branch2 > diff_files.txt

::Copy the files to respective folders:
mkdir -p branch1_files
mkdir -p branch2_files

while read file; do
    # Copy files from branch1
    git checkout branch1 -- "$file"
    cp "$file" "branch1_files/$file"
    
    # Copy files from branch2
    git checkout branch2 -- "$file"
    cp "$file" "branch2_files/$file"
done < diff_files.txt
::Extract added or modified lines:
git diff branch1 branch2 > diff_output.txt