import os
import subprocess
import shutil

# HotFix Prep Script
# 1. Identifies changed files between Dev and Target.
# 2. Generates fileList.txt.
# 3. Updates buildScript.sh.
# 4. Commits to HotFix branch.

def git_get_changed_files(target_branch, dev_branch):
    # Fetch latest
    subprocess.run(["git", "fetch", "origin"], check=True)
    
    # Diff to find changed files
    # Note: Adjust logic if you are identifying by PR Merge Commit ID instead
    cmd = ["git", "diff", "--name-only", f"origin/{target_branch}...origin/{dev_branch}"]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    
    files = result.stdout.strip().split('\n')
    return [f for f in files if f] # Filter empty strings

def generate_file_list(files, output_path):
    with open(output_path, 'w') as f:
        for file in files:
            # OPTIONAL: Map source paths to compiled paths if needed
            # e.g. src/main/java/Foo.java -> WEB-INF/classes/Foo.class
            f.write(file + "\n")
    print(f"Generated {output_path} with {len(files)} files.")

def update_build_script(script_path, hf_number, target_branch):
    # Mock update of shell script variables
    lines = []
    if os.path.exists(script_path):
        with open(script_path, 'r') as f:
            lines = f.readlines()
    
    with open(script_path, 'w') as f:
        found_hf = False
        found_target = False
        
        for line in lines:
            if line.startswith("export HF_NUMBER="):
                f.write(f"export HF_NUMBER={hf_number}\n")
                found_hf = True
            elif line.startswith("export TARGET_BRANCH="):
                f.write(f"export TARGET_BRANCH={target_branch}\n")
                found_target = True
            else:
                f.write(line)
        
        if not found_hf: f.write(f"export HF_NUMBER={hf_number}\n")
        if not found_target: f.write(f"export TARGET_BRANCH={target_branch}\n")

def main():
    # INPUTS
    DEV_BRANCH = "feature/CR-1234-fix"
    TARGET_BRANCH = "release/1.0"
    HOTFIX_BRANCH = "hotfix/builder"
    HF_NUMBER = "1234"
    REPO_ROOT = os.getcwd() # Run from repo root

    print(f"--- Preparing HotFix {HF_NUMBER} ---")
    
    # 1. Get Files
    changed_files = git_get_changed_files(TARGET_BRANCH, DEV_BRANCH)
    print(f"Identified {len(changed_files)} changed files.")
    
    # 2. Switch to HotFix Branch
    print(f"Switching to {HOTFIX_BRANCH}...")
    subprocess.run(["git", "checkout", HOTFIX_BRANCH], check=True)
    subprocess.run(["git", "pull", "origin", HOTFIX_BRANCH], check=True)
    
    # 3. Write Artifacts
    generate_file_list(changed_files, "fileList.txt")
    update_build_script("buildScript.sh", HF_NUMBER, TARGET_BRANCH)
    
    # 4. Commit (User must push manually or uncomment push)
    subprocess.run(["git", "add", "fileList.txt", "buildScript.sh"], check=True)
    subprocess.run(["git", "commit", "-m", f"Setup HotFix {HF_NUMBER}"], check=True)
    # subprocess.run(["git", "push", "origin", HOTFIX_BRANCH], check=True)
    
    print("HotFix prep committed. Ready to push.")

if __name__ == "__main__":
    main()
