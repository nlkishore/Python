import subprocess
import os

def get_modified_files():
    # Fetch the list of modified files using Git
    result = subprocess.run(['git', 'diff', '--name-only', 'HEAD'], stdout=subprocess.PIPE)
    files = result.stdout.decode('utf-8').split('\n')
    return [file for file in files if file.endswith('.java')]

def run_pmd_on_files(files):
    for file in files:
        if os.path.exists(file):
            result = subprocess.run(['pmd', '-f', 'text', '-R', 'pmd.xml', '-d', file], stdout=subprocess.PIPE)
            output = result.stdout.decode('utf-8')
            if output:
                print(f"Issues found in {file}:\n{output}\n")
            else:
                print(f"No issues found in {file}\n")

if __name__ == "__main__":
    modified_files = get_modified_files()
    if modified_files:
        run_pmd_on_files(modified_files)
    else:
        print("No modified Java files found.")
